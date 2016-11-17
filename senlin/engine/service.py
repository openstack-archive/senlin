# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import functools

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service
from oslo_utils import timeutils
from oslo_utils import uuidutils
from osprofiler import profiler
import six

from senlin.common import consts
from senlin.common import context as senlin_context
from senlin.common import exception
from senlin.common.i18n import _, _LE, _LI
from senlin.common import messaging as rpc_messaging
from senlin.common import scaleutils as su
from senlin.common import schema
from senlin.common import utils
from senlin.engine.actions import base as action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import cluster_policy as cpm
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import health_manager
from senlin.engine import node as node_mod
from senlin.engine.receivers import base as receiver_mod
from senlin.engine import scheduler
from senlin.objects import action as action_obj
from senlin.objects import base as obj_base
from senlin.objects import cluster as cluster_obj
from senlin.objects import cluster_policy as cp_obj
from senlin.objects import credential as cred_obj
from senlin.objects import event as event_obj
from senlin.objects import node as node_obj
from senlin.objects import policy as policy_obj
from senlin.objects import profile as profile_obj
from senlin.objects import receiver as receiver_obj
from senlin.objects import service as service_obj
from senlin.policies import base as policy_base
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx,
                                              senlin_context.RequestContext):
            ctx = senlin_context.RequestContext.from_dict(ctx.to_dict())
        try:
            return func(self, ctx, *args, **kwargs)
        except exception.SenlinException:
            raise oslo_messaging.rpc.dispatcher.ExpectedException()
    return wrapped


def request_context2(func):
    @functools.wraps(func)
    def wrapped(self, ctx, req):
        if ctx and not isinstance(ctx, senlin_context.RequestContext):
            ctx = senlin_context.RequestContext.from_dict(ctx.to_dict())

        obj = obj_base.SenlinObject.obj_class_from_name(
            req['senlin_object.name'],
            req['senlin_object.version'])
        req_obj = obj.obj_from_primitive(req)
        try:
            return func(self, ctx, req_obj)
        except exception.SenlinException:
            raise oslo_messaging.rpc.dispatcher.ExpectedException()
    return wrapped


