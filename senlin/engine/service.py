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
from senlin.common.i18n import _
from senlin.common import messaging as rpc_messaging
from senlin.common import scaleutils as su
from senlin.common import schema
from senlin.common import utils
from senlin.engine.actions import base as action_mod
from senlin.engine.actions import cluster_action as cluster_action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import event as EVENT
from senlin.engine import health_manager
from senlin.engine import node as node_mod
from senlin.engine.receivers import base as receiver_mod
from senlin.engine import scheduler
from senlin.objects import action as action_obj
from senlin.objects import base as obj_base
from senlin.objects import cluster as co
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

    def __init__(self, host, topic):

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
        EVENT.load_dispatcher()

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
        LOG.info("Starting dispatcher for engine %s", self.engine_id)
        self.dispatcher.start()

        target = oslo_messaging.Target(version=consts.RPC_API_VERSION,
                                       server=self.host,
                                       topic=self.topic)
        serializer = obj_base.VersionedObjectSerializer()
        self._rpc_server = rpc_messaging.get_rpc_server(
            target, self, serializer=serializer)
        self._rpc_server.start()

        # create service record
        ctx = senlin_context.get_admin_context()
        service_obj.Service.create(ctx, self.engine_id, self.host,
                                   'senlin-engine', self.topic)

        # create a health manager RPC service for this engine.
        self.health_mgr = health_manager.HealthManager(
            self, self.health_mgr_topic, consts.RPC_API_VERSION)

        LOG.info("Starting health manager for engine %s", self.engine_id)
        self.health_mgr.start()

        # we may want to make the clean-up attempts configurable.
        self.cleanup_timer = self.TG.add_timer(2 * CONF.periodic_interval,
                                               self.service_manage_cleanup)

        self.TG.add_timer(CONF.periodic_interval, self.service_manage_report)
        super(EngineService, self).start()

    def _stop_rpc_server(self):
        # Stop RPC connection to prevent new requests
        LOG.info("Stopping engine service...")
        try:
            self._rpc_server.stop()
            self._rpc_server.wait()
            LOG.info('Engine service stopped successfully')
        except Exception as ex:
            LOG.error('Failed to stop engine service: %s',
                      six.text_type(ex))

    def stop(self):
        self._stop_rpc_server()

        # Notify dispatcher to stop all action threads it started.
        LOG.info("Stopping dispatcher for engine %s", self.engine_id)
        self.dispatcher.stop()

        # Notify health_manager to stop
        LOG.info("Stopping health manager for engine %s", self.engine_id)
        self.health_mgr.stop()

        self.TG.stop()

        service_obj.Service.delete(self.engine_id)
        LOG.info('Engine %s is deleted', self.engine_id)

        super(EngineService, self).stop()

    def service_manage_report(self):
        ctx = senlin_context.get_admin_context()
        service_obj.Service.update(ctx, self.engine_id)

    def _service_manage_cleanup(self):
        ctx = senlin_context.get_admin_context()
        time_window = (2 * CONF.periodic_interval)
        svcs = service_obj.Service.get_all(ctx)
        for svc in svcs:
            if svc['id'] == self.engine_id:
                continue
            if timeutils.is_older_than(svc['updated_at'], time_window):
                LOG.info('Service %s was aborted', svc['id'])
                LOG.info('Breaking locks for dead engine %s', svc['id'])
                service_obj.Service.gc_by_engine(svc['id'])
                LOG.info('Done breaking locks for engine %s', svc['id'])
                service_obj.Service.delete(svc['id'])

    def service_manage_cleanup(self):
        self._service_manage_cleanup()
        self.cleanup_count += 1
        LOG.info('Service clean-up attempt count: %s', self.cleanup_count)
        if self.cleanup_count >= 2:
            self.cleanup_timer.stop()
            LOG.info("Finished cleaning up dead services.")

    @request_context
    def credential_create(self, ctx, req):
        """Create the credential based on the context.

        We may add more parameters in future to the query parameter, for
        example as Senlin expands its support to non-OpenStack backends.

        :param ctx: An instance of the request context.
        :param req: An instance of the CredentialCreateRequest.
        :return: A dictionary containing the persistent credential.
        """
        values = {
            'user': ctx.user_id,
            'project': ctx.project_id,
            'cred': req.cred
        }
        cred_obj.Credential.update_or_create(ctx, values)
        return {'cred': req.cred}

    @request_context
    def credential_get(self, ctx, req):
        """Get the credential based on the context.

        We may add more parameters in future to the req.query, for
        example as Senlin expands its support to non-OpenStack backends.

        :param ctx: An instance of the request context.
        :param req: An instance of the CredentialGetRequest.
        :return: A dictionary containing the persistent credential, or None
            if no matching credential is found.
        """
        res = cred_obj.Credential.get(ctx, req.user, req.project)
        if res is None:
            return None
        return res.cred.get('openstack', None)

    @request_context
    def credential_update(self, ctx, req):
        """Update a credential based on the context and provided value.

        We may add more parameters in future to the query parameter, for
        example as Senlin expands its support to non-OpenStack backends.

        :param ctx: An instance of the request context.
        :param req: An instance of the CredentialUpdateRequest.
        :return: A dictionary containing the persistent credential.
        """
        cred_obj.Credential.update(ctx, ctx.user_id, ctx.project_id,
                                   {'cred': req.cred})
        return {'cred': req.cred}

    @request_context
    def get_revision(self, ctx, req):
        return CONF.revision['senlin_engine_revision']

    @request_context
    def profile_type_list(self, ctx, req):
        """List known profile type implementations.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileTypeListRequest.
        :return: A list of profile types.
        """
        return environment.global_env().get_profile_types()

    @request_context
    def profile_type_get(self, ctx, req):
        """Get the details about a profile type.

        :param ctx: An instance of the request context.
        :param req: An instance of ProfileTypeGetRequest.
        :return: The details about a profile type.
        """
        profile = environment.global_env().get_profile(req.type_name)
        data = profile.get_schema()

        return {
            'name': req.type_name,
            'schema': data,
            'support_status': profile.VERSIONS
        }

    @request_context
    def profile_type_ops(self, ctx, req):
        """List the operations supported by a profile type.

        :param ctx: An instance of the request context.
        :param req: An instance of ProfileTypeOpListRequest.
        :return: A dictionary containing the operations supported by the
                 profile type.
        """
        try:
            pt = environment.global_env().get_profile(req.type_name)
        except exception.ResourceNotFound as ex:
            raise exception.BadRequest(msg=six.text_type(ex))

        return {'operations': pt.get_ops()}

    @request_context
    def profile_list(self, ctx, req):
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

        profiles = profile_obj.Profile.get_all(ctx, **query)
        return [p.to_dict() for p in profiles]

    def _validate_profile(self, ctx, spec, name=None,
                          metadata=None, validate_props=False):
        """Validate a profile.

        :param ctx: An instance of the request context.
        :param name: The name of the profile to be validated.
        :param spec: A dictionary containing the spec for the profile.
        :param metadata: A dictionary containing optional key-value pairs to
                         be associated with the profile.
        :param validate_props: Whether to validate if provide a valid Value
                               to property.
        :return: Validated profile object.
        """
        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        plugin = environment.global_env().get_profile(type_str)

        kwargs = {
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
            'metadata': metadata
        }
        if name is None:
            name = 'validated_profile'
        profile = plugin(name, spec, **kwargs)
        try:
            profile.validate(validate_props=validate_props)
        except exception.ESchema as ex:
            msg = six.text_type(ex)
            LOG.error("Failed in validating profile: %s", msg)
            raise exception.InvalidSpec(message=msg)

        return profile

    @request_context
    def profile_create(self, ctx, req):
        """Create a profile with the given properties.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileCreateRequest object.
        :return: A dictionary containing the details of the profile object
                 created.
        """
        name = req.profile.name
        if CONF.name_unique:
            if profile_obj.Profile.get_by_name(ctx, name):
                msg = _("A profile named '%(name)s' already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        metadata = {}
        if req.profile.obj_attr_is_set('metadata'):
            metadata = req.profile.metadata

        LOG.info("Creating profile '%s'.", name)

        # NOTE: we get the Profile subclass directly to ensure we are calling
        # the correct methods.
        type_name, version = schema.get_spec_version(req.profile.spec)
        type_str = "-".join([type_name, version])
        cls = environment.global_env().get_profile(type_str)
        profile = cls.create(ctx, name, req.profile.spec, metadata=metadata)

        LOG.info("Profile %(name)s is created: %(id)s.",
                 {'name': name, 'id': profile.id})

        return profile.to_dict()

    @request_context
    def profile_validate(self, ctx, req):
        """Validate a profile with the given properties.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileValidateRequest.
        :return: A dictionary containing the details of the profile object
                 validated.
        """
        profile = self._validate_profile(ctx, req.profile.spec,
                                         validate_props=True)

        return profile.to_dict()

    @request_context
    def profile_get(self, ctx, req):
        """Retrieve the details about a profile.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileGetRequest.
        :return: A dictionary containing the profile details, or an exception
                 of type `ResourceNotFound` if no matching object is found.
        """
        profile = profile_obj.Profile.find(ctx, req.identity)
        return profile.to_dict()

    @request_context
    def profile_update(self, ctx, req):
        """Update the properties of a given profile.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileUpdateRequest object.
        :returns: A dictionary containing the details of the updated profile,
                  or an exception `ResourceNotFound` if no matching profile is
                  found.
        """
        LOG.info("Updating profile '%(id)s.'", {'id': req.identity})
        db_profile = profile_obj.Profile.find(ctx, req.identity)
        profile = profile_base.Profile.load(ctx, profile=db_profile)
        changed = False
        if (req.profile.obj_attr_is_set('name') and
                req.profile.name is not None):
            if req.profile.name != profile.name:
                profile.name = req.profile.name
                changed = True
        if req.profile.obj_attr_is_set('metadata'):
            if req.profile.metadata != profile.metadata:
                profile.metadata = req.profile.metadata
                changed = True
        if changed:
            profile.store(ctx)
        else:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        LOG.info("Profile '%(id)s' is updated.", {'id': req.identity})
        return profile.to_dict()

    @request_context
    def profile_delete(self, ctx, req):
        """Delete the specified profile.

        :param ctx: An instance of the request context.
        :param req: An instance of the ProfileDeleteRequest.
        :return: None if succeeded or an exception of `ResourceInUse` if
                 profile is referenced by certain clusters/nodes.
        """
        db_profile = profile_obj.Profile.find(ctx, req.identity)
        LOG.info("Deleting profile '%s'.", req.identity)

        cls = environment.global_env().get_profile(db_profile.type)
        try:
            cls.delete(ctx, db_profile.id)
        except exception.EResourceBusy:
            reason = _("still referenced by some clusters and/or nodes.")
            raise exception.ResourceInUse(type='profile', id=db_profile.id,
                                          reason=reason)
        LOG.info("Profile '%s' is deleted.", req.identity)

    @request_context
    def policy_type_list(self, ctx, req):
        """List known policy type implementations.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyTypeListRequest.
        :return: A list of policy types.
        """
        return environment.global_env().get_policy_types()

    @request_context
    def policy_type_get(self, ctx, req):
        """Get the details about a policy type.

        :param ctx: An instance of the request context.
        :param req: An instance of PolicyTypeGetRequest.
        :return: The details about a policy type.
        """
        policy_type = environment.global_env().get_policy(req.type_name)
        data = policy_type.get_schema()

        return {
            'name': req.type_name,
            'schema': data,
            'support_status': policy_type.VERSIONS
        }

    @request_context
    def policy_list(self, ctx, req):
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

        return [p.to_dict() for p in policy_obj.Policy.get_all(ctx, **query)]

    def _validate_policy(self, ctx, spec, name=None, validate_props=False):
        """Validate a policy.

        :param ctx: An instance of the request context.
        :param spec: A dictionary containing the spec for the policy.
        :param name: The name of the policy to be validated.
        :param validate_props: Whether to validate the value of property.
        :return: Validated policy object.
        """

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])

        plugin = environment.global_env().get_policy(type_str)

        kwargs = {
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
        }
        if name is None:
            name = 'validated_policy'
        policy = plugin(name, spec, **kwargs)

        try:
            policy.validate(ctx, validate_props=validate_props)
        except exception.InvalidSpec as ex:
            msg = six.text_type(ex)
            LOG.error("Failed in validating policy: %s", msg)
            raise exception.InvalidSpec(message=msg)

        return policy

    @request_context
    def policy_create(self, ctx, req):
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

        policy = self._validate_policy(ctx, req.spec, name=name,
                                       validate_props=True)

        LOG.info("Creating policy %(type)s '%(name)s'",
                 {'type': policy.type, 'name': policy.name})

        policy.store(ctx)
        LOG.info("Policy '%(name)s' is created: %(id)s.",
                 {'name': name, 'id': policy.id})
        return policy.to_dict()

    @request_context
    def policy_get(self, ctx, req):
        """Retrieve the details about a policy.

        :param ctx: An instance of request context.
        :param req: An instance of the PolicyGetRequest.
        :return: A dictionary containing the policy details.
        """
        policy = policy_obj.Policy.find(ctx, req.identity)
        return policy.to_dict()

    @request_context
    def policy_update(self, ctx, req):
        """Update the properties of a given policy

        :param ctx: An instance of request context.
        :param req: An instance of the PolicyUpdateRequest.
        :return: A dictionary containing the policy details.
        """
        db_policy = policy_obj.Policy.find(ctx, req.identity)
        policy = policy_base.Policy.load(ctx, db_policy=db_policy)

        changed = False
        if (req.policy.name is not None and
                req.policy.name != policy.name):
            LOG.info("Updating policy '%s'.", req.identity)
            policy.name = req.policy.name
            changed = True
            policy.store(ctx)
            LOG.info("Policy '%s' is updated.", req.identity)

        if not changed:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        return policy.to_dict()

    @request_context
    def policy_delete(self, ctx, req):
        """Delete the specified policy.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyDeleteRequest.
        :return: None if succeeded or an exception of `ResourceInUse` if
                 policy is still attached to certain clusters.
        """
        db_policy = policy_obj.Policy.find(ctx, req.identity)
        LOG.info("Deleting policy '%s'.", req.identity)
        try:
            policy_base.Policy.delete(ctx, db_policy.id)
        except exception.EResourceBusy:
            reason = _("still attached to some clusters")
            raise exception.ResourceInUse(type='policy', id=req.identity,
                                          reason=reason)
        LOG.info("Policy '%s' is deleted.", req.identity)

    @request_context
    def policy_validate(self, ctx, req):
        """Validate a policy with the given properties.

        :param ctx: An instance of the request context.
        :param req: An instance of the PolicyValidateRequestBody.
        :return: A dictionary containing the details of the policy object
                 validated.
        """

        policy = self._validate_policy(ctx, req.spec, validate_props=False)

        return policy.to_dict()

    @request_context
    def cluster_list(self, ctx, req):
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

        return [c.to_dict() for c in co.Cluster.get_all(ctx, **query)]

    @request_context
    def cluster_get(self, context, req):
        """Retrieve the cluster specified.

        :param context: An instance of the request context.
        :param req: An instance of the ClusterGetRequest.
        :return: A dictionary containing the details about a cluster.
        """
        cluster = co.Cluster.find(context, req.identity)
        return cluster.to_dict()

    def check_cluster_quota(self, context):
        """Validate the number of clusters created in a project.

        :param context: An instance of the request context.
        :return: None if cluster creation is okay, or an exception of type
                 `Forbidden` if number of clusters reaches the maximum.
        """
        existing = co.Cluster.count_all(context)
        maximum = CONF.max_clusters_per_project
        if existing >= maximum:
            raise exception.Forbidden()

    @request_context
    def cluster_create(self, ctx, req):
        """Create a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterCreateRequestBody object.
        :return: A dictionary containing the details about the cluster and the
                 ID of the action triggered by this operation.
        """
        self.check_cluster_quota(ctx)
        if CONF.name_unique:
            if co.Cluster.get_by_name(ctx, req.name):
                msg = _("a cluster named '%s' already exists.") % req.name
                raise exception.BadRequest(msg=msg)

        try:
            db_profile = profile_obj.Profile.find(ctx, req.profile_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        if req.obj_attr_is_set('desired_capacity'):
            desired = req.desired_capacity
        elif req.obj_attr_is_set('min_size'):
            desired = req.min_size
        else:
            desired = 0
        min_size = req.min_size if req.obj_attr_is_set('min_size') else None
        max_size = req.max_size if req.obj_attr_is_set('max_size') else None
        res = su.check_size_params(None, desired, min_size, max_size, True)
        if res:
            raise exception.BadRequest(msg=res)

        # set defaults to the request object
        req.obj_set_defaults()

        LOG.info("Creating cluster '%s'.", req.name)

        values = {
            'name': req.name,
            'profile_id': db_profile.id,
            'desired_capacity': desired,
            'min_size': req.min_size or consts.CLUSTER_DEFAULT_MIN_SIZE,
            'max_size': req.max_size or consts.CLUSTER_DEFAULT_MAX_SIZE,
            'next_index': 1,
            'timeout': req.timeout or cfg.CONF.default_action_timeout,
            'status': consts.CS_INIT,
            'status_reason': 'Initializing',
            'data': {},
            'metadata': req.metadata or {},
            'dependents': {},
            'config': req.config or {},
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
        }
        cluster = co.Cluster.create(ctx, values)

        # Build an Action for cluster creation
        kwargs = {
            'name': 'cluster_create_%s' % cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, cluster.id,
                                             consts.CLUSTER_CREATE, **kwargs)
        dispatcher.start_action()
        LOG.info("Cluster create action queued: %s.", action_id)

        result = cluster.to_dict()
        result['action'] = action_id
        return result

    @request_context
    def cluster_update(self, ctx, req):
        """Update a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterUpdateRequest object.
        :return: A dictionary containing the details about the cluster and the
                 ID of the action triggered by this operation.
        """
        cluster = co.Cluster.find(ctx, req.identity)
        if cluster.status == consts.CS_ERROR:
            msg = _('Updating a cluster in error state')
            LOG.error(msg)
            raise exception.FeatureNotSupported(feature=msg)

        LOG.info("Updating cluster '%s'.", req.identity)

        inputs = {}
        if (req.obj_attr_is_set(consts.CLUSTER_PROFILE) and
                req.profile_id is not None):
            old_profile = profile_obj.Profile.find(ctx, cluster.profile_id)
            try:
                new_profile = profile_obj.Profile.find(ctx, req.profile_id)
            except exception.ResourceNotFound as ex:
                msg = ex.enhance_msg('specified', ex)
                raise exception.BadRequest(msg=msg)

            if new_profile.type != old_profile.type:
                msg = _('Cannot update a cluster to a different profile type, '
                        'operation aborted.')
                raise exception.BadRequest(msg=msg)
            if old_profile.id != new_profile.id:
                inputs['new_profile_id'] = new_profile.id

        if (req.obj_attr_is_set(consts.CLUSTER_METADATA) and
                req.metadata != cluster.metadata):
            inputs['metadata'] = copy.deepcopy(req.metadata)

        if (req.obj_attr_is_set(consts.CLUSTER_TIMEOUT) and
                req.timeout != cluster.timeout):
            inputs['timeout'] = req.timeout

        if (req.obj_attr_is_set(consts.CLUSTER_NAME) and
                req.name != cluster.name):
            inputs['name'] = req.name

        if (req.obj_attr_is_set(consts.CLUSTER_CONFIG) and
                req.config != cluster.config):
            # TODO(anyone): updating cluster config is a multiplexed operation
            # which have to be handled carefully.
            inputs['config'] = req.config

        if req.obj_attr_is_set(consts.CLUSTER_PROFILE_ONLY):
            inputs['profile_only'] = req.profile_only

        if not inputs:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        kwargs = {
            'name': 'cluster_update_%s' % cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, cluster.id,
                                             consts.CLUSTER_UPDATE, **kwargs)
        dispatcher.start_action()
        LOG.info("Cluster update action queued: %s.", action_id)

        resp = cluster.to_dict()
        resp['action'] = action_id
        return resp

    @request_context
    def cluster_delete(self, ctx, req):
        """Delete the specified cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterDeleteRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info('Deleting cluster %s', req.identity)

        # 'cluster' below is a DB object.
        cluster = co.Cluster.find(ctx, req.identity)

        force = False
        if req.obj_attr_is_set(consts.CLUSTER_DELETE_FORCE):
            force = req.force

        if (not force and
            cluster.status in [consts.CS_CREATING,
                               consts.CS_UPDATING,
                               consts.CS_DELETING,
                               consts.CS_RECOVERING]):
            raise exception.ActionInProgress(type='cluster', id=req.identity,
                                             status=cluster.status)

        # collect all errors
        msg = []
        con_profiles = cluster.dependents.get('profiles', None)
        if con_profiles is not None:
            err = _("still referenced by profile(s): %s") % con_profiles
            LOG.error(err)
            msg.append(err)

        policies = cp_obj.ClusterPolicy.get_all(ctx, cluster.id)
        if len(policies) > 0:
            err = _('Cluster %(id)s cannot be deleted without having all '
                    'policies detached.') % {'id': req.identity}
            LOG.error(err)
            msg.append(_("there is still policy(s) attached to it."))

        receivers = receiver_obj.Receiver.get_all(
            ctx, filters={'cluster_id': cluster.id})
        if len(receivers) > 0:
            err = _('Cluster %(id)s cannot be deleted without having all '
                    'receivers deleted.') % {'id': req.identity}
            LOG.error(err)
            msg.append(_("there is still receiver(s) associated with it."))

        if msg:
            raise exception.ResourceInUse(type='cluster', id=req.identity,
                                          reason='\n'.join(msg))

        params = {
            'name': 'cluster_delete_%s' % cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, cluster.id,
                                             consts.CLUSTER_DELETE, **params)
        dispatcher.start_action()
        LOG.info("Cluster delete action queued: %s", action_id)

        return {'action': action_id}

    @request_context
    def cluster_add_nodes(self, context, req):
        """Add specified nodes to the specified cluster.

        :param context: An instance of the request context.
        :param req: An instance of the ClusterAddNodesRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info("Adding nodes '%(nodes)s' to cluster '%(cluster)s'.",
                 {'cluster': req.identity, 'nodes': req.nodes})

        db_cluster = co.Cluster.find(context, req.identity)
        db_cluster_profile = profile_obj.Profile.get(
            context, db_cluster.profile_id, project_safe=True)
        cluster_profile_type = db_cluster_profile.type

        found = []
        not_found = []
        bad_nodes = []
        owned_nodes = []
        not_match_nodes = []
        for node in req.nodes:
            try:
                db_node = node_obj.Node.find(context, node)
                # Check node status whether in ACTIVE
                if db_node.status != consts.NS_ACTIVE:
                    bad_nodes.append(db_node.id)
                # Check the node whether owned by any cluster
                if db_node.cluster_id:
                    owned_nodes.append(db_node.id)
                # check profile type matching
                db_node_profile = profile_obj.Profile.get(
                    context, db_node.profile_id, project_safe=True)
                node_profile_type = db_node_profile.type
                if node_profile_type != cluster_profile_type:
                    not_match_nodes.append(db_node.id)

                found.append(db_node.id)
            except (exception.ResourceNotFound, exception.MultipleChoices):
                not_found.append(node)
                pass

        msg = []
        if len(not_match_nodes):
            msg.append(_("Profile type of nodes %s does not match that of the "
                         "cluster.") % not_match_nodes)
        if len(owned_nodes):
            msg.append(("Nodes %s already owned by some "
                        "cluster.") % owned_nodes)
        if len(bad_nodes):
            msg.append(_("Nodes are not ACTIVE: %s.") % bad_nodes)
        if len(not_found):
            msg.append(_("Nodes not found: %s.") % not_found)

        if msg:
            msg_err = '\n'.join(msg)
            LOG.error(msg_err)
            raise exception.BadRequest(msg=msg_err)

        target_size = db_cluster.desired_capacity + len(found)
        error = su.check_size_params(db_cluster, target_size, strict=True)
        if error:
            LOG.error(error)
            raise exception.BadRequest(msg=error)

        params = {
            'name': 'cluster_add_nodes_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {'nodes': found},
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_ADD_NODES,
                                             **params)
        dispatcher.start_action()
        LOG.info("Cluster add nodes action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_del_nodes(self, ctx, req):
        """Delete specified nodes from the named cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterDelNodesRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info("Deleting nodes '%(nodes)s' from cluster '%(cluster)s'.",
                 {'cluster': req.identity, 'nodes': req.nodes})
        db_cluster = co.Cluster.find(ctx, req.identity)
        found = []
        not_found = []
        bad_nodes = []
        depended_nodes = []
        for node in req.nodes:
            try:
                db_node = node_obj.Node.find(ctx, node)
                dep_nodes = db_node.dependents.get('nodes', None)
                if db_node.cluster_id != db_cluster.id:
                    bad_nodes.append(db_node.id)
                elif dep_nodes is not None:
                    depended_nodes.append(db_node.id)
                else:
                    found.append(db_node.id)
            except (exception.ResourceNotFound, exception.MultipleChoices):
                not_found.append(node)
                pass

        msg = []
        if len(depended_nodes):
            reason = _("nodes %s are depended by other nodes, so can't be "
                       "deleted or become orphan nodes") % depended_nodes
            LOG.error(reason)
            raise exception.ResourceInUse(type='node', id=depended_nodes,
                                          reason=reason)
        if len(not_found):
            msg.append(_("Nodes not found: %s.") % not_found)
        if len(bad_nodes):
            msg.append(_("Nodes not members of specified cluster: "
                         "%s.") % bad_nodes)

        if msg:
            msg_err = '\n'.join(msg)
            LOG.error(msg_err)
            raise exception.BadRequest(msg=msg_err)

        target_size = db_cluster.desired_capacity - len(found)
        error = su.check_size_params(db_cluster, target_size, strict=True)
        if error:
            LOG.error(error)
            raise exception.BadRequest(msg=error)

        params = {
            'name': 'cluster_del_nodes_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'candidates': found,
                'count': len(found),
            },
        }
        if 'destroy_after_deletion' in req:   # version 1.1
            params['inputs'].update(
                {'destroy_after_deletion': req.destroy_after_deletion})
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_DEL_NODES,
                                             **params)
        dispatcher.start_action()
        LOG.info("Cluster delete nodes action queued: %s.", action_id)

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
        profile = profile_obj.Profile.get(ctx, cluster.profile_id,
                                          project_safe=True)

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
                db_old_node = node_obj.Node.find(ctx, old_node)
            except (exception.ResourceNotFound, exception.MultipleChoices):
                not_found_old.append(old_node)
                continue

            try:
                db_new_node = node_obj.Node.find(ctx, new_node)
            except (exception.ResourceNotFound, exception.MultipleChoices):
                not_found_new.append(new_node)
                continue

            if db_old_node.cluster_id != cluster.id:
                not_member.append(old_node)
            if db_new_node.cluster_id:
                owned_nodes.append(new_node)
            if db_new_node.status != consts.NS_ACTIVE:
                bad_nodes.append(new_node)

            # check the profile type
            node_profile = profile_obj.Profile.get(ctx, db_new_node.profile_id,
                                                   project_safe=True)

            if cluster_profile_type != node_profile.type:
                not_match_nodes.append(new_node)

            found[db_old_node.id] = db_new_node.id

        msg = []
        if len(not_member) > 0:
            msg.append(_("The specified nodes %(n)s to be replaced are not "
                         "members of the cluster %(c)s.") % {'n': not_member,
                                                             'c': cluster.id})
        if len(owned_nodes) > 0:
            msg.append(_("Nodes %s already member of a "
                         "cluster.") % owned_nodes)
        if len(bad_nodes) > 0:
            msg.append(_("Nodes are not ACTIVE: %s.") % bad_nodes)
        if len(not_match_nodes) > 0:
            msg.append(_("Profile type of nodes %s do not match that of the "
                         "cluster.") % not_match_nodes)
        if len(not_found_old) > 0:
            msg.append(_("Original nodes not found: %s.") % not_found_old)
        if len(not_found_new) > 0:
            msg.append(_("Replacement nodes not found: %s.") % not_found_new)

        if msg:
            msg_err = '\n'.join(msg)
            LOG.error(msg_err)
            raise exception.BadRequest(msg=msg_err)

        return found

    @request_context
    def cluster_replace_nodes(self, ctx, req):
        """Replace the nodes in cluster with specified nodes

        :param ctx: An instance of the request context.
        :param req: An object of ClusterReplaceNodesRequest.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info("Replace nodes of the cluster '%s'.", req.identity)
        db_cluster = co.Cluster.find(ctx, req.identity)

        nodes = self._validate_replace_nodes(ctx, db_cluster, req.nodes)
        kwargs = {
            'name': 'cluster_replace_nodes_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': nodes,
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_REPLACE_NODES,
                                             **kwargs)
        dispatcher.start_action()
        LOG.info("Cluster replace nodes action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_resize(self, ctx, req):
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

        db_cluster = co.Cluster.find(ctx, req.identity)
        current = node_obj.Node.count_by_cluster(ctx, db_cluster.id)
        if adj_type is not None:
            desired = su.calculate_desired(current, adj_type, number, min_step)
        else:
            desired = None

        res = su.check_size_params(db_cluster, desired, min_size, max_size,
                                   strict)
        if res:
            raise exception.BadRequest(msg=res)

        fmt = _("Resizing cluster '%(cluster)s': type=%(adj_type)s, "
                "number=%(number)s, min_size=%(min_size)s, "
                "max_size=%(max_size)s, min_step=%(min_step)s, "
                "strict=%(strict)s.")
        LOG.info(fmt, {'cluster': req.identity, 'adj_type': adj_type,
                       'number': number, 'min_size': min_size,
                       'max_size': max_size, 'min_step': min_step,
                       'strict': strict})

        params = {
            'name': 'cluster_resize_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
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
        LOG.info("Cluster resize action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_scale_out(self, ctx, req):
        """Inflate the size of a cluster by then given number (optional).

        :param ctx: Request context for the call.
        :param req: An instance of the ClusterScaleOutRequest object.
        :return: A dict with the ID of the action fired.
        """
        db_cluster = co.Cluster.find(ctx, req.identity)
        if req.obj_attr_is_set('count'):
            if req.count == 0:
                err = _("Count for scale-out request cannot be 0.")
                raise exception.BadRequest(msg=err)

            err = su.check_size_params(db_cluster,
                                       db_cluster.desired_capacity + req.count)
            if err:
                raise exception.BadRequest(msg=err)

            LOG.info('Scaling out cluster %(name)s by %(delta)s nodes',
                     {'name': req.identity, 'delta': req.count})
            inputs = {'count': req.count}
        else:
            LOG.info('Scaling out cluster %s', db_cluster.name)
            inputs = {}

        params = {
            'name': 'cluster_scale_out_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_SCALE_OUT,
                                             **params)
        dispatcher.start_action()
        LOG.info("Cluster Scale out action queued: %s", action_id)

        return {'action': action_id}

    @request_context
    def cluster_scale_in(self, ctx, req):
        """Deflate the size of a cluster by given number (optional).

        :param ctx: Request context for the call.
        :param req: An instance of the ClusterScaleInRequest object.
        :return: A dict with the ID of the action fired.
        """
        db_cluster = co.Cluster.find(ctx, req.identity)
        if req.obj_attr_is_set('count'):
            if req.count == 0:
                err = _("Count for scale-in request cannot be 0.")
                raise exception.BadRequest(msg=err)

            err = su.check_size_params(db_cluster,
                                       db_cluster.desired_capacity - req.count)
            if err:
                raise exception.BadRequest(msg=err)

            LOG.info('Scaling in cluster %(name)s by %(delta)s nodes',
                     {'name': req.identity, 'delta': req.count})
            inputs = {'count': req.count}
        else:
            LOG.info('Scaling in cluster %s', db_cluster.name)
            inputs = {}

        params = {
            'name': 'cluster_scale_in_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_SCALE_IN,
                                             **params)
        dispatcher.start_action()
        LOG.info("Cluster Scale in action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_collect(self, ctx, req):
        """Collect a certain attribute across a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterCollectRequest object.
        :return: A dictionary containing values of attribute collected from all
                 nodes.
        """
        # validate 'path' string and return a parser,
        # The function may raise a BadRequest exception.
        parser = utils.get_path_parser(req.path)
        cluster = co.Cluster.find(ctx, req.identity)
        nodes = node_obj.Node.get_all_by_cluster(ctx, cluster.id)
        attrs = []
        for node in nodes:
            info = node.to_dict()
            if node.physical_id and 'details' in req.path:
                obj = node_mod.Node.load(ctx, db_node=node)
                info['details'] = obj.get_details(ctx)

            matches = [m.value for m in parser.find(info)]
            if matches:
                attrs.append({'id': node.id, 'value': matches[0]})

        return {'cluster_attributes': attrs}

    @request_context
    def cluster_check(self, ctx, req):
        """Check the status of a cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterCheckRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info("Checking cluster '%s'.", req.identity)
        db_cluster = co.Cluster.find(ctx, req.identity)
        # cope with cluster check request from engine internal
        if not ctx.user_id or not ctx.project_id:
            ctx.user_id = db_cluster.user
            ctx.project_id = db_cluster.project

        kwargs = {
            'name': 'cluster_check_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': req.params if req.obj_attr_is_set('params') else {}
        }
        need_delete = kwargs['inputs'].get('delete_check_action', False)
        # delete some records of CLUSTER_CHECK
        if need_delete:
            action_obj.Action.delete_by_target(
                ctx, db_cluster.id, action=[consts.CLUSTER_CHECK],
                status=[consts.ACTION_SUCCEEDED, consts.ACTION_FAILED])

        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_CHECK,
                                             **kwargs)
        dispatcher.start_action()
        LOG.info("Cluster check action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_recover(self, ctx, req):
        """Recover a cluster to a healthy status.

        :param ctx: An instance of the request context.
        :param req: An instance of a ClusterRecoverRequest object.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info("Recovering cluster '%s'.", req.identity)
        db_cluster = co.Cluster.find(ctx, req.identity)

        # cope with cluster check request from engine internal
        if not ctx.user_id or not ctx.project_id:
            ctx.user_id = db_cluster.user
            ctx.project_id = db_cluster.project

        inputs = {}
        if req.obj_attr_is_set('params') and req.params:
            if 'operation' in req.params:
                inputs['operation'] = req.params.pop('operation')

            if 'check' in req.params:
                inputs['check'] = req.params.pop('check')

            if 'check_capacity' in req.params:
                inputs['check_capacity'] = req.params.pop('check_capacity')

            if len(req.params):
                keys = [str(k) for k in req.params]
                msg = _("Action parameter %s is not recognizable.") % keys
                raise exception.BadRequest(msg=msg)

        # TODO(anyone): should check if the 'params' attribute, if set,
        # contains valid fields. This can be done by modeling the 'params'
        # attribute into a separate object.
        params = {
            'name': 'cluster_recover_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_RECOVER, **params)
        dispatcher.start_action()
        LOG.info("Cluster recover action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_complete_lifecycle(self, ctx, req):
        """Complete lifecycle for a cluster's action token

        :param ctx: Request context for the call.
        :param req: An instance of the ClusterCompleteLifecycle object.
        :return: A dict with the ID of the action fired.
        """

        LOG.info("Complete lifecycle for %s.", req.lifecycle_action_token)
        cluster_action_mod.CompleteLifecycleProc(ctx,
                                                 req.lifecycle_action_token)

        return {'action': req.lifecycle_action_token}

    @request_context
    def cluster_op(self, ctx, req):
        """Perform an operation on the specified cluster.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterOperationRequest object.
        :return: A dictionary containing the ID of the action triggered by the
                 recover request.
        """
        LOG.info("Performing operation '%(o)s' on cluster '%(n)s'.",
                 {'o': req.operation, 'n': req.identity})

        db_cluster = co.Cluster.find(ctx, req.identity)
        cluster = cluster_mod.Cluster.load(ctx, dbcluster=db_cluster)
        profile = cluster.rt['profile']
        if req.operation not in profile.OPERATIONS:
            msg = _("The requested operation '%(o)s' is not supported by the "
                    "profile type '%(t)s'."
                    ) % {'o': req.operation, 't': profile.type}
            raise exception.BadRequest(msg=msg)

        if req.obj_attr_is_set('params') and req.params:
            params = req.params
            try:
                profile.OPERATIONS[req.operation].validate(req.params)
            except exception.ESchema as ex:
                raise exception.BadRequest(msg=six.text_type(ex))
        else:
            params = {}

        if 'filters' in req and req.filters:
            errors = []
            for k in req.filters:
                if k not in (consts.NODE_NAME, consts.NODE_PROFILE_ID,
                             consts.NODE_STATUS, consts.NODE_ROLE):
                    errors.append(_("Filter key '%s' is unsupported") % k)
            if errors:
                raise exception.BadRequest(msg='\n'.join(errors))
            node_ids = node_obj.Node.ids_by_cluster(ctx, cluster.id,
                                                    filters=req.filters)
        else:
            node_ids = node_obj.Node.ids_by_cluster(ctx, cluster.id)

        if not node_ids:
            msg = _("No node (matching the filter) could be found")
            raise exception.BadRequest(msg=msg)

        kwargs = {
            'name': 'cluster_%s_%s' % (req.operation, cluster.id[:8]),
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'operation': req.operation,
                'params': params,
                'nodes': node_ids,
            }
        }
        action_id = action_mod.Action.create(
            ctx, cluster.id, consts.CLUSTER_OPERATION, **kwargs)
        dispatcher.start_action()
        LOG.info("Cluster operation action is queued: %s.", action_id)
        return {'action': action_id}

    @request_context
    def node_list(self, ctx, req):
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
            try:
                db_cluster = co.Cluster.find(ctx, req.cluster_id)
            except exception.ResourceNotFound:
                msg = _("Cannot find the given cluster: %s") % req.cluster_id
                raise exception.BadRequest(msg=msg)
            query['cluster_id'] = db_cluster.id

        filters = {}
        if req.obj_attr_is_set('name'):
            filters['name'] = req.name
        if req.obj_attr_is_set('status'):
            filters['status'] = req.status
        if filters:
            query['filters'] = filters

        nodes = node_obj.Node.get_all(ctx, **query)
        return [node.to_dict() for node in nodes]

    @request_context
    def node_create(self, ctx, req):
        """Create a node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeCreateRequestBody object.
        :return: A dictionary containing the details about the node and the
                 ID of the action triggered by this operation.
        """
        cluster_id = ""
        index = -1
        name_format = ""
        req.obj_set_defaults()

        try:
            node_profile = profile_obj.Profile.find(ctx, req.profile_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        if req.cluster_id:
            try:
                db_cluster = co.Cluster.find(ctx, req.cluster_id)
            except (exception.ResourceNotFound,
                    exception.MultipleChoices) as ex:
                msg = ex.enhance_msg('specified', ex)
                raise exception.BadRequest(msg=msg)

            # Validate profile type
            if node_profile.id != db_cluster.profile_id:
                cluster_profile = profile_obj.Profile.find(
                    ctx, db_cluster.profile_id)
                if node_profile.type != cluster_profile.type:
                    msg = _('Node and cluster have different profile type, '
                            'operation aborted.')
                    raise exception.BadRequest(msg=msg)

            cluster_id = db_cluster.id
            name_format = db_cluster.config.get("node.name.format", "")
            index = co.Cluster.get_next_index(ctx, cluster_id)

        # we use requested name only when cluster is not specified
        if cluster_id == "":
            node_name = req.name
        else:
            node_name = utils.format_node_name(name_format, db_cluster, index)

        if CONF.name_unique:
            if node_obj.Node.get_by_name(ctx, node_name):
                msg = _("The node named (%(name)s) already exists."
                        ) % {"name": node_name}
                raise exception.BadRequest(msg=msg)

        LOG.info("Creating node '%s'.", node_name)

        # Create a node instance
        values = {
            'name': node_name,
            'profile_id': node_profile.id,
            'cluster_id': cluster_id or '',
            'physical_id': None,
            'index': index,
            'role': req.role or '',
            'metadata': req.metadata or {},
            'status': consts.NS_INIT,
            'status_reason': 'Initializing',
            'data': {},
            'dependents': {},
            'init_at': timeutils.utcnow(True),
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
        }
        node = node_obj.Node.create(ctx, values)

        params = {
            'name': 'node_create_%s' % node.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, node.id,
                                             consts.NODE_CREATE, **params)
        dispatcher.start_action()
        LOG.info("Node create action queued: %s.", action_id)

        result = node.to_dict()
        result['action'] = action_id
        return result

    @request_context
    def node_get(self, ctx, req):
        """Retrieve the node specified.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeGetRequest object.
        :return: A dictionary containing the detailed information about a node
                 or an exception of `ResourceNotFound` if no matching node
                 could be found.
        """
        req.obj_set_defaults()
        node = node_obj.Node.find(ctx, req.identity)
        res = node.to_dict()
        if req.show_details and node.physical_id:
            obj = node_mod.Node.load(ctx, db_node=node)
            res['details'] = obj.get_details(ctx)
        return res

    @request_context
    def node_update(self, ctx, req):
        """Update a node with new propertye values.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeUpdateRequest object.
        :return: A dictionary containing the updated representation of the
                 node along with the ID of the action triggered by this
                 request.
        """
        LOG.info("Updating node '%s'.", req.identity)

        node = node_obj.Node.find(ctx, req.identity)
        inputs = {}
        if req.obj_attr_is_set('profile_id') and req.profile_id is not None:
            try:
                db_profile = profile_obj.Profile.find(ctx, req.profile_id)
            except exception.ResourceNotFound as ex:
                msg = ex.enhance_msg('specified', ex)
                raise exception.BadRequest(msg=msg)
            profile_id = db_profile.id

            # check if profile_type matches
            old_profile = profile_obj.Profile.find(ctx, node.profile_id)
            if old_profile.type != db_profile.type:
                msg = _('Cannot update a node to a different profile type, '
                        'operation aborted.')
                raise exception.BadRequest(msg=msg)

            if profile_id != old_profile.id:
                inputs['new_profile_id'] = profile_id

        if req.obj_attr_is_set('name') and req.name:
            if req.name != node.name:
                inputs['name'] = req.name
        if req.obj_attr_is_set('role') and req.role != node.role:
            inputs['role'] = req.role
        if req.obj_attr_is_set('metadata'):
            if req.metadata != node.metadata:
                inputs['metadata'] = req.metadata

        if not inputs:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'node_update_%s' % node.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(ctx, node.id, consts.NODE_UPDATE,
                                             **params)
        dispatcher.start_action()
        LOG.info("Node update action is queued: %s.", action_id)

        resp = node.to_dict()
        resp['action'] = action_id

        return resp

    @request_context
    def node_delete(self, ctx, req):
        """Delete the specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeDeleteRequest object.
        :return: A dictionary containing the ID of the action triggered by
                 this request.
        """
        LOG.info('Deleting node %s', req.identity)

        node = node_obj.Node.find(ctx, req.identity)

        force = False
        if req.obj_attr_is_set(consts.NODE_DELETE_FORCE):
            force = req.force

        if (not force and
            node.status in [consts.NS_CREATING,
                            consts.NS_UPDATING,
                            consts.NS_DELETING,
                            consts.NS_RECOVERING]):
            raise exception.ActionInProgress(type='node', id=req.identity,
                                             status=node.status)

        nodes = node.dependents.get('nodes', None)
        if nodes is not None and len(nodes) > 0:
            reason = _("still depended by other clusters and/or nodes")
            raise exception.ResourceInUse(type='node', id=req.identity,
                                          reason=reason)

        params = {
            'name': 'node_delete_%s' % node.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(ctx, node.id,
                                             consts.NODE_DELETE, **params)
        dispatcher.start_action()
        LOG.info("Node delete action is queued: %s.", action_id)

        return {'action': action_id}

    def _node_adopt_preview(self, ctx, req):
        """Preview version of node adoption (internal version).

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeAdoptPreviewRequest or the
                    NodeAdoptRequest object.
        :returns: A tuple containing the profile class and the spec for the
                 node that can be adopted.
        :raises: BadRequest(404) if profile type not found; or
                 InternalServerError(500) if profile operation failed.
        """

        # Apply default settings on the request
        req.obj_set_defaults()

        try:
            profile_cls = environment.global_env().get_profile(req.type)
        except exception.ResourceNotFound as ex:
            raise exception.BadRequest(msg=six.text_type(ex))

        # NOTE: passing in context to avoid loading runtime data
        temp_node = node_mod.Node('adopt', 'TBD', physical_id=req.identity,
                                  context=ctx)
        # TODO(Qiming): return node status and created timestamp
        # TODO(Qiming): pass 'preview' into 'adopt_node' so that we don't
        #               blindly create snapshots.
        spec = profile_base.Profile.adopt_node(ctx, temp_node, req.type,
                                               overrides=req.overrides,
                                               snapshot=req.snapshot)
        if 'Error' in spec:
            err = '%s: %s' % (spec['Error']['code'], spec['Error']['message'])
            raise exception.ProfileOperationFailed(message=err)

        parts = req.type.split('-')
        res = {
            'type': parts[0],
            'version': parts[1],
            'properties': spec
        }
        return profile_cls, res

    @request_context
    def node_adopt_preview(self, ctx, req):
        """Preview a node adoption operation.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeAdoptPreviewRequest object.
        :returns: A dict containing the properties of a spec.
        """
        LOG.info("Adopting node '%s' (preview).", req.identity)
        _, spec = self._node_adopt_preview(ctx, req)
        return {'node_preview': spec}

    @request_context
    def node_adopt(self, ctx, req):
        """Adopt a node into senlin's management.

        :param ctx: An instance of the request context.
        :param req: An NodeAdoptRequest object.
        :returns: A dict containing information about the node created by
                  adopting an existing physical resource.
        """
        LOG.info("Adopting node '%s'.", req.identity)

        # check name uniqueness if needed
        if req.obj_attr_is_set('name') and req.name:
            name = req.name
            if CONF.name_unique and node_obj.Node.get_by_name(ctx, name):
                msg = _("The node named (%s) already exists.") % name
                raise exception.BadRequest(msg=msg)
        else:
            name = 'node-' + utils.random_name()

        # create spec using preview
        profile_cls, spec = self._node_adopt_preview(ctx, req)
        # create profile
        profile = profile_cls.create(ctx, "prof-%s" % name, spec)
        if req.obj_attr_is_set('metadata'):
            metadata = req.metadata
        else:
            metadata = {}
        # Create a node instance
        values = {
            'name': name,
            'data': {},
            'dependents': {},
            'profile_id': profile.id,
            'cluster_id': '',
            'physical_id': req.identity,
            'index': -1,
            'role': '',
            'metadata': metadata,
            # TODO(Qiming): Set node status properly
            'status': consts.NS_ACTIVE,
            'status_reason': 'Node adopted successfully',
            'init_at': timeutils.utcnow(True),
            'created_at': timeutils.utcnow(True),
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
        }
        node = node_obj.Node.create(ctx, values)

        # TODO(Qiming): set cluster_node_id metadata
        LOG.info("Adopted node '%(rid)s' as '%(id)s'.",
                 {'rid': req.identity, 'id': node.id})
        return node.to_dict()

    @request_context
    def node_check(self, ctx, req):
        """Check the health status of specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeCheckRequest object.
        :return: A dictionary containing the ID of the action triggered by
                 this request.
        """
        LOG.info("Checking node '%s'.", req.identity)

        db_node = node_obj.Node.find(ctx, req.identity)

        kwargs = {
            'name': 'node_check_%s' % db_node.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY
        }
        if req.obj_attr_is_set('params') and req.params:
            kwargs['inputs'] = req.params
        action_id = action_mod.Action.create(ctx, db_node.id,
                                             consts.NODE_CHECK, **kwargs)
        dispatcher.start_action()
        LOG.info("Node check action is queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def node_recover(self, ctx, req):
        """Recover the specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeRecoverRequest object.
        :return: A dictionary containing the ID of the action triggered by the
                 recover request.
        """
        LOG.info("Recovering node '%s'.", req.identity)

        db_node = node_obj.Node.find(ctx, req.identity)

        kwargs = {
            'name': 'node_recover_%s' % db_node.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {}
        }
        if req.obj_attr_is_set('params') and req.params:
            if 'check' in req.params:
                kwargs['inputs']['check'] = req.params.pop('check')

            if 'operation' in req.params:
                op_name = req.params.pop('operation')
                kwargs['inputs']['operation'] = [{'name': op_name}]

            if len(req.params):
                keys = [str(k) for k in req.params]
                msg = _("Action parameter %s is not recognizable."
                        ) % keys
                raise exception.BadRequest(msg=msg)

        action_id = action_mod.Action.create(ctx, db_node.id,
                                             consts.NODE_RECOVER, **kwargs)
        dispatcher.start_action()
        LOG.info("Node recover action is queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def node_op(self, ctx, req):
        """Perform an operation on the specified node.

        :param ctx: An instance of the request context.
        :param req: An instance of the NodeOperationRequest object.
        :return: A dictionary containing the ID of the action triggered by the
                 operation request.
        """
        LOG.info("Performing operation '%(o)s' on node '%(n)s'.",
                 {'o': req.operation, 'n': req.identity})

        db_node = node_obj.Node.find(ctx, req.identity)
        node = node_mod.Node.load(ctx, db_node=db_node)
        profile = node.rt['profile']
        if req.operation not in profile.OPERATIONS:
            msg = _("The requested operation '%(o)s' is not supported by the "
                    "profile type '%(t)s'."
                    ) % {'o': req.operation, 't': profile.type}
            raise exception.BadRequest(msg=msg)

        params = {}
        if req.obj_attr_is_set('params') and req.params:
            params = req.params
            try:
                profile.OPERATIONS[req.operation].validate(req.params)
            except exception.ESchema as ex:
                raise exception.BadRequest(msg=six.text_type(ex))

        kwargs = {
            'name': 'node_%s_%s' % (req.operation, db_node.id[:8]),
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'operation': req.operation,
                'params': params
            }
        }
        action_id = action_mod.Action.create(ctx, db_node.id,
                                             consts.NODE_OPERATION, **kwargs)
        dispatcher.start_action()
        LOG.info("Node operation action is queued: %s.", action_id)
        return {'action': action_id}

    @request_context
    def cluster_policy_list(self, ctx, req):
        """List cluster-policy bindings given the cluster identity.

        :param ctx: An instance of the request context.
        :param req: An instance of the ClusterPolicyListRequest object.
        :return: A list containing dictionaries each representing a binding.
        """
        sort = None
        if req.obj_attr_is_set('sort'):
            sort = req.sort
        filters = {}
        if req.obj_attr_is_set('policy_name'):
            filters['policy_name'] = req.policy_name
        if req.obj_attr_is_set('policy_type'):
            filters['policy_type'] = req.policy_type
        if req.obj_attr_is_set('enabled'):
            filters['enabled'] = req.enabled

        db_cluster = co.Cluster.find(ctx, req.identity)
        bindings = cp_obj.ClusterPolicy.get_all(
            ctx, db_cluster.id, filters=filters, sort=sort)

        return [binding.to_dict() for binding in bindings]

    @request_context
    def cluster_policy_get(self, ctx, req):
        """Get the binding record giving the cluster and policy identity.

        :param ctx: An instance of request context.
        :param req: An instance of the ClusterPolicyGetRequest object.
        :return: A dictionary containing the binding record, or raises an
                 exception of ``PolicyBindingNotFound``.
        """
        identity = req.identity
        policy_id = req.policy_id
        db_cluster = co.Cluster.find(ctx, identity)
        db_policy = policy_obj.Policy.find(ctx, policy_id)

        binding = cp_obj.ClusterPolicy.get(ctx, db_cluster.id, db_policy.id)
        if binding is None:
            raise exception.PolicyBindingNotFound(policy=policy_id,
                                                  identity=identity)

        return binding.to_dict()

    @request_context
    def cluster_policy_attach(self, ctx, req):
        """Attach a policy to the specified cluster.

        This is done via an action because a cluster lock is needed.

        :param ctx: An instance of request context.
        :param req: An instance of the ClusterAttachPolicyRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        LOG.info("Attaching policy (%(policy)s) to cluster "
                 "(%(cluster)s).",
                 {'policy': req.policy_id, 'cluster': req.identity})

        db_cluster = co.Cluster.find(ctx, req.identity)
        try:
            db_policy = policy_obj.Policy.find(ctx, req.policy_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        req.obj_set_defaults()

        params = {
            'name': 'attach_policy_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'policy_id': db_policy.id,
                'enabled': req.enabled,
            }
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_ATTACH_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info("Policy attach action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_policy_detach(self, ctx, req):
        """Detach a policy from the specified cluster.

        This is done via an action because cluster lock is needed.

        :param ctx: An instance of request context.
        :param req: An instance of the ClusterDetachPolicyRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        LOG.info("Detaching policy '%(policy)s' from cluster "
                 "'%(cluster)s'.",
                 {'policy': req.policy_id, 'cluster': req.identity})

        db_cluster = co.Cluster.find(ctx, req.identity)
        try:
            db_policy = policy_obj.Policy.find(ctx, req.policy_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        binding = cp_obj.ClusterPolicy.get(ctx, db_cluster.id, db_policy.id)
        if binding is None:
            msg = _("The policy '%(p)s' is not attached to the specified "
                    "cluster '%(c)s'."
                    ) % {'p': req.policy_id, 'c': req.identity}
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'detach_policy_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {'policy_id': db_policy.id},
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_DETACH_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info("Policy detach action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def cluster_policy_update(self, ctx, req):
        """Update an existing policy binding on a cluster.

        This is done via an action because cluster lock is needed.

        :param context: An instance of request context.
        :param req: An instance of the ClusterUpdatePolicyRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        LOG.info("Updating policy '%(policy)s' on cluster '%(cluster)s.'",
                 {'policy': req.policy_id, 'cluster': req.identity})

        db_cluster = co.Cluster.find(ctx, req.identity)
        try:
            db_policy = policy_obj.Policy.find(ctx, req.policy_id)
        except exception.ResourceNotFound as ex:
            msg = ex.enhance_msg('specified', ex)
            raise exception.BadRequest(msg=msg)

        binding = cp_obj.ClusterPolicy.get(ctx, db_cluster.id, db_policy.id)
        if binding is None:
            msg = _("The policy '%(p)s' is not attached to the specified "
                    "cluster '%(c)s'."
                    ) % {'p': req.policy_id, 'c': req.identity}
            raise exception.BadRequest(msg=msg)

        inputs = {'policy_id': db_policy.id}
        if req.obj_attr_is_set('enabled'):
            inputs['enabled'] = req.enabled

        params = {
            'name': 'update_policy_%s' % db_cluster.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs
        }
        action_id = action_mod.Action.create(ctx, db_cluster.id,
                                             consts.CLUSTER_UPDATE_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info("Policy update action queued: %s.", action_id)

        return {'action': action_id}

    @request_context
    def action_list(self, ctx, req):
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

        actions = action_obj.Action.get_all(ctx, **query)
        return [a.to_dict() for a in actions]

    @request_context
    def action_create(self, ctx, req):
        """Create an action with given details.

        :param ctx: An instance of the request context.
        :param req: An instance of the ActionCreateRequestBody object.
        :return: A dictionary containing the details about the action and the
                 ID of the action triggered by this operation.
        """
        LOG.info("Creating action '%s'.", req.name)

        req.obj_set_defaults()
        try:
            target = co.Cluster.find(ctx, req.cluster_id)
        except exception.ResourceNotFound:
            msg = _("Cannot find the given cluster: %s") % req.cluster_id
            raise exception.BadRequest(msg=msg)

        # Create an action instance
        params = {
            'name': req.name,
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': req.inputs or {},
        }
        action_id = action_mod.Action.create(ctx, target.id, req.action,
                                             **params)

        # TODO(Anyone): Uncomment this to notify the dispatcher
        # dispatcher.start_action(action_id=action.id)

        LOG.info("Action '%(name)s' is created: %(id)s.",
                 {'name': req.name, 'id': action_id})
        return {'action': action_id}

    @request_context
    def action_get(self, ctx, req):
        """Retrieve the action specified.

        :param ctx: An instance of the request context.
        :param req: An instance of the ActionGetRequest object.
        :return: A dictionary containing the detailed information about a
                 action or an exception of `ResourceNotFound` if no matching
                 action could be found.
        """
        action = action_obj.Action.find(ctx, req.identity)
        return action.to_dict()

    @request_context
    def action_delete(self, ctx, req):
        """Delete the specified action object.

        :param ctx: An instance of the request context.
        :param req: An instance of the ActionDeleteRequest object.
        :return: None if deletion was successful, or an exception of type
                 `ResourceInUse`.
        """
        db_action = action_obj.Action.find(ctx, req.identity)
        LOG.info("Deleting action '%s'.", req.identity)
        try:
            action_mod.Action.delete(ctx, db_action.id)
        except exception.EResourceBusy:
            reason = _("still in one of WAITING, RUNNING or SUSPENDED state")
            raise exception.ResourceInUse(type='action', id=req.identity,
                                          reason=reason)

        LOG.info("Action '%s' is deleted.", req.identity)

    @request_context
    def receiver_list(self, ctx, req):
        """List receivers matching the specified criteria.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverListRequest object.
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
        if req.obj_attr_is_set('user'):
            filters['user'] = req.user
        if filters:
            query['filters'] = filters

        receivers = receiver_obj.Receiver.get_all(ctx, **query)
        return [r.to_dict() for r in receivers]

    @request_context
    def receiver_create(self, ctx, req):
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

        LOG.info("Creating %(t)s receiver %(n)s.",
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
            invalid_actions = [consts.CLUSTER_CREATE]
            if action in invalid_actions:
                msg = _("Action name cannot be any of %s.") % invalid_actions
                raise exception.BadRequest(msg=msg)

            # Check whether cluster identified by cluster_id does exist
            try:
                cluster = co.Cluster.find(ctx, req.cluster_id)
            except (exception.ResourceNotFound,
                    exception.MultipleChoices) as ex:
                msg = ex.enhance_msg('referenced', ex)
                raise exception.BadRequest(msg=msg)

            # permission checking
            if not ctx.is_admin and ctx.user_id != cluster.user:
                raise exception.Forbidden()

        kwargs = {
            'name': req.name,
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
            'params': req.params
        }

        receiver = receiver_mod.Receiver.create(ctx, req.type, cluster,
                                                action, **kwargs)
        LOG.info("Receiver (%(n)s) is created: %(i)s.",
                 {'n': req.name, 'i': receiver.id})

        return receiver.to_dict()

    @request_context
    def receiver_get(self, ctx, req):
        """Get the details about a receiver.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverGetRequest object.
        :return: A dictionary containing the details about a receiver or
                 an exception `ResourceNotFound` if no matching object found.
        """
        # NOTE: Temporary code to make tempest tests about webhook_trigger
        #       pass, will remove in latter patches.
        kwargs = {}
        if ctx.is_admin is True:
            kwargs['project_safe'] = False

        receiver = receiver_obj.Receiver.find(ctx, req.identity, **kwargs)
        return receiver.to_dict()

    @request_context
    def receiver_update(self, ctx, req):
        """Update the properties of a given receiver

        :param ctx: An instance of request context.
        :param req: An instance of the ReceiverUpdateRequest.
        :returns: A dictionary containing the receiver details of the updated
                  receiver, or an exception `ResourceNotFound` if no matching
                  receiver is found.
        """
        LOG.info("Updating receiver '%(id)s'.", {'id': req.identity})
        db_receiver = receiver_obj.Receiver.find(ctx, req.identity)
        receiver = receiver_mod.Receiver.load(ctx, receiver_obj=db_receiver)
        changed = False
        if (req.obj_attr_is_set('name') and req.name is not None):
            if req.name != receiver.name:
                receiver.name = req.name
                changed = True
        if (req.obj_attr_is_set('action') and req.action is not None):
            if req.action != receiver.action:
                receiver.action = req.action
                changed = True
        if (req.obj_attr_is_set('params') and req.params is not None):
            if req.params != receiver.params:
                receiver.params = req.params
                changed = True
        if changed:
            receiver.store(ctx, update=True)
        else:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)
        LOG.info("Receiver '%(id)s' is updated.", {'id': req.identity})
        return receiver.to_dict()

    @request_context
    def receiver_delete(self, ctx, req):
        """Delete the specified receiver.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverDeleteRequest object.
        :return: None if successfully deleted the receiver or an exception of
                 `ResourceNotFound` if the object could not be found.
        """
        db_receiver = receiver_obj.Receiver.find(ctx, req.identity)
        LOG.info("Deleting receiver %s.", req.identity)
        receiver_mod.Receiver.delete(ctx, db_receiver.id)
        LOG.info("Receiver %s is deleted.", req.identity)

    @request_context
    def receiver_notify(self, ctx, req):
        """Handle notification to specified receiver.

        :param ctx: An instance of the request context.
        :param req: An instance of the ReceiverNotifyRequest object.
        """
        db_receiver = receiver_obj.Receiver.find(ctx, req.identity)
        # permission checking
        if not ctx.is_admin and ctx.user_id != db_receiver.user:
            raise exception.Forbidden()

        # Receiver type check
        if db_receiver.type != consts.RECEIVER_MESSAGE:
            msg = _("Notifying non-message receiver is not allowed.")
            raise exception.BadRequest(msg=msg)

        LOG.info("Received notification to receiver %s.", req.identity)
        receiver = receiver_mod.Receiver.load(ctx,
                                              receiver_obj=db_receiver,
                                              project_safe=True)
        receiver.notify(ctx)

    @request_context
    def webhook_trigger(self, ctx, req):
        """trigger the webhook.

        :param ctx: An instance of the request context.
        :param req: An instance of the WebhookTriggerRequest object.
        :return: A dictionary contains the ID of the action fired.
        """
        identity = req.identity
        params = req.body.params

        LOG.info("Triggering webhook (%s)", identity)
        receiver = receiver_obj.Receiver.find(ctx, identity)

        try:
            cluster = co.Cluster.find(ctx, receiver.cluster_id)
        except (exception.ResourceNotFound, exception.MultipleChoices) as ex:
            msg = ex.enhance_msg('referenced', ex)
            raise exception.BadRequest(msg=msg)

        data = copy.deepcopy(receiver.params)
        if params:
            data.update(params)

        kwargs = {
            'name': 'webhook_%s' % receiver.id[:8],
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': data
        }

        action_id = action_mod.Action.create(ctx, cluster.id,
                                             receiver.action, **kwargs)
        dispatcher.start_action()
        LOG.info("Webhook %(w)s triggered with action queued: %(a)s.",
                 {'w': identity, 'a': action_id})

        return {'action': action_id}

    @request_context
    def event_list(self, ctx, req):
        """List event records matching the specified criteria.

        :param ctx: An instance of the request context.
        :param req: An instance of the EventListRequest object.
        :return: A list of `Event` object representations.
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
        if req.obj_attr_is_set('oid'):
            filters['oid'] = req.oid
        if req.obj_attr_is_set('oname'):
            filters['oname'] = req.oname
        if req.obj_attr_is_set('otype'):
            filters['otype'] = req.otype
        if req.obj_attr_is_set('action'):
            filters['action'] = req.action
        if req.obj_attr_is_set('level'):
            filters['level'] = req.level
        if req.obj_attr_is_set('cluster_id'):
            cluster_ids = []
            for cid in req.cluster_id:
                try:
                    cluster = co.Cluster.find(ctx, cid)
                    cluster_ids.append(cluster.id)
                except exception.ResourceNotFound:
                    return []
            if len(cluster_ids) > 0:
                filters['cluster_id'] = cluster_ids
        if filters:
            query['filters'] = filters

        if filters and consts.EVENT_LEVEL in filters:
            value = filters.pop(consts.EVENT_LEVEL)
            value = utils.parse_level_values(value)
            if value is not None:
                filters[consts.EVENT_LEVEL] = value

        all_events = event_obj.Event.get_all(ctx, **query)

        results = []
        for event in all_events:
            evt = event.as_dict()
            level = utils.level_from_number(evt['level'])
            evt['level'] = level
            results.append(evt)

        return results

    @request_context
    def event_get(self, ctx, req):
        """Retrieve the event specified.

        :param ctx: An instance of the request context.
        :param req: An instance of the EventGetRequest object.
        :return: A dictionary containing the detailed information about a
                 event or an exception of `ResourceNotFound` if no matching
                 event could be found.
        """

        db_event = event_obj.Event.find(ctx, req.identity)
        evt = db_event.as_dict()
        level = utils.level_from_number(evt['level'])
        evt['level'] = level

        return evt