@profiler.trace_cls("rpc")
class EngineService(service.Service):
    """Lifecycle manager for a running service engine.

    - All the contained methods here are called from the RPC client.
    - If a RPC call does not have a corresponding method here, an exception
      will be thrown.
    - Arguments to these calls are added dynamically and will be treated as
      keyword arguments by the RPC client.
    """

    def __init__(self, host, topic, manager=None):

        super(EngineService, self).__init__()
        self.host = host
        self.topic = topic
        self.dispatcher_topic = consts.DISPATCHER_TOPIC
        self.health_mgr_topic = consts.HEALTH_MANAGER_TOPIC

        # The following are initialized here and will be assigned in start()
        # which happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.TG = None
        self._rpc_server = None
        self.cleanup_timer = None
        self.cleanup_count = 0

        # Initialize the global environment
        environment.initialize()

    def init_tgm(self):
        self.TG = scheduler.ThreadGroupManager()

    def start(self):
        self.engine_id = uuidutils.generate_uuid()
        self.init_tgm()

        # create a dispatcher RPC service for this engine.
        self.dispatcher = dispatcher.Dispatcher(self,
                                                self.dispatcher_topic,
                                                consts.RPC_API_VERSION,
                                                self.TG)
        LOG.info(_LI("Starting dispatcher for engine %s"), self.engine_id)
        self.dispatcher.start()

        target = oslo_messaging.Target(version=consts.RPC_API_VERSION,
                                       server=self.host,
                                       topic=self.topic)
        if CONF.rpc_use_object:
            serializer = obj_base.VersionedObjectSerializer()
        else:
            serializer = None
        self._rpc_server = rpc_messaging.get_rpc_server(
            target, self, serializer=serializer)
        self._rpc_server.start()

        # create a health manager RPC service for this engine.
        self.health_mgr = health_manager.HealthManager(
            self, self.health_mgr_topic, consts.RPC_API_VERSION)

        LOG.info(_LI("Starting health manager for engine %s"), self.engine_id)
        self.health_mgr.start()

        # we may want to make the clean-up attempts configurable.
        self.cleanup_timer = self.TG.add_timer(2 * CONF.periodic_interval,
                                               self.service_manage_cleanup)

        self.TG.add_timer(CONF.periodic_interval,
                          self.service_manage_report)
        super(EngineService, self).start()

    def _stop_rpc_server(self):
        # Stop RPC connection to prevent new requests
        LOG.info(_LI("Stopping engine service..."))
        try:
            self._rpc_server.stop()
            self._rpc_server.wait()
            LOG.info(_LI('Engine service stopped successfully'))
        except Exception as ex:
            LOG.error(_LE('Failed to stop engine service: %s'),
                      six.text_type(ex))

    def stop(self):
        self._stop_rpc_server()

        # Notify dispatcher to stop all action threads it started.
        LOG.info(_LI("Stopping dispatcher for engine %s"), self.engine_id)
        self.dispatcher.stop()

        # Notify health_manager to stop
        LOG.info(_LI("Stopping health manager for engine %s"), self.engine_id)
        self.health_mgr.stop()

        self.TG.stop()

        ctx = senlin_context.get_admin_context()
        service_obj.Service.delete(ctx, self.engine_id)
        LOG.info(_LI('Engine %s is deleted'), self.engine_id)

        super(EngineService, self).stop()

    def service_manage_report(self):
        ctx = senlin_context.get_admin_context()
        try:
            svc = service_obj.Service.update(ctx, self.engine_id)
            # if svc is None, means it's not created.
            if svc is None:
                service_obj.Service.create(ctx, self.engine_id, self.host,
                                           'senlin-engine', self.topic)
        except Exception as ex:
            LOG.error(_LE('Service %(service_id)s update failed: %(error)s'),
                      {'service_id': self.engine_id, 'error': ex})

    def _service_manage_cleanup(self):
        ctx = senlin_context.get_admin_context()
        time_window = (2 * CONF.periodic_interval)
        svcs = service_obj.Service.get_all(ctx)
        for svc in svcs:
            if svc['id'] == self.engine_id:
                continue
            if timeutils.is_older_than(svc['updated_at'], time_window):
                LOG.info(_LI('Service %s was aborted'), svc['id'])
                service_obj.Service.delete(ctx, svc['id'])

    def service_manage_cleanup(self):
        self._service_manage_cleanup()
        self.cleanup_count += 1
        LOG.info(_LI('Service chean-up attempt count: %s'), self.cleanup_count)
        if self.cleanup_count >= 2:
            self.cleanup_timer.stop()
            LOG.info(_LI("Finished cleaning up dead services."))

    @request_context
    def credential_create(self, context, cred, attrs=None):
        """Create the credential based on the context.

        We may add more parameters in future to the query parameter, for
        example as Senlin expands its support to non-OpenStack backends.

        :param context: The requesting context which contains the user id
                        along with other identity information.
        :param cred: A credential to be associated with the user identity
                     provided in the context.
        :param dict attrs: Optional attributes associated with the credential.
        :return: A dictionary containing the persistent credential.
        """
        values = {
            'user': context.user,
            'project': context.project,
            'cred': {
                'openstack': {
                    'trust': cred
                }
            }
        }
        cred_obj.Credential.update_or_create(context, values)
        return {'cred': cred}

    @request_context
    def credential_get(self, context, query=None):
        """Get the credential based on the context.

        We may add more parameters in future to the query parameter, for
        example as Senlin expands its support to non-OpenStack backends.

        :param context: The requesting context which contains the user id
            along with other identity information.
        :param dict query: Optional query parameters.
        :return: A dictionary containing the persistent credential, or None
            if no matching credential is found.
        """
        res = cred_obj.Credential.get(context, context.user, context.project)
        if res is None:
            return None
        return res.cred.get('openstack', None)

    @request_context
    def credential_update(self, context, cred, **attrs):
        """Update a credential based on the context and provided value.

        We may add more parameters in future to the query parameter, for
        example as Senlin expands its support to non-OpenStack backends.

        :param context: The requesting context which contains the user id
                        along with other identity information.
        :param dict attrs: Optional attribute values to be associated with
                           the credential.
        :return: A dictionary containing the updated credential.
        """
        cred_obj.Credential.update(context, context.user, context.project,
                                   {'cred': {'openstack': {'trust': cred}}})
        return {'cred': cred}

    @request_context
    def get_revision(self, context):
        return CONF.revision['senlin_engine_revision']

    @request_context
    def profile_type_list(self, context):
        """List known profile type implementations.

        :param context: An instance of the request context.
        :return: A list of profile types.
        """
        return environment.global_env().get_profile_types()

    @request_context
    def profile_type_get(self, context, type_name):
        """Get the details about a profile type.

        :param context: An instance of the request context.
        :param type_name: The name of a profile type.
        :return: The details about a profile type.
        """
        profile = environment.global_env().get_profile(type_name)
        data = profile.get_schema()

        return {
            'name': type_name,
            'schema': data,
        }

    def profile_find(self, context, identity, project_safe=True):
        """Find a profile with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :param project_safe: A boolean indicating whether profile from
                             projects other than the requesting one can be
                             returned.
        :return: A DB object of profile or an exception `ResourceNotFound`
                 if no matching object is found.
        """
        if uuidutils.is_uuid_like(identity):
            profile = profile_obj.Profile.get(context, identity,
                                              project_safe=project_safe)
            if not profile:
                profile = profile_obj.Profile.get_by_name(
                    context, identity, project_safe=project_safe)
        else:
            profile = profile_obj.Profile.get_by_name(
                context, identity, project_safe=project_safe)
            if not profile:
                profile = profile_obj.Profile.get_by_short_id(
                    context, identity, project_safe=project_safe)

        if not profile:
            raise exception.ResourceNotFound(type='profile', id=identity)

        return profile

    @request_context2
    def profile_list2(self, ctx, req):
        """List profiles matching the specified criteria.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileListRequest object.
        :return: A list of `Profile` object representations.
        """
        req.obj_set_defaults()
        if not req.project_safe and not ctx.is_admin:
            raise exception.Forbidden()

        query = {'project_safe': req.project_safe}
        if req.obj_attr_is_set('limit'):
            query['limit'] = req.limit
        if req.obj_attr_is_set('marker'):
            query['marker'] = req.marker
        if req.obj_attr_is_set('sort') and req.sort is not None:
            query['sort'] = req.sort
        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('type'):
            filters['type'] = req.type
        if filters:
            query['filters'] = filters

        profiles = profile_base.Profile.load_all(ctx, **query)
        return [p.to_dict() for p in profiles]

    @request_context
    def profile_list(self, context, limit=None, marker=None, sort=None,
                     filters=None, project_safe=True):
        """List profiles matching the specified criteria.

        :param context: An instance of request context.
        :param limit: An integer specifying the maximum number of profiles to
                      return in a response.
        :param marker: An UUID specifying the profile after which the result
                       list starts.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param project_safe: A boolean indicating whether profiles from all
                             projects will be returned.
        :return: A list of `Profile` object representations.
        """
        limit = utils.parse_int_param(consts.PARAM_LIMIT, limit)
        utils.validate_sort_param(sort, consts.PROFILE_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()

        profiles = profile_base.Profile.load_all(context,
                                                 limit=limit, marker=marker,
                                                 sort=sort, filters=filters,
                                                 project_safe=project_safe)

        return [p.to_dict() for p in profiles]

    def _validate_profile(self, context, spec, name=None,
                          metadata=None, validate_props=False):
        """Validate a profile.

        :param context: An instance of the request context.
        :param name: The name for the profile to be created.
        :param spec: A dictionary containing the spec for the profile.
        :param metadata: A dictionary containing optional key-value pairs to
                         be associated with the profile.
        :param validate_props: Whether to validate if provide a valid Value
                               to property.
        :return: Validated profile object.
        """
        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        try:
            plugin = environment.global_env().get_profile(type_str)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.SpecValidationFailed(message=msg)

        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'metadata': metadata
        }
        if name is None:
            name = 'validated_profile'
        profile = plugin(name, spec, **kwargs)
        try:
            profile.validate(validate_props=validate_props)
        except exception.InvalidSpec as ex:
            msg = six.text_type(ex)
            LOG.error(_LE("Failed in validating profile: %s"), msg)
            raise exception.SpecValidationFailed(message=msg)

        return profile

    @request_context
    def profile_create(self, context, name, spec, metadata=None):
        """Create a profile with the given properties.

        :param context: An instance of the request context.
        :param name: The name for the profile to be created.
        :param spec: A dictionary containing the spec for the profile.
        :param metadata: A dictionary containing optional key-value pairs to
                         be associated with the profile.
        :return: A dictionary containing the details of the profile object
                 created.
        """
        if CONF.name_unique:
            if profile_obj.Profile.get_by_name(context, name):
                msg = _("A profile named '%(name)s' already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        profile = self._validate_profile(context, spec, name=name,
                                         metadata=metadata)

        LOG.info(_LI("Creating profile %(type)s '%(name)s'."),
                 {'type': profile.type, 'name': profile.name})

        profile.store(context)

        LOG.info(_LI("Profile %(name)s is created: %(id)s."),
                 {'name': name, 'id': profile.id})

        return profile.to_dict()

    @request_context
    def profile_validate(self, context, spec):
        """Validate a profile with the given properties.

        :param context: An instance of the request context.
        :param spec: A dictionary containing the spec for the profile.
        :return: A dictionary containing the details of the profile object
                 validated.
        """
        profile = self._validate_profile(context, spec, validate_props=True)

        return profile.to_dict()

    @request_context2
    def profile_get2(self, ctx, req):
        """Retrieve the details about a profile.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileGetRequest.
        :return: A dictionary containing the profile details, or an exception
                 of type `ResourceNotFound` if no matching object is found.
        """
        db_profile = self.profile_find(ctx, req.identity)
        profile = profile_base.Profile.load(ctx, profile=db_profile)
        return profile.to_dict()

    @request_context
    def profile_get(self, context, identity):
        """Retrieve the details about a profile.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :return: A dictionary containing the policy details, or an exception
                 of type `ResourceNotFound` if no matching object is found.
        """
        db_profile = self.profile_find(context, identity)
        profile = profile_base.Profile.load(context, profile=db_profile)
        return profile.to_dict()

    @request_context
    def profile_update(self, context, identity, name=None, metadata=None):
        """Update the properties of a given profile.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :param name: The new name for the profile.
        :param metadata: A dictionary of key-value pairs to be associated with
                         the profile.
        :returns: A dictionary containing the details of the updated profile,
                  or an exception `ResourceNotFound` if no matching profile is
                  found.
        """
        LOG.info(_LI("Updating profile '%(id)s.'"), {'id': identity})

        db_profile = self.profile_find(context, identity)
        profile = profile_base.Profile.load(context, profile=db_profile)
        changed = False
        if name is not None and name != profile.name:
            profile.name = name
            changed = True
        if metadata is not None and metadata != profile.metadata:
            profile.metadata = metadata
            changed = True
        if changed:
            profile.store(context)
        else:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Profile '%(id)s' is updated."), {'id': identity})
        return profile.to_dict()

    @request_context2
    def profile_delete2(self, ctx, req):
        """Delete the specified profile.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileDeleteRequest.
        :return: None if succeeded or an exception of `ResourceInUse` if
                 profile is referenced by certain clusters/nodes.
        """
        db_profile = self.profile_find(ctx, req.identity)
        LOG.info(_LI("Deleting profile '%s'."), req.identity)
        try:
            profile_base.Profile.delete(ctx, db_profile.id)
        except exception.EResourceBusy:
            reason = _("still referenced by some clusters and/or nodes.")
            raise exception.ResourceInUse(type='profile', id=db_profile.id,
                                          reason=reason)

        LOG.info(_LI("Profile '%s' is deleted."), req.identity)

    @request_context
    def profile_delete(self, context, identity):
        """Delete the specified profile.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :return: None if succeeded or an exception of `ResourceInUse` if
                 profile is referenced by certain clusters/nodes.
        """
        db_profile = self.profile_find(context, identity)
        LOG.info(_LI("Deleting profile '%s'."), identity)
        try:
            profile_base.Profile.delete(context, db_profile.id)
        except exception.EResourceBusy:
            reason = _("still referenced by some clusters and/or nodes.")
            raise exception.ResourceInUse(type='profile', id=identity,
                                          reason=reason)

        LOG.info(_LI("Profile '%(id)s' is deleted."), {'id': identity})

    @request_context2
    def policy_type_list2(self, ctx, req):
        """List known policy type implementations.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyTypeListRequest.
        :return: A list of policy types.
        """
        return environment.global_env().get_policy_types()

    @request_context2
    def policy_type_get2(self, ctx, req):
        """Get the details about a policy type.

        :param ctx: An instance of the request context.
        :param req: An instance of PolicyTypeGetRequest.
        :return: The details about a policy type.
        """
        policy_type = environment.global_env().get_policy(req.type_name)
        data = policy_type.get_schema()

        return {
            'name': req.type_name,
            'schema': data
        }

    def policy_find(self, context, identity, project_safe=True):
        """Find a policy with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :param project_safe: A boolean indicating whether policies from
                             projects other than the requesting one should be
                             evaluated.
        :return: A DB object of policy or an exception of `ResourceNotFound`
                 if no matching object is found.
        """
        if uuidutils.is_uuid_like(identity):
            policy = policy_obj.Policy.get(context, identity,
                                           project_safe=project_safe)
            if not policy:
                policy = policy_obj.Policy.get_by_name(
                    context, identity, project_safe=project_safe)
        else:
            policy = policy_obj.Policy.get_by_name(context, identity,
                                                   project_safe=project_safe)
            if not policy:
                policy = policy_obj.Policy.get_by_short_id(
                    context, identity, project_safe=project_safe)

        if not policy:
            raise exception.ResourceNotFound(type='policy', id=identity)

        return policy

    @request_context2
    def policy_list2(self, ctx, req):
        """List policies matching the specified criteria

        :param ctx: An instance of request context.
        :param req: An instance of the PolicyListRequest.
        :return: A List of `Policy` object representations.
        """
        req.obj_set_defaults()
        if not req.project_safe and not ctx.is_admin:
            raise exception.Forbidden()

        query = {'project_safe': req.project_safe}
        if req.obj_attr_is_set('limit'):
            query['limit'] = req.limit
        if req.obj_attr_is_set('marker'):
            query['marker'] = req.marker
        if req.obj_attr_is_set('sort') and req.sort is not None:
            query['sort'] = req.sort
        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('type'):
            filters['type'] = req.type
        if filters:
            query['filters'] = filters

        return [p.to_dict()
                for p in policy_base.Policy.load_all(ctx, **query)]

    @request_context
    def _validate_policy(self, context, spec, name=None, validate_props=False):
        """Validate a policy.

        :param context: An instance of the request context.
        :param spec: A dictionary containing the spec for the policy.
        :param name: The name for the policy to be created.
        :param validate_props: Whether to validate the value of property.
        :return: Validated policy object.
        """

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        try:
            plugin = environment.global_env().get_policy(type_str)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.SpecValidationFailed(message=msg)

        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
        }
        if name is None:
            name = 'validated_policy'
        policy = plugin(name, spec, **kwargs)

        try:
            policy.validate(context, validate_props=validate_props)
        except exception.InvalidSpec as ex:
            msg = six.text_type(ex)
            LOG.error(_LE("Failed in validating policy: %s"), msg)
            raise exception.SpecValidationFailed(message=msg)

        return policy

    @request_context2
    def policy_create2(self, ctx, req):
        """Create a policy with the given name and spec.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyCreateRequestBody.
        :return: A dictionary containing the details of the policy object
                 created.
        """
        name = req.name

        if CONF.name_unique:
            if policy_obj.Policy.get_by_name(ctx, name):
                msg = _("A policy named '%(name)s' already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        policy = self._validate_policy(ctx, req.spec, name=name)

        LOG.info(_LI("Creating policy %(type)s '%(name)s'"),
                 {'type': policy.type, 'name': policy.name})

        policy.store(ctx)
        LOG.info(_LI("Policy '%(name)s' is created: %(id)s."),
                 {'name': name, 'id': policy.id})
        return policy.to_dict()

    @request_context2
    def policy_get2(self, ctx, req):
        """Retrieve the details about a policy.

        :param ctx: An instance of request context.
        :param req: An instance of the PolicyGetRequest.
        :return: A dictionary containing the policy details.
        """
        db_policy = self.policy_find(ctx, req.identity)
        policy = policy_base.Policy.load(ctx, db_policy=db_policy)
        return policy.to_dict()

    @request_context2
    def policy_update2(self, ctx, req):
        """Update the properties of a given policy

        :param ctx: An instance of request context.
        :param req: An instance of the PolicyUpdateRequest.
        :return: A dictionary containing the policy details.
        """
        db_policy = self.policy_find(ctx, req.identity)
        policy = policy_base.Policy.load(ctx, db_policy=db_policy)

        if req.policy.name != policy.name:
            LOG.info(_LI("Updating policy '%s'."), req.identity)
            policy.name = req.policy.name
            policy.store(ctx)
            LOG.info(_LI("Policy '%s' is updated."), req.identity)

        return policy.to_dict()

    @request_context2
    def policy_delete2(self, ctx, req):
        """Delete the specified policy.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyDeleteRequest.
        :return: None if succeeded or an exception of `ResourceInUse` if
                 policy is still attached to certain clusters.
        """
        db_policy = self.policy_find(ctx, req.identity)
        LOG.info(_LI("Deleting policy '%s'."), req.identity)
        try:
            policy_base.Policy.delete(ctx, db_policy.id)
        except exception.EResourceBusy:
            reason = _("still attached to some clusters")
            raise exception.ResourceInUse(type='policy', id=req.identity,
                                          reason=reason)
        LOG.info(_LI("Policy '%s' is deleted."), req.identity)

    @request_context2
    def policy_validate2(self, ctx, req):
        """Validate a policy with the given properties.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyValidateRequestBody.
        :return: A dictionary containing the details of the policy object
                 validated.
        """

        policy = self._validate_policy(ctx, req.spec, validate_props=True)

        return policy.to_dict()

    def cluster_find(self, context, identity, project_safe=True):
        """Find a cluster with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short ID of a cluster.
        :param project_safe: A boolean parameter specifying whether only
                             clusters from the same project are qualified to
                             be returned.
        :return: An instance of `Cluster` class.
        :raises: `ResourceNotFound` if no matching object can be found.
        """

        if uuidutils.is_uuid_like(identity):
            cluster = cluster_obj.Cluster.get(context, identity,
                                              project_safe=project_safe)
            if not cluster:
                cluster = cluster_obj.Cluster.get_by_name(
                    context, identity, project_safe=project_safe)
        else:
            cluster = cluster_obj.Cluster.get_by_name(
                context, identity, project_safe=project_safe)
            # maybe it is a short form of UUID
            if not cluster:
                cluster = cluster_obj.Cluster.get_by_short_id(
                    context, identity, project_safe=project_safe)

        if not cluster:
            raise exception.ResourceNotFound(type='cluster', id=identity)

        return cluster

    @request_context2
    def cluster_list2(self, ctx, req):
        """List clusters matching the specified criteria.

        :param ctx: An instance of request context.
        :param req: An instance of the ClusterListRequest.
        :return: A list of `Cluster` object representations.
        """
        req.obj_set_defaults()
        if not req.project_safe and not ctx.is_admin:
            raise exception.Forbidden()

        query = {'project_safe': req.project_safe}
        if req.obj_attr_is_set('limit'):
            query['limit'] = req.limit
        if req.obj_attr_is_set('marker'):
            query['marker'] = req.marker
        if req.obj_attr_is_set('sort') and req.sort is not None:
            query['sort'] = req.sort
        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('status'):
            filters['status'] = req.status
        if filters:
            query['filters'] = filters

        return [c.to_dict()
                for c in cluster_mod.Cluster.load_all(ctx, **query)]

    @request_context2
    def cluster_get2(self, context, req):
        """Retrieve the cluster specified.

        :param context: An instance of the request context.
        :param req: An instance of the ClusterGetRequest.
        :return: A dictionary containing the details about a cluster.
        """
        db_cluster = self.cluster_find(context, req.identity)
        cluster = cluster_mod.Cluster.load(context, dbcluster=db_cluster)
        return cluster.to_dict()

    def check_cluster_quota(self, context):
        """Validate the number of clusters created in a project.

        :param context: An instance of the request context.
        :return: None if cluster creation is okay, or an exception of type
                 `Forbbiden` if number of clusters reaches the maximum.
        """
        existing = cluster_obj.Cluster.count_all(context)
        maximum = CONF.max_clusters_per_project
        if existing >= maximum:
            raise exception.Forbidden()

    @request_context2
    def cluster_create2(self, ctx, req):
        """Create a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterCreateRequestBody object.
        :return: A dictionary containing the details about the cluster and the
                 ID of the action triggered by this operation.
        """
        self.check_cluster_quota(ctx)
        if CONF.name_unique:
            if cluster_obj.Cluster.get_by_name(ctx, req.name):
                msg = _("a cluster named '%s' already exists.") % req.name
                raise exception.BadRequest(msg=msg)

        try:
            db_profile = self.profile_find(ctx, req.profile_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        if req.obj_attr_is_set('desired_capacity'):
            desired = req.desired_capacity
        else:
            desired = None
        min_size = req.min_size if req.obj_attr_is_set('min_size') else None
        max_size = req.max_size if req.obj_attr_is_set('max_size') else None
        res = su.check_size_params(None, desired, min_size, max_size, True)
        if res:
            raise exception.BadRequest(msg=res)

        # set defaults to the request object
        req.obj_set_defaults()

        LOG.info(_LI("Creating cluster '%s'."), req.name)

        kwargs = {
            'min_size': req.min_size,
            'max_size': req.max_size,
            'timeout': req.timeout,
            'metadata': req.metadata,
            'user': ctx.user,
            'project': ctx.project,
            'domain': ctx.domain,
        }

        cluster = cluster_mod.Cluster(req.name, req.desired_capacity,
                                      db_profile.id, **kwargs)
        cluster.store(ctx)

        # Build an Action for cluster creation
        kwargs = {
            'name': 'cluster_create_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, cluster.id,
                                             consts.CLUSTER_CREATE, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Cluster create action queued: %s."), action_id)

        result = cluster.to_dict()
        result['action'] = action_id
        return result

    @request_context2
    def cluster_update2(self, ctx, req):
        """Update a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterUpdateRequest object.
        :return: A dictionary containing the details about the cluster and the
                 ID of the action triggered by this operation.
        """
        db_cluster = self.cluster_find(ctx, req.identity)
        cluster = cluster_mod.Cluster.load(ctx, dbcluster=db_cluster)
        if cluster.status == consts.CS_ERROR:
            msg = _('Updating a cluster in error state')
            LOG.error(msg)
            raise exception.FeatureNotSupported(feature=msg)

        LOG.info(_LI("Updating cluster '%s'."), req.identity)

        inputs = {}
        if (req.obj_attr_is_set(consts.CLUSTER_PROFILE) and
                req.profile_id is not None):
            old_profile = self.profile_find(ctx, cluster.profile_id)
            try:
                new_profile = self.profile_find(ctx, req.profile_id)
            except exception.ResourceNotFound as ex:
                msg = ex.enhance_msg('specified', ex)
                raise exception.BadRequest(msg=msg)

            if new_profile.type != old_profile.type:
                msg = _('Cannot update a cluster to a different profile type, '
                        'operation aborted.')
                raise exception.ProfileTypeNotMatch(message=msg)
            if old_profile.id != new_profile.id:
                inputs['new_profile_id'] = new_profile.id

        if (req.obj_attr_is_set(consts.CLUSTER_METADATA) and
                req.metadata != cluster.metadata):
            inputs['metadata'] = copy.deepcopy(req.metadata)

        if req.obj_attr_is_set(consts.CLUSTER_TIMEOUT):
            inputs['timeout'] = req.timeout

        if req.obj_attr_is_set(consts.CLUSTER_NAME):
            inputs['name'] = req.name

        if not inputs:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        kwargs = {
            'name': 'cluster_update_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, cluster.id,
                                             consts.CLUSTER_UPDATE, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Cluster update action queued: %s."), action_id)

        resp = cluster.to_dict()
        resp['action'] = action_id
        return resp

    @request_context2
    def cluster_delete2(self, ctx, req):
        """Delete the specified cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterDeleteRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI('Deleting cluster %s'), req.identity)

        # 'cluster' below is a DB object.
        cluster = self.cluster_find(ctx, req.identity)
        if cluster.status in [consts.CS_CREATING,
                              consts.CS_UPDATING,
                              consts.CS_DELETING,
                              consts.CS_RECOVERING]:
            raise exception.ActionInProgress(type='cluster', id=req.identity,
                                             status=cluster.status)

        containers = cluster.dependents.get('containers', None)
        if containers is not None and len(containers) > 0:
            reason = _("still depended by other clusters and/or nodes")
            raise exception.ResourceInUse(type='cluster', id=req.identity,
                                          reason=reason)

        policies = cp_obj.ClusterPolicy.get_all(ctx, cluster.id)
        if len(policies) > 0:
            msg = _('Cluster %(id)s cannot be deleted without having all '
                    'policies detached.') % {'id': req.identity}
            LOG.error(msg)
            reason = _("there is still policy(s) attached to it.")
            raise exception.ResourceInUse(type='cluster', id=req.identity,
                                          reason=reason)

        receivers = receiver_obj.Receiver.get_all(
            ctx, filters={'cluster_id': cluster.id})
        if len(receivers) > 0:
            msg = _('Cluster %(id)s cannot be deleted without having all '
                    'receivers deleted.') % {'id': req.identity}
            LOG.error(msg)
            reason = _("there is still receiver(s) associated with it.")
            raise exception.ResourceInUse(type='cluster', id=req.identity,
                                          reason=reason)

        params = {
            'name': 'cluster_delete_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, cluster.id,
                                             consts.CLUSTER_DELETE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster delete action queued: %s"), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_add_nodes2(self, context, req):
        """Add specified nodes to the specified cluster.

        :param context: An instance of the request context.
        :param req: An instance of the ClusterAddNodesRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Adding nodes '%(nodes)s' to cluster '%(cluster)s'."),
                 {'cluster': req.identity, 'nodes': req.nodes})

        db_cluster = self.cluster_find(context, req.identity)
        db_cluster_profile = self.profile_find(context,
                                               db_cluster.profile_id)
        cluster_profile_type = db_cluster_profile.type

        found = []
        not_found = []
        bad_nodes = []
        owned_nodes = []
        not_match_nodes = []
        for node in req.nodes:
            try:
                db_node = self.node_find(context, node)
                # Skip node in the same cluster already
                if db_node.status != consts.NS_ACTIVE:
                    bad_nodes.append(db_node.id)
                elif len(db_node.cluster_id) != 0:
                    owned_nodes.append(db_node.id)
                else:
                    # check profile type matching
                    db_node_profile = self.profile_find(context,
                                                        db_node.profile_id)
                    node_profile_type = db_node_profile.type
                    if node_profile_type != cluster_profile_type:
                        not_match_nodes.append(db_node.id)
                    else:
                        found.append(db_node.id)
            except exception.ResourceNotFound:
                not_found.append(node)
                pass

        error = None
        if len(not_match_nodes) > 0:
            error = _("Profile type of nodes %s does not match that of the "
                      "cluster.") % not_match_nodes
            LOG.error(error)
            raise exception.ProfileTypeNotMatch(message=error)
        elif len(owned_nodes) > 0:
            error = _("Nodes %s already owned by some cluster.") % owned_nodes
            LOG.error(error)
            raise exception.NodeNotOrphan(message=error)
        elif len(bad_nodes) > 0:
            error = _("Nodes are not ACTIVE: %s.") % bad_nodes
        elif len(not_found) > 0:
            error = _("Nodes not found: %s.") % not_found
        elif len(found) == 0:
            error = _("No nodes to add: %s.") % req.nodes

        if error is not None:
            LOG.error(error)
            raise exception.BadRequest(msg=error)

        target_size = db_cluster.desired_capacity + len(found)
        error = su.check_size_params(db_cluster, target_size, strict=True)
        if error:
            LOG.error(error)
            raise exception.BadRequest(msg=error)

        params = {
            'name': 'cluster_add_nodes_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {'nodes': found},
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_ADD_NODES,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster add nodes action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_del_nodes2(self, ctx, req):
        """Delete specified nodes from the named cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterDelNodesRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Deleting nodes '%(nodes)s' from cluster '%(cluster)s'."),
                 {'cluster': req.identity, 'nodes': req.nodes})
        db_cluster = self.cluster_find(ctx, req.identity)
        found = []
        not_found = []
        bad_nodes = []
        for node in req.nodes:
            try:
                db_node = self.node_find(ctx, node)
                if db_node.cluster_id != db_cluster.id:
                    bad_nodes.append(db_node.id)
                else:
                    found.append(db_node.id)
            except exception.ResourceNotFound:
                not_found.append(node)
                pass

        error = None
        if len(not_found):
            error = _("Nodes not found: %s.") % not_found
        elif len(bad_nodes):
            error = _("Nodes not members of specified cluster: "
                      "%s.") % bad_nodes
        elif len(found) == 0:
            error = _("No nodes specified.")

        if error is not None:
            LOG.error(error)
            raise exception.BadRequest(msg=error)

        target_size = db_cluster.desired_capacity - len(found)
        error = su.check_size_params(db_cluster, target_size, strict=True)
        if error:
            LOG.error(error)
            raise exception.BadRequest(msg=error)

        params = {
            'name': 'cluster_del_nodes_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'candidates': found,
                'count': len(found),
            },
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_DEL_NODES,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster delete nodes action queued: %s."), action_id)

        return {'action': action_id}

    def _validate_replace_nodes(self, ctx, cluster, nodes):
        """Validate the nodes specified in a replacement operation.

        :param ctx: The request context.
        :param cluster: The cluster object from the DB layer.
        :param nodes: A dictionary wherein each key is the identity of a node
                      to be replaced and the corresponding value is the
                      identity of a node as replacement.
        :returns: A dict containing the validated map of node substitutions.
        """
        # TODO(anyone): This should use profile_get
        profile = self.profile_find(ctx, cluster.profile_id)
        cluster_profile_type = profile.type

        found = {}
        not_member = []
        owned_nodes = []
        not_found_new = []
        not_found_old = []
        bad_nodes = []
        not_match_nodes = []
        for (old_node, new_node) in nodes.items():
            try:
                db_old_node = self.node_find(ctx, old_node)
            except exception.ResourceNotFound:
                not_found_old.append(old_node)
                continue

            try:
                db_new_node = self.node_find(ctx, new_node)
            except exception.ResourceNotFound:
                not_found_new.append(new_node)
                continue

            # TODO(anyone): replace the 'elif' below with 'if' directly
            if db_old_node.cluster_id != cluster.id:
                not_member.append(old_node)
            elif db_new_node.cluster_id:
                owned_nodes.append(new_node)
            elif db_new_node.status != consts.NS_ACTIVE:
                bad_nodes.append(new_node)
            else:
                # check the profile type
                # TODO(anyone): This should use profile_get
                node_profile = self.profile_find(ctx, db_new_node.profile_id)
                if cluster_profile_type != node_profile.type:
                    not_match_nodes.append(new_node)
                else:
                    found[db_old_node.id] = db_new_node.id

        # TODO(Anyone): since the above checking is already aggregating all
        # illegal node specifications, we should combine the error message
        # into a single one.
        msg = None
        if len(not_member) > 0:
            msg = _("The specified nodes %(n)s to be replaced are not "
                    "members of the cluster %(c)s.") % {'n': not_member,
                                                        'c': cluster.id}
        elif len(owned_nodes) > 0:
            msg = _("Nodes %s already member of a cluster.") % owned_nodes
            LOG.error(msg)
            raise exception.NodeNotOrphan(message=msg)
        elif len(bad_nodes) > 0:
            msg = _("Nodes are not ACTIVE: %s.") % bad_nodes
        elif len(not_match_nodes) > 0:
            msg = _("Profile type of nodes %s do not match that of the "
                    "cluster.") % not_match_nodes
            LOG.error(msg)
            raise exception.ProfileTypeNotMatch(message=msg)
        elif len(not_found_old) > 0:
            msg = _("Original nodes not found: %s.") % not_found_old
        elif len(not_found_new) > 0:
            msg = _("Replacement nodes not found: %s.") % not_found_new

        if msg is not None:
            LOG.error(msg)
            raise exception.BadRequest(msg=msg)

        return found

    @request_context2
    def cluster_replace_nodes2(self, ctx, req):
        """Replace the nodes in cluster with specified nodes

        :param ctx: An instance of the request context.
        :param req: An object of ClusterReplaceNodesRequest.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Replace nodes of the cluster '%s'."), req.identity)
        db_cluster = self.cluster_find(ctx, req.identity)

        nodes = self._validate_replace_nodes(ctx, db_cluster, req.nodes)
        kwargs = {
            'name': 'cluster_replace_nodes_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': nodes,
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_REPLACE_NODES,
                                             **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Cluster replace nodes action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_resize2(self, ctx, req):
        """Adjust cluster size parameters.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterResizeRequest object.

        :return: A dict containing the ID of an action fired.
        """
        adj_type = None
        number = None
        min_size = None
        max_size = None
        min_step = None
        strict = True

        if (req.obj_attr_is_set(consts.ADJUSTMENT_TYPE) and
                req.adjustment_type is not None):
            adj_type = req.adjustment_type
            if not req.obj_attr_is_set(consts.ADJUSTMENT_NUMBER):
                msg = _('Missing number value for size adjustment.')
                raise exception.BadRequest(msg=msg)

            if (req.adjustment_type == consts.EXACT_CAPACITY and
                    req.number <= 0):
                msg = _("The 'number' must be positive integer for adjustment "
                        "type '%s'.") % adj_type
                raise exception.BadRequest(msg=msg)

            if adj_type == consts.CHANGE_IN_PERCENTAGE:
                # min_step is only used (so checked) for this case
                if req.obj_attr_is_set(consts.ADJUSTMENT_MIN_STEP):
                    min_step = req.min_step
                number = req.number
            else:
                number = int(req.number)
        else:
            if (req.obj_attr_is_set(consts.ADJUSTMENT_NUMBER) and
                    req.number is not None):
                msg = _('Missing adjustment_type value for size adjustment.')
                LOG.error(msg)
                raise exception.BadRequest(msg=msg)

        if req.obj_attr_is_set(consts.ADJUSTMENT_MIN_SIZE):
            min_size = req.min_size
        if req.obj_attr_is_set(consts.ADJUSTMENT_MAX_SIZE):
            max_size = req.max_size
        if req.obj_attr_is_set(consts.ADJUSTMENT_STRICT):
            strict = req.strict

        db_cluster = self.cluster_find(ctx, req.identity)
        current = node_obj.Node.count_by_cluster(ctx, db_cluster.id)
        if adj_type is not None:
            desired = su.calculate_desired(current, adj_type, number, min_step)
        else:
            desired = None

        res = su.check_size_params(db_cluster, desired, min_size, max_size,
                                   strict)
        if res:
            raise exception.BadRequest(msg=res)

        fmt = _LI("Resizing cluster '%(cluster)s': type=%(adj_type)s, "
                  "number=%(number)s, min_size=%(min_size)s, "
                  "max_size=%(max_size)s, min_step=%(min_step)s, "
                  "strict=%(strict)s.")
        LOG.info(fmt, {'cluster': req.identity, 'adj_type': adj_type,
                       'number': number, 'min_size': min_size,
                       'max_size': max_size, 'min_step': min_step,
                       'strict': strict})

        params = {
            'name': 'cluster_resize_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                consts.ADJUSTMENT_TYPE: adj_type,
                consts.ADJUSTMENT_NUMBER: number,
                consts.ADJUSTMENT_MIN_SIZE: min_size,
                consts.ADJUSTMENT_MAX_SIZE: max_size,
                consts.ADJUSTMENT_MIN_STEP: min_step,
                consts.ADJUSTMENT_STRICT: strict
            }
        }
        action_id = action_mod.Action.create(
            ctx, db_cluster.id, consts.CLUSTER_RESIZE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster resize action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_scale_out2(self, ctx, req):
        """Inflate the size of a cluster by then given number (optional).

        :param ctx: Request context for the call.
        :param req: An instance of the ClusterScaleOutRequest object.
        :return: A dict with the ID of the action fired.
        """
        db_cluster = self.cluster_find(ctx, req.identity)
        if req.obj_attr_is_set('count'):
            if req.count == 0:
                err = _("Count for scale-out request cannot be 0.")
                raise exception.BadRequest(msg=err)

            err = su.check_size_params(db_cluster,
                                       db_cluster.desired_capacity + req.count)
            if err:
                raise exception.BadRequest(msg=err)

            LOG.info(_LI('Scaling out cluster %(name)s by %(delta)s nodes'),
                     {'name': req.identity, 'delta': req.count})
            inputs = {'count': req.count}
        else:
            LOG.info(_LI('Scaling out cluster %s'), db_cluster.name)
            inputs = {}

        params = {
            'name': 'cluster_scale_out_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_SCALE_OUT,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster Scale out action queued: %s"), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_scale_in2(self, ctx, req):
        """Deflate the size of a cluster by given number (optional).

        :param ctx: Request context for the call.
        :param req: An instance of the ClusterScaleOutRequest object.
        :return: A dict with the ID of the action fired.
        """
        db_cluster = self.cluster_find(ctx, req.identity)
        if req.obj_attr_is_set('count'):
            if req.count == 0:
                err = _("Count for scale-in request cannot be 0.")
                raise exception.BadRequest(msg=err)

            err = su.check_size_params(db_cluster,
                                       db_cluster.desired_capacity - req.count)
            if err:
                raise exception.BadRequest(msg=err)

            LOG.info(_LI('Scaling in cluster %(name)s by %(delta)s nodes'),
                     {'name': req.identity, 'delta': req.count})
            inputs = {'count': req.count}
        else:
            LOG.info(_LI('Scaling in cluster %s'), db_cluster.name)
            inputs = {}

        params = {
            'name': 'cluster_scale_in_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_SCALE_IN,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster Scale in action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_collect2(self, ctx, req):
        """Collect a certain attribute across a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterCollectRequest object.
        :return: A list containing values of attribute collected from all
                 nodes.
        """
        # validate 'path' string and return a parser,
        # The function may raise a BadRequest exception.
        parser = utils.get_path_parser(req.path)
        cluster = self.cluster_find(ctx, req.identity)
        nodes = node_mod.Node.load_all(ctx, cluster_id=cluster.id)
        attrs = []
        for node in nodes:
            info = node.to_dict()
            if node.physical_id:
                info['details'] = node.get_details(ctx)
            matches = [m.value for m in parser.find(info)]
            if matches:
                attrs.append({'id': node.id, 'value': matches[0]})

        return {'cluster_attributes': attrs}

    @request_context2
    def cluster_check2(self, ctx, req):
        """Check the status of a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterCheckRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Checking cluster '%s'."), req.identity)
        db_cluster = self.cluster_find(ctx, req.identity)
        # cope with cluster check request from engine internal
        if not ctx.user or not ctx.project:
            ctx.user = db_cluster.user
            ctx.project = db_cluster.project

        params = {
            'name': 'cluster_check_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': req.params if req.obj_attr_is_set('params') else {}
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_CHECK, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster check action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_recover2(self, ctx, req):
        """Recover a cluster to a healthy status.

        :param ctx: An instance of the request context.
        :param req: An instance of a ClusterRecoverRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Recovering cluster '%s'."), req.identity)
        db_cluster = self.cluster_find(ctx, req.identity)

        # cope with cluster check request from engine internal
        if not ctx.user or not ctx.project:
            ctx.user = db_cluster.user
            ctx.project = db_cluster.project

        params = {
            'name': 'cluster_recover_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': req.params if req.obj_attr_is_set('params') else {}
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_RECOVER, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster recover action queued: %s."), action_id)

        return {'action': action_id}

    def node_find(self, context, identity, project_safe=True):
        """Find a node with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a node.
        :param project_safe: A boolean indicating whether only nodes from the
                             same project as the requesting one are qualified
                             to be returned.
        :return: A DB object of Node or an exception of `ResourceNotFound` if
                 no matching object is found.
        """
        if uuidutils.is_uuid_like(identity):
            node = node_obj.Node.get(context, identity,
                                     project_safe=project_safe)
            if not node:
                node = node_obj.Node.get_by_name(context, identity,
                                                 project_safe=project_safe)
        else:
            node = node_obj.Node.get_by_name(context, identity,
                                             project_safe=project_safe)
            if not node:
                node = node_obj.Node.get_by_short_id(
                    context, identity, project_safe=project_safe)

        if node is None:
            raise exception.ResourceNotFound(type='node', id=identity)

        return node

    @request_context2
    def node_list2(self, ctx, req):
        """List node records matching the specified criteria.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeListRequest object.
        :return: A list of `Node` object representations.
        """
        req.obj_set_defaults()
        if not req.project_safe and not ctx.is_admin:
            raise exception.Forbidden()

        query = {'project_safe': req.project_safe}
        if req.obj_attr_is_set('limit'):
            query['limit'] = req.limit
        if req.obj_attr_is_set('marker'):
            query['marker'] = req.marker
        if req.obj_attr_is_set('sort') and req.sort is not None:
            query['sort'] = req.sort
        if req.obj_attr_is_set('cluster_id') and req.cluster_id:
            db_cluster = self.cluster_find(ctx, req.cluster_id)
            query['cluster_id'] = db_cluster.id

        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('status'):
            filters['status'] = req.status
        if filters:
            query['filters'] = filters

        nodes = node_mod.Node.load_all(ctx, **query)
        return [node.to_dict() for node in nodes]

    @request_context2
    def node_create2(self, ctx, req):
        """Create a node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeCreateRequestBody object.
        :return: A dictionary containing the details about the node and the
                 ID of the action triggered by this operation.
        """
        if CONF.name_unique:
            if node_obj.Node.get_by_name(ctx, req.name):
                msg = _("The node named (%(name)s) already exists."
                        ) % {"name": req.name}
                raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Creating node '%s'."), req.name)

        try:
            node_profile = self.profile_find(ctx, req.profile_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        req.obj_set_defaults()
        if req.cluster_id:
            try:
                db_cluster = self.cluster_find(ctx, req.cluster_id)
            except exception.ResourceNotFound as ex:
                msg = ex.enhance_msg('specified', ex)

                raise exception.BadRequest(msg=msg)

            cluster_id = db_cluster.id
            if node_profile.id != db_cluster.profile_id:
                cluster_profile = self.profile_find(ctx,
                                                    db_cluster.profile_id)
                if node_profile.type != cluster_profile.type:
                    msg = _('Node and cluster have different profile type, '
                            'operation aborted.')
                    LOG.error(msg)
                    raise exception.ProfileTypeNotMatch(message=msg)
            index = cluster_obj.Cluster.get_next_index(ctx, cluster_id)
        else:
            cluster_id = ''
            index = -1

        # Create a node instance
        kwargs = {
            'index': index,
            'role': req.role,
            'metadata': req.metadata,
            'user': ctx.user,
            'project': ctx.project,
            'domain': ctx.domain,
        }

        node = node_mod.Node(req.name, node_profile.id, cluster_id, ctx,
                             **kwargs)
        node.store(ctx)

        params = {
            'name': 'node_create_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, node.id,
                                             consts.NODE_CREATE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Node create action queued: %s."), action_id)

        result = node.to_dict()
        result['action'] = action_id
        return result

    @request_context2
    def node_get2(self, ctx, req):
        """Retrieve the node specified.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeGetRequestBody object.
        :return: A dictionary containing the detailed information about a node
                 or an exception of `ResourceNotFound` if no matching node
                 could be found.
        """
        req.obj_set_defaults()
        db_node = self.node_find(ctx, req.identity)
        node = node_mod.Node.load(ctx, db_node=db_node)
        res = node.to_dict()
        if req.show_details and node.physical_id:
            res['details'] = node.get_details(ctx)
        return res

    @request_context2
    def node_update2(self, ctx, req):
        """Update a node with new propertye values.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeUpdateRequest object.
        :return: A dictionary containing the updated representation of the
                 node along with the ID of the action triggered by this
                 request.
        """
        LOG.info(_LI("Updating node '%s'."), req.identity)

        db_node = self.node_find(ctx, req.identity)
        if req.obj_attr_is_set('profile_id') and req.profile_id is not None:
            try:
                db_profile = self.profile_find(ctx, req.profile_id)
            except exception.ResourceNotFound as ex:
                msg = ex.enhance_msg('specified', ex)
                raise exception.BadRequest(msg=msg)
            profile_id = db_profile.id

            # check if profile_type matches
            old_profile = self.profile_find(ctx, db_node.profile_id)
            if old_profile.type != db_profile.type:
                msg = _('Cannot update a node to a different profile type, '
                        'operation aborted.')
                LOG.error(msg)
                raise exception.ProfileTypeNotMatch(message=msg)

            inputs = {'new_profile_id': profile_id}
        else:
            inputs = {}

        if req.obj_attr_is_set('name') and req.name:
            if req.name != db_node.name:
                inputs['name'] = req.name
        if req.obj_attr_is_set('role') and req.role != db_node.role:
            inputs['role'] = req.role
        if req.obj_attr_is_set('metadata'):
            if req.metadata != db_node.metadata:
                inputs['metadata'] = req.metadata

        if not inputs:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'node_update_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, db_node.id,
                                             consts.NODE_UPDATE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Node update action is queued: %s."), action_id)

        node = node_mod.Node.load(ctx, db_node=db_node)
        resp = node.to_dict()
        resp['action'] = action_id

        return resp

    @request_context2
    def node_delete2(self, ctx, req):
        """Delete the specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeDeleteRequest object.
        :return: A dictionary containing the ID of the action triggered by
                 this request.
        """
        LOG.info(_LI('Deleting node %s'), req.identity)

        node = self.node_find(ctx, req.identity)

        if node.status in [consts.NS_CREATING,
                           consts.NS_UPDATING,
                           consts.NS_DELETING,
                           consts.NS_RECOVERING]:
            raise exception.ActionInProgress(type='node', id=req.identity,
                                             status=node.status)

        containers = node.dependents.get('containers', None)
        if containers is not None and len(containers) > 0:
            reason = _("still depended by other clusters and/or nodes")
            raise exception.ResourceInUse(type='node', id=req.identity,
                                          reason=reason)

        params = {
            'name': 'node_delete_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, node.id,
                                             consts.NODE_DELETE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Node delete action is queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def node_check2(self, ctx, req):
        """Check the health status of specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeCheckRequest object.
        :return: A dictionary containing the ID of the action triggered by
                 this request.
        """
        LOG.info(_LI("Checking node '%s'."), req.identity)

        db_node = self.node_find(ctx, req.identity)

        kwargs = {
            'name': 'node_check_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY
        }
        if req.obj_attr_is_set('params') and req.params:
            kwargs['inputs'] = req.params
        action_id = action_mod.Action.create(ctx, db_node.id,
                                             consts.NODE_CHECK, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Node check action is queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def node_recover2(self, ctx, req):
        """Recover the specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeRecoverRequest object.
        :return: A dictionary containing the ID of the action triggered by the
                 recover request.
        """
        LOG.info(_LI("Recovering node '%s'."), req.identity)

        db_node = self.node_find(ctx, req.identity)

        kwargs = {
            'name': 'node_recover_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY
        }
        if req.obj_attr_is_set('params') and req.params:
            kwargs['inputs'] = req.params
        action_id = action_mod.Action.create(ctx, db_node.id,
                                             consts.NODE_RECOVER, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Node recover action is queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_policy_list(self, context, identity, filters=None, sort=None):
        """List cluster-policy bindings given the cluster identity.

        :param context: An instance of the request context.
        :param identity: The ID, name or short ID of the target cluster.
        :param filters: A list of key-value pairs for filtering out the result
                        list.
        :param sort: A list of sorting keys (optionally appended with sorting
                     directions) separated by commas.
        :return: A list containing dictionaries each representing a binding.
        """
        utils.validate_sort_param(sort, consts.CLUSTER_POLICY_SORT_KEYS)
        db_cluster = self.cluster_find(context, identity)
        bindings = cpm.ClusterPolicy.load_all(
            context, db_cluster.id, filters=filters, sort=sort)

        return [binding.to_dict() for binding in bindings]

    @request_context
    def cluster_policy_get(self, context, identity, policy_id):
        """Get the binding record giving the cluster and policy identity.

        :param context: An instance of the request context.
        :param identity: The ID, name or short ID of the target cluster.
        :param policy_id: The ID, name or short ID of the target policy.
        :return: A dictionary containing the binding record, or raises an
                 exception of ``PolicyNotAttached``.
        """
        db_cluster = self.cluster_find(context, identity)
        db_policy = self.policy_find(context, policy_id)

        try:
            binding = cpm.ClusterPolicy.load(
                context, db_cluster.id, db_policy.id)
        except exception.PolicyNotAttached:
            raise exception.PolicyBindingNotFound(policy=policy_id,
                                                  identity=identity)

        return binding.to_dict()

    @request_context2
    def cluster_policy_attach2(self, ctx, req):
        """Attach a policy to the specified cluster.

        This is done via an action because a cluster lock is needed.

        :param ctx: An instance of request context.
        :param req: An instance of the ClusterAttachPolicyRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        LOG.info(_LI("Attaching policy (%(policy)s) to cluster "
                     "(%(cluster)s)."),
                 {'policy': req.policy_id, 'cluster': req.identity})

        db_cluster = self.cluster_find(ctx, req.identity)
        try:
            db_policy = self.policy_find(ctx, req.policy_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        req.obj_set_defaults()

        params = {
            'name': 'attach_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'policy_id': db_policy.id,
                'enabled': utils.parse_bool_param('enabled', req.enabled),
            }
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_ATTACH_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Policy attach action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_policy_detach2(self, ctx, req):
        """Detach a policy from the specified cluster.

        This is done via an action because cluster lock is needed.

        :param ctx: An instance of request context.
        :param req: An instance of the ClusterDetachPolicyRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        LOG.info(_LI("Detaching policy '%(policy)s' from cluster "
                     "'%(cluster)s'."),
                 {'policy': req.policy_id, 'cluster': req.identity})

        db_cluster = self.cluster_find(ctx, req.identity)
        try:
            db_policy = self.policy_find(ctx, req.policy_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        binding = cp_obj.ClusterPolicy.get(ctx, db_cluster.id, db_policy.id)
        if binding is None:
            msg = _("The policy (%(p)s) is not attached to the specified "
                    "cluster (%(c)s)."
                    ) % {'p': req.policy_id, 'c': req.identity}
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'detach_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {'policy_id': db_policy.id},
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_DETACH_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Policy dettach action queued: %s."), action_id)

        return {'action': action_id}

    @request_context2
    def cluster_policy_update2(self, ctx, req):
        """Update an existing policy binding on a cluster.

        This is done via an action because cluster lock is needed.

        :param context: An instance of request context.
        :param req: An instance of the ClusterUpdatePolicyRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        LOG.info(_LI("Updating policy '%(policy)s' on cluster '%(cluster)s.'"),
                 {'policy': req.policy_id, 'cluster': req.identity})

        db_cluster = self.cluster_find(ctx, req.identity)
        try:
            db_policy = self.policy_find(ctx, req.policy_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        binding = cp_obj.ClusterPolicy.get(ctx, db_cluster.id, db_policy.id)
        if binding is None:
            msg = _("The policy (%(p)s) is not attached to the specified "
                    "cluster (%(c)s)."
                    ) % {'p': req.policy_id, 'c': req.identity}
            raise exception.BadRequest(msg=msg)

        inputs = {'policy_id': db_policy.id}
        if req.obj_attr_is_set('enabled'):
            inputs['enabled'] = req.enabled

        params = {
            'name': 'update_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_UPDATE_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Policy update action queued: %s."), action_id)

        return {'action': action_id}

    def action_find(self, context, identity, project_safe=True):
        """Find an action with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an action.
        :return: A DB object of action or an exception `ResourceNotFound` if
                 no matching action is found.
        """
        if uuidutils.is_uuid_like(identity):
            action = action_obj.Action.get(context, identity,
                                           project_safe=project_safe)
            if not action:
                action = action_obj.Action.get_by_name(
                    context, identity, project_safe=project_safe)
        else:
            action = action_obj.Action.get_by_name(
                context, identity, project_safe=project_safe)
            if not action:
                action = action_obj.Action.get_by_short_id(
                    context, identity, project_safe=project_safe)

        if not action:
            raise exception.ResourceNotFound(type='action', id=identity)

        return action

    @request_context
    def action_list(self, context, filters=None, limit=None, marker=None,
                    sort=None, project_safe=True):
        """List action records matching the specified criteria.

        :param context: An instance of the request context.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param limit: An integer specifying the maximum number of objects to
                      return in a response.
        :param marker: An UUID specifying the action after which the result
                       list starts.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param project_safe: A boolean indicating whether actions from all
                             projects will be returned.
        :return: A list of `Action` object representations.
        """
        limit = utils.parse_int_param('limit', limit)
        utils.validate_sort_param(sort, consts.ACTION_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()
        results = action_mod.Action.load_all(context, filters=filters,
                                             limit=limit, marker=marker,
                                             sort=sort,
                                             project_safe=project_safe)

        return [a.to_dict() for a in results]

    @request_context2
    def action_list2(self, ctx, req):
        """List action records matching the specified criteria.

        :param ctx: An instance of the request context.
        :param req: An instance of the ActionListRequest object.
        :return: A list of `Action` object representations.
        """

        req.obj_set_defaults()
        if not req.project_safe and not ctx.is_admin:
            raise exception.Forbidden()

        query = {'project_safe': req.project_safe}
        if req.obj_attr_is_set('limit'):
            query['limit'] = req.limit
        if req.obj_attr_is_set('marker'):
            query['marker'] = req.marker
        if req.obj_attr_is_set('sort') and req.sort is not None:
            query['sort'] = req.sort

        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('action'):
            filters['action'] = req.action
        if req.obj_attr_is_set('target'):
            filters['target'] = req.target
        if req.obj_attr_is_set('status'):
            filters['status'] = req.status
        if filters:
            query['filters'] = filters
        results = action_mod.Action.load_all(ctx, **query)

        return [a.to_dict() for a in results]

    @request_context
    def action_create(self, context, name, cluster, action, inputs=None):
        """Create an action with given details.

        :param context: Request context instance.
        :param name: Name of the action.
        :param cluster: Name, ID or short ID of the targeted cluster.
        :param action: String representation of the action.
        :param inputs: Optional inputs for the action.
        :return: A dict containing the action created.
        """
        LOG.info(_LI("Creating action '%s'."), name)

        target = self.cluster_find(context, cluster)

        # Create an action instance
        params = {
            'name': name,
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs or {},
        }
        action_id = action_mod.Action.create(context, target.id, action,
                                             **params)

        # TODO(Anyone): Uncomment this to notify the dispatcher
        # dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Action '%(name)s' is created: %(id)s."),
                 {'name': name, 'id': action_id})
        return {'action': action_id}

    @request_context
    def action_get(self, context, identity):
        """Get the details about specified action.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an action.
        :return: A dictionary containing the details about an action, or an
                 exception `ResourceNotFound` if no matching action is found.
        """
        db_action = self.action_find(context, identity)
        action = action_mod.Action.load(context, db_action=db_action)
        return action.to_dict()

    @request_context2
    def action_get2(self, ctx, req):
        """Retrieve the action specified.

        :param ctx: An instance of the request context.
        :param req: An instance of the ActionGetRequest object.
        :return: A dictionary containing the detailed information about a
                 action or an exception of `ResourceNotFound` if no matching
                 action could be found.
        """

        db_action = self.action_find(ctx, req.identity)
        action = action_mod.Action.load(ctx, db_action=db_action)

        return action.to_dict()

    @request_context
    def action_delete(self, context, identity):
        """Delete the specified action object.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an action object.
        :return: None if deletion was successful, or an exception of type
                 `ResourceInUse`.
        """
        db_action = self.action_find(context, identity)
        LOG.info(_LI("Deleting action '%s'."), identity)
        try:
            action_mod.Action.delete(context, db_action.id)
        except exception.EResourceBusy:
            reason = _("still in one of WAITING, RUNNING or SUSPENDED state")
            raise exception.ResourceInUse(type='action', id=identity,
                                          reason=reason)

        LOG.info(_LI("Action '%s' is deleted."), identity)

    def receiver_find(self, context, identity, project_safe=True):
        """Find a receiver with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :param project_safe: A boolean indicating whether receiver from other
                             projects other than the requesting one can be
                             returned.
        :return: A DB object of receiver or an exception `ResourceNotFound`
                 if no matching receiver is found.
        """
        if uuidutils.is_uuid_like(identity):
            receiver = receiver_obj.Receiver.get(
                context, identity, project_safe=project_safe)
            if not receiver:
                receiver = receiver_obj.Receiver.get_by_name(
                    context, identity, project_safe=project_safe)
        else:
            receiver = receiver_obj.Receiver.get_by_name(
                context, identity, project_safe=project_safe)
            if not receiver:
                receiver = receiver_obj.Receiver.get_by_short_id(
                    context, identity, project_safe=project_safe)

        if not receiver:
            raise exception.ResourceNotFound(type='receiver', id=identity)

        return receiver

    @request_context2
    def receiver_list2(self, ctx, req):
        """List receivers matching the specified criteria.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverListRequestBody object.
        :return: A list of `Receiver` object representations.
        """
        req.obj_set_defaults()
        if not req.project_safe and not ctx.is_admin:
            raise exception.Forbidden()

        query = {'project_safe': req.project_safe}
        if req.obj_attr_is_set('limit'):
            query['limit'] = req.limit
        if req.obj_attr_is_set('marker'):
            query['marker'] = req.marker
        if req.obj_attr_is_set('sort') and req.sort is not None:
            query['sort'] = req.sort

        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('type'):
            filters['type'] = req.type
        if req.obj_attr_is_set('action'):
            filters['action'] = req.action
        if req.obj_attr_is_set('cluster_id'):
            filters['cluster_id'] = req.cluster_id
        if filters:
            query['filters'] = filters

        receivers = receiver_mod.Receiver.load_all(ctx, **query)
        return [r.to_dict() for r in receivers]

    @request_context2
    def receiver_create2(self, ctx, req):
        """Create a receiver.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverCreateRequestBody object.
        :return: A dictionary containing the details about the receiver
                 created.
        """
        if CONF.name_unique:
            if receiver_obj.Receiver.get_by_name(ctx, req.name):
                msg = _("A receiver named '%s' already exists.") % req.name
                raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Creating %(t)s receiver %(n)s."),
                 {'n': req.name, 't': req.type})

        req.obj_set_defaults()
        # Sanity check for webhook target
        cluster = None
        action = None
        if req.type == consts.RECEIVER_WEBHOOK:
            if not req.obj_attr_is_set('cluster_id') or req.cluster_id is None:
                msg = _("Cluster identity is required for creating "
                        "webhook receiver.")
                raise exception.BadRequest(msg=msg)

            if not req.obj_attr_is_set('action') or req.action is None:
                msg = _("Action name is required for creating webhook "
                        "receiver.")
                raise exception.BadRequest(msg=msg)
            action = req.action

            # Check whether cluster identified by cluster_id does exist
            try:
                cluster = self.cluster_find(ctx, req.cluster_id)
            except exception.ResourceNotFound as ex:
                msg = ex.enhance_msg('referenced', ex)
                raise exception.BadRequest(msg=msg)

            # permission checking
            if not ctx.is_admin and ctx.user != cluster.user:
                raise exception.Forbidden()

        kwargs = {
            'name': req.name,
            'user': ctx.user,
            'project': ctx.project,
            'domain': ctx.domain,
            'params': req.params
        }

        receiver = receiver_mod.Receiver.create(ctx, req.type, cluster,
                                                action, **kwargs)
        LOG.info(_LI("Receiver (%(n)s) is created: %(i)s."),
                 {'n': req.name, 'i': receiver.id})

        return receiver.to_dict()

    @request_context2
    def receiver_get2(self, ctx, req):
        """Get the details about a receiver.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverGetRequestBody object.
        :return: A dictionary containing the details about a receiver or
                 an exception `ResourceNotFound` if no matching object found.
        """
        db_receiver = self.receiver_find(ctx, req.identity)
        receiver = receiver_mod.Receiver.load(ctx,
                                              receiver_obj=db_receiver)
        return receiver.to_dict()

    @request_context
    def receiver_delete(self, context, identity):
        """Delete the specified receiver.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :return: None if successfully deleted the receiver or an exception of
                 `ResourceNotFound` if the object could not be found.
        """
        db_receiver = self.receiver_find(context, identity)
        LOG.info(_LI("Deleting receiver %s."), identity)
        receiver_mod.Receiver.delete(context, db_receiver.id)
        LOG.info(_LI("Receiver %s is deleted."), identity)

    @request_context
    def receiver_notify(self, context, identity, params=None):
        """Handle notification to specified receiver.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :param params: Parameters received from notification.
        """
        db_receiver = self.receiver_find(context, identity)
        # permission checking
        if not context.is_admin and context.user != db_receiver.user:
            raise exception.Forbidden()

        # Receiver type check
        if db_receiver.type != consts.RECEIVER_MESSAGE:
            raise exception.Forbidden()

        LOG.info(_LI("Received notification to receiver %s."), identity)
        receiver = receiver_mod.Receiver.load(context,
                                              receiver_obj=db_receiver,
                                              project_safe=True)
        receiver.notify(context, params)

    @request_context
    def webhook_trigger(self, context, identity, params=None):

        LOG.info(_LI("Triggering webhook (%s)."), identity)
        receiver = self.receiver_find(context, identity)

        try:
            cluster = self.cluster_find(context, receiver.cluster_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('referenced', ex)
            raise exception.BadRequest(msg=msg)

        data = copy.deepcopy(receiver.params)
        if params:
            data.update(params)

        kwargs = {
            'name': 'webhook_%s' % receiver.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': data,
        }
        action_id = action_mod.Action.create(context, cluster.id,
                                             receiver.action, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Webhook %(w)s' triggered with action queued: %(a)s."),
                 {'w': identity, 'a': action_id})

        return {'action': action_id}

    def event_find(self, context, identity, project_safe=True):
        """Find an event with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the event.
        :param project_safe: A boolean specifying that only events from the
                             same project as the requesting one are qualified
                             to be returned.
        :return: A dictionary containing the details of the event.
        """
        event = None
        if uuidutils.is_uuid_like(identity):
            event = event_obj.Event.get(context, identity,
                                        project_safe=project_safe)
        if not event:
            event = event_obj.Event.get_by_short_id(context, identity,
                                                    project_safe=project_safe)
        if not event:
            raise exception.ResourceNotFound(type='event', id=identity)

        return event

    @request_context
    def event_list(self, context, filters=None, limit=None, marker=None,
                   sort=None, project_safe=True):
        """List event records matching the specified criteria.

        :param context: An instance of the request context.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param limit: An integer specifying the maximum number of objects to
                      return in a response.
        :param marker: An UUID specifying the event after which the result
                       list starts.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param project_safe: A boolean indicating whether events from all
                             projects will be returned.
        :return: A list of `Event` object representations.
        """
        limit = utils.parse_int_param('limit', limit)
        utils.validate_sort_param(sort, consts.EVENT_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()

        if filters and consts.EVENT_LEVEL in filters:
            value = filters.pop(consts.EVENT_LEVEL)
            value = utils.parse_level_values(value)
            if value is not None:
                filters[consts.EVENT_LEVEL] = value

        all_events = event_obj.Event.get_all(context, filters=filters,
                                             limit=limit, marker=marker,
                                             sort=sort,
                                             project_safe=project_safe)
        results = []
        for event in all_events:
            evt = event.as_dict()
            level = utils.level_from_number(evt['level'])
            evt['level'] = level
            results.append(evt)

        return results

    @request_context
    def event_get(self, context, identity):
        """Get the details about a specified event.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an event.
        :return: A dictionary containing the details about the event or an
                 exception of `ResourceNotFound` if no matching record could
                 be found.
        """
        db_event = self.event_find(context, identity)
        evt = db_event.as_dict()
        level = utils.level_from_number(evt['level'])
        evt['level'] = level

        return evt
