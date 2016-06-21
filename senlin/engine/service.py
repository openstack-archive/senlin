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
import six

from senlin.common import consts
from senlin.common import context as senlin_context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
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
from senlin.engine import receiver as receiver_mod
from senlin.engine import scheduler
from senlin.objects import action as action_obj
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


class EngineService(service.Service):
    '''Lifecycle manager for a running service engine.

    - All the contained methods here are called from the RPC client.
    - If a RPC call does not have a corresponding method here, an exception
      will be thrown.
    - Arguments to these calls are added dynamically and will be treated as
      keyword arguments by the RPC client.
    '''

    def __init__(self, host, topic, manager=None):

        super(EngineService, self).__init__()
        self.host = host
        self.topic = topic
        self.dispatcher_topic = consts.ENGINE_DISPATCHER_TOPIC
        self.health_mgr_topic = consts.ENGINE_HEALTH_MGR_TOPIC

        # The following are initialized here and will be assigned in start()
        # which happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.TG = None
        self.target = None
        self._rpc_server = None

        # Intialize the global environment
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

        # create a health manager RPC service for this engine.
        self.health_mgr = health_manager.HealthManager(
            self, self.health_mgr_topic, consts.RPC_API_VERSION)

        LOG.info(_LI("Starting health manager for engine %s"), self.engine_id)
        self.health_mgr.start()

        target = oslo_messaging.Target(version=consts.RPC_API_VERSION,
                                       server=self.host,
                                       topic=self.topic)
        self.target = target
        self._rpc_server = rpc_messaging.get_rpc_server(target, self)
        self._rpc_server.start()
        self.service_manage_cleanup()
        self.TG.add_timer(cfg.CONF.periodic_interval,
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

    def service_manage_cleanup(self):
        ctx = senlin_context.get_admin_context()
        time_window = (2 * cfg.CONF.periodic_interval)
        svcs = service_obj.Service.get_all(ctx)
        for svc in svcs:
            if svc['id'] == self.engine_id:
                continue
            if timeutils.is_older_than(svc['updated_at'], time_window):
                # < time_line:
                # hasn't been updated, assuming it's died.
                LOG.info(_LI('Service %s was aborted'), svc['id'])
                service_obj.Service.delete(ctx, svc['id'])

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
        return cfg.CONF.revision['senlin_engine_revision']

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
        :return: A DB object of profile or an exception `ProfileNotFound` if
                 no matching object is found.
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
            raise exception.ProfileNotFound(profile=identity)

        return profile

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
        if cfg.CONF.name_unique:
            if profile_obj.Profile.get_by_name(context, name):
                msg = _("A profile named '%(name)s' already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        try:
            plugin = environment.global_env().get_profile(type_str)
        except exception.ProfileTypeNotFound:
            msg = _("The specified profile type (%(name)s) is not found."
                    ) % {"name": type_str}
            raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Creating profile %(type)s '%(name)s'."),
                 {'type': type_str, 'name': name})

        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'metadata': metadata,
        }
        profile = plugin(name, spec, **kwargs)
        try:
            profile.validate()
        except exception.InvalidSpec as ex:
            msg = six.text_type(ex)
            LOG.error(_LE("Failed in creating profile: %s"), msg)
            raise exception.BadRequest(msg=msg)

        profile.store(context)

        LOG.info(_LI("Profile %(name)s is created: %(id)s."),
                 {'name': name, 'id': profile.id})

        return profile.to_dict()

    @request_context
    def profile_get(self, context, identity):
        """Retrieve the details about a profile.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :return: A dictionary containing the policy details, or an exception
                 of type `ProfileNotFound` if no matching object is found.
        """
        db_profile = self.profile_find(context, identity)
        profile = profile_base.Profile.load(context, profile=db_profile)
        return profile.to_dict()

    @request_context
    def profile_update(self, context, profile_id, name=None, metadata=None):
        """Update the properties of a given profile.

        :param context: An instance of the request context.
        :param profile_id: The UUID, name or short-id of a profile.
        :param name: The new name for the profile.
        :param metadata: A dictionary of key-value pairs to be associated with
                         the profile.
        :returns: A dictionary containing the details of the updated profile,
                  or an exception `ProfileNotFound` if no matching profile is
                  found.
        """
        LOG.info(_LI("Updating profile '%(id)s.'"), {'id': profile_id})

        db_profile = self.profile_find(context, profile_id)
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

        LOG.info(_LI("Profile '%(id)s' is updated."), {'id': profile_id})
        return profile.to_dict()

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
        except exception.ResourceBusyError:
            LOG.error(_LI("The profile '%s' cannot be deleted."), identity)
            raise exception.ResourceInUse(resource_type='profile',
                                          resource_id=db_profile.id)

        LOG.info(_LI("Profile '%(id)s' is deleted."), {'id': identity})

    @request_context
    def policy_type_list(self, context):
        """List known policy type implementations.

        :param context: An instance of the request context.
        :return: A list of policy types.
        """
        return environment.global_env().get_policy_types()

    @request_context
    def policy_type_get(self, context, type_name):
        """Get the details about a policy type.

        :param context: An instance of the request context.
        :param type_name: The name of a policy type.
        :return: The details about a policy type.
        """
        policy_type = environment.global_env().get_policy(type_name)
        data = policy_type.get_schema()

        return {
            'name': type_name,
            'schema': data
        }

    def policy_find(self, context, identity, project_safe=True):
        """Find a policy with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :param project_safe: A boolean indicating whether policies from
                             projects other than the requesting one should be
                             evaluated.
        :return: A DB object of policy or an exception of `PolicyNotFound` if
                 no matching object is found.
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
            raise exception.PolicyNotFound(policy=identity)

        return policy

    @request_context
    def policy_list(self, context, limit=None, marker=None, sort=None,
                    filters=None, project_safe=True):
        """List policies matching the specified criteria.

        :param context: An instance of request context.
        :param limit: An integer specifying the maximum number of policies to
                      return in a response.
        :param marker: An UUID specifying the policy after which the result
                       list starts.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param project_safe: A boolean indicating whether policies from all
                             projects will be returned.
        :return: A list of `Policy` object representations.
        """
        limit = utils.parse_int_param('limit', limit)
        utils.validate_sort_param(sort, consts.POLICY_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()
        policies = policy_base.Policy.load_all(context,
                                               limit=limit, marker=marker,
                                               sort=sort, filters=filters,
                                               project_safe=project_safe)
        return [p.to_dict() for p in policies]

    @request_context
    def policy_create(self, context, name, spec):
        """Create a policy with the given name and spec.

        :param context: An instance of the request context.
        :param name: The name for the policy to be created.
        :param spec: A dictionary containing the spec for the policy.
        :return: A dictionary containing the details of the policy object
                 created.
        """
        if cfg.CONF.name_unique:
            if policy_obj.Policy.get_by_name(context, name):
                msg = _("A policy named '%(name)s' already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        try:
            plugin = environment.global_env().get_policy(type_str)
        except exception.PolicyTypeNotFound:
            msg = _("The specified policy type (%(name)s) is not found."
                    ) % {"name": type_str}
            raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Creating policy %(type)s '%(name)s'"),
                 {'type': type_str, 'name': name})

        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
        }
        policy = plugin(name, spec, **kwargs)

        try:
            policy.validate()
        except exception.InvalidSpec as ex:
            msg = six.text_type(ex)
            LOG.error(_LE("Failed in creating policy: %s"), msg)
            raise exception.BadRequest(msg=msg)

        policy.store(context)
        LOG.info(_LI("Policy '%(name)s' is created: %(id)s."),
                 {'name': name, 'id': policy.id})
        return policy.to_dict()

    @request_context
    def policy_get(self, context, identity):
        """Retrieve the details about a policy.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a policy.
        :return: A dictionary containing the policy details, or an exception
                 of type `PolicyNotFound` if no matching object is found.
        """
        db_policy = self.policy_find(context, identity)
        policy = policy_base.Policy.load(context, db_policy=db_policy)
        return policy.to_dict()

    @request_context
    def policy_update(self, context, identity, name):
        """Update the properties of a given policy.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a policy.
        :param name: The new name for the policy.
        :returns: A dictionary containing the details of the updated policy or
                  an exception `PolicyNotFound` if no matching poicy is found,
                  or an exception `BadRequest` if name is not provided.
        """
        if not name:
            msg = _('Policy name not specified.')
            raise exception.BadRequest(msg=msg)

        db_policy = self.policy_find(context, identity)
        policy = policy_base.Policy.load(context, db_policy=db_policy)

        if name != policy.name:
            LOG.info(_LI("Updating policy '%s'."), identity)
            policy.name = name
            policy.store(context)
            LOG.info(_LI("Policy '%s' is updated."), identity)

        return policy.to_dict()

    @request_context
    def policy_delete(self, context, identity):
        """Delete the specified policy.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a policy.
        :return: None if succeeded or an exception of `ResourceInUse` if
                 policy is still attached to certain clusters.
        """
        db_policy = self.policy_find(context, identity)
        LOG.info(_LI("Delete policy '%s'."), identity)
        try:
            policy_base.Policy.delete(context, db_policy.id)
        except exception.ResourceBusyError:
            LOG.error(_LI("Policy '%s' cannot be deleted."), identity)
            raise exception.ResourceInUse(resource_type='policy',
                                          resource_id=db_policy.id)

        LOG.info(_LI("Policy '%s' is deleted."), identity)

    def cluster_find(self, context, identity, project_safe=True):
        """Find a cluster with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short ID of a cluster.
        :param project_safe: A boolean parameter specifying whether only
                             clusters from the same project are qualified to
                             be returned.
        :return: An instance of `Cluster` class.
        :raises: `ClusterNotFound` if no matching object can be found.
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
            raise exception.ClusterNotFound(cluster=identity)

        return cluster

    @request_context
    def cluster_list(self, context, limit=None, marker=None, sort=None,
                     filters=None, project_safe=True):
        """List clusters matching the specified criteria.

        :param context: An instance of request context.
        :param limit: An integer specifying the maximum number of objects to
                      return in a response.
        :param marker: An UUID specifying the cluster after which the result
                       list starts.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param project_safe: A boolean indicating whether clusters from all
                             projects will be returned.
        :return: A list of `Cluster` object representations.
        """
        limit = utils.parse_int_param('limit', limit)
        utils.validate_sort_param(sort, consts.CLUSTER_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()
        clusters = cluster_mod.Cluster.load_all(context, limit=limit,
                                                marker=marker, sort=sort,
                                                filters=filters,
                                                project_safe=project_safe)

        return [cluster.to_dict() for cluster in clusters]

    @request_context
    def cluster_get(self, context, identity):
        """Retrieve the cluster specified.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-ID of a cluster.
        :return: A dictionary containing the details about a cluster.
        """
        db_cluster = self.cluster_find(context, identity)
        cluster = cluster_mod.Cluster.load(context, dbcluster=db_cluster)
        return cluster.to_dict()

    def check_cluster_quota(self, context):
        """Validate the number of clusters created in a project.

        :param context: An instance of the request context.
        :return: None if cluster creation is okay, or an exception of type
                 `Forbbiden` if number of clusters reaches the maximum.
        """
        existing = cluster_obj.Cluster.count_all(context)
        maximum = cfg.CONF.max_clusters_per_project
        if existing >= maximum:
            raise exception.Forbidden()

    @request_context
    def cluster_create(self, context, name, desired_capacity, profile_id,
                       min_size=None, max_size=None, metadata=None,
                       timeout=None):
        """Create a cluster.

        :param context: An instance of the request context.
        :param name: A string specifying the name of the cluster to be created.
        :param desired_capacity: The desired capacity of the cluster.
        :param profile_ID: The UUID, name or short-ID of the profile to use.
        :param min_size: An integer specifying the minimum size of the cluster.
        :param max_size: An integer specifying the maximum size of the cluster.
        :param metadata: A dictionary containing key-value pairs to be
                         associated with the cluster.
        :param timeout: An optional integer specifying the operation timeout
                        value in seconds.
        :return: A dictionary containing the details about the cluster and the
                 ID of the action triggered by this operation.
        """
        self.check_cluster_quota(context)

        if cfg.CONF.name_unique:
            if cluster_obj.Cluster.get_by_name(context, name):
                msg = _("The cluster (%(name)s) already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        try:
            db_profile = self.profile_find(context, profile_id)
        except exception.ProfileNotFound:
            msg = _("The specified profile '%s' is not found.") % profile_id
            raise exception.BadRequest(msg=msg)

        init_size = utils.parse_int_param(consts.CLUSTER_DESIRED_CAPACITY,
                                          desired_capacity)
        if min_size is not None:
            min_size = utils.parse_int_param(consts.CLUSTER_MIN_SIZE, min_size)
        if max_size is not None:
            max_size = utils.parse_int_param(consts.CLUSTER_MAX_SIZE, max_size,
                                             allow_negative=True)
        if timeout is not None:
            timeout = utils.parse_int_param(consts.CLUSTER_TIMEOUT, timeout)
        else:
            timeout = cfg.CONF.default_action_timeout

        res = su.check_size_params(None, init_size, min_size, max_size, True)
        if res:
            raise exception.BadRequest(msg=res)

        LOG.info(_LI("Creating cluster '%s'."), name)

        kwargs = {
            'min_size': min_size,
            'max_size': max_size,
            'timeout': timeout,
            'metadata': metadata,
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
        }

        cluster = cluster_mod.Cluster(name, init_size, db_profile.id, **kwargs)
        cluster.store(context)

        # Build an Action for cluster creation
        kwargs = {
            'name': 'cluster_create_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(context, cluster.id,
                                             consts.CLUSTER_CREATE, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Cluster create action queued: %s."), action_id)

        result = cluster.to_dict()
        result['action'] = action_id
        return result

    @request_context
    def cluster_update(self, context, identity, name=None, profile_id=None,
                       metadata=None, timeout=None):
        """Update a cluster.

        :param context: An instance of the request context.
        :param identity: The UUID, name, or short-ID or the target cluster.
        :param name: A string specifying the new name of the cluster.
        :param profile_id: The UUID, name or short-ID of the new profile.
        :param metadata: A dictionary containing key-value pairs to be
                         associated with the cluster.
        :param timeout: An optional integer specifying the new operation
                        timeout value in seconds.
        :return: A dictionary containing the details about the cluster and the
                 ID of the action triggered by this operation.
        """

        # Get the database representation of the existing cluster
        db_cluster = self.cluster_find(context, identity)
        cluster = cluster_mod.Cluster.load(context, dbcluster=db_cluster)
        if cluster.status == cluster.ERROR:
            msg = _('Updating a cluster in error state')
            LOG.error(msg)
            raise exception.FeatureNotSupported(feature=msg)

        LOG.info(_LI("Updating cluster '%s'."), identity)

        inputs = {}
        if profile_id is not None:
            old_profile = self.profile_find(context, cluster.profile_id)
            try:
                new_profile = self.profile_find(context, profile_id)
            except exception.ProfileNotFound:
                msg = _("The specified profile '%s' is not found."
                        ) % profile_id
                raise exception.BadRequest(msg=msg)

            if new_profile.type != old_profile.type:
                msg = _('Cannot update a cluster to a different profile type, '
                        'operation aborted.')
                raise exception.ProfileTypeNotMatch(message=msg)
            if old_profile.id != new_profile.id:
                inputs['new_profile_id'] = new_profile.id

        if metadata is not None and metadata != cluster.metadata:
            inputs['metadata'] = metadata

        if timeout is not None:
            timeout = utils.parse_int_param(consts.CLUSTER_TIMEOUT, timeout)
            inputs['timeout'] = timeout

        if name is not None:
            inputs['name'] = name

        if not inputs:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        kwargs = {
            'name': 'cluster_update_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(context, cluster.id,
                                             consts.CLUSTER_UPDATE, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Cluster update action queued: %s."), action_id)

        resp = cluster.to_dict()
        resp['action'] = action_id
        return resp

    @request_context
    def cluster_delete(self, context, identity):
        """Delete the specified cluster.

        :param identity: The UUID, name or short-ID of the target cluster.
        :return: A dictionary containing the ID of the action triggered.
        """

        LOG.info(_LI('Deleting cluster %s'), identity)

        db_cluster = self.cluster_find(context, identity)

        policies = cp_obj.ClusterPolicy.get_all(context, db_cluster.id)
        if len(policies) > 0:
            msg = _('Cluster %(id)s cannot be deleted without having all '
                    'policies detached.') % {'id': identity}
            LOG.error(msg)
            reason = _("there is still policy(s) attached to it.")
            raise exception.ClusterBusy(cluster=db_cluster.id, reason=reason)

        receivers = receiver_obj.Receiver.get_all(
            context, filters={'cluster_id': db_cluster.id})
        if len(receivers) > 0:
            msg = _('Cluster %(id)s cannot be deleted without having all '
                    'receivers deleted.') % {'id': identity}
            LOG.error(msg)
            reason = _("there is still receiver(s) associated with it.")
            raise exception.ClusterBusy(cluster=db_cluster.id, reason=reason)

        params = {
            'name': 'cluster_delete_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_DELETE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster delete action queued: %s"), action_id)

        return {'action': action_id}

    @request_context
    def cluster_add_nodes(self, context, identity, nodes):
        """Add specified nodes to the specified cluster.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the target cluster.
        :param nodes: A list of node identities where each item is the UUID,
                      name or short-id of a node.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Adding nodes '%(nodes)s' to cluster '%(cluster)s'."),
                 {'cluster': identity, 'nodes': nodes})

        db_cluster = self.cluster_find(context, identity)
        db_cluster_profile = self.profile_find(context,
                                               db_cluster.profile_id)
        cluster_profile_type = db_cluster_profile.type

        found = []
        not_found = []
        bad_nodes = []
        owned_nodes = []
        not_match_nodes = []
        for node in nodes:
            try:
                db_node = self.node_find(context, node)
                # Skip node in the same cluster already
                if db_node.status != node_mod.Node.ACTIVE:
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
            except exception.NodeNotFound:
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
            error = _("No nodes to add: %s.") % nodes

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

    @request_context
    def cluster_del_nodes(self, context, identity, nodes):
        """Delete specified nodes from the named cluster.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the cluster.
        :param nodes: A list containing the identities of the nodes to delete.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Deleting nodes '%(nodes)s' from cluster '%(cluster)s'."),
                 {'cluster': identity, 'nodes': nodes})
        db_cluster = self.cluster_find(context, identity)
        found = []
        not_found = []
        bad_nodes = []
        for node in nodes:
            try:
                db_node = self.node_find(context, node)
                if db_node.cluster_id != db_cluster.id:
                    bad_nodes.append(db_node.id)
                else:
                    found.append(db_node.id)
            except exception.NodeNotFound:
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
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_DEL_NODES,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster delete nodes action queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_resize(self, context, identity, adj_type=None, number=None,
                       min_size=None, max_size=None, min_step=None,
                       strict=True):
        """Adjust cluster size parameters.

        :param identity: cluster identity which can be cluster name, UUID or
                         short ID.
        :param adj_type: type of adjustment. If specified, must be one of the
                         strings defined in `consts.ADJUSTMENT_TYPES`.
        :param number: number for adjustment. It is interpreted as the new
                       desired_capacity of the cluster if `adj_type` is set
                       to `EXACT_CAPACITY`; it is interpreted as the relative
                       number of nodes to add/remove when `adj_type` is set
                       to `CHANGE_IN_CAPACITY`; it is treated as a percentage
                       when `adj_type` is set to `CHANGE_IN_PERCENTAGE`.
        :param min_size: new lower bound of the cluster size, if specified.
        :param max_size: new upper bound of the cluster size, if specified.
                         A value of negative means no upper limit is imposed.
        :param min_step: the number of nodes to be added or removed when
                         `adj_type` is set to value `CHANGE_IN_PERCENTAGE`
                         and the number calculated is less than 1.
        :param strict: whether Senlin should try a best-effort style resizing
                       or just rejects the request when scaling beyond its
                       current size constraint.

        :return: A dict containing the ID of an action fired.
        """

        # check adj_type
        if adj_type is not None:
            if adj_type not in consts.ADJUSTMENT_TYPES:
                raise exception.InvalidParameter(
                    name=consts.ADJUSTMENT_TYPE, value=adj_type)
            if number is None:
                msg = _('Missing number value for size adjustment.')
                raise exception.BadRequest(msg=msg)
        else:
            if number is not None:
                msg = _('Missing adjustment_type value for size adjustment.')
                raise exception.BadRequest(msg=msg)

        if adj_type == consts.EXACT_CAPACITY:
            number = utils.parse_int_param(consts.ADJUSTMENT_NUMBER, number)
        elif adj_type == consts.CHANGE_IN_CAPACITY:
            number = utils.parse_int_param(consts.ADJUSTMENT_NUMBER, number,
                                           allow_negative=True)
        elif adj_type == consts.CHANGE_IN_PERCENTAGE:
            try:
                number = float(number)
            except ValueError:
                raise exception.InvalidParameter(name=consts.ADJUSTMENT_NUMBER,
                                                 value=number)
            # min_step is only used (so checked) for this case
            if min_step is not None:
                min_step = utils.parse_int_param(consts.ADJUSTMENT_MIN_STEP,
                                                 min_step)

        if min_size is not None:
            min_size = utils.parse_int_param(consts.ADJUSTMENT_MIN_SIZE,
                                             min_size)
        if max_size is not None:
            max_size = utils.parse_int_param(consts.ADJUSTMENT_MAX_SIZE,
                                             max_size, allow_negative=True)
        if strict is not None:
            strict = utils.parse_bool_param(consts.ADJUSTMENT_STRICT, strict)

        db_cluster = self.cluster_find(context, identity)
        current = db_cluster.desired_capacity
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
        LOG.info(fmt, {'cluster': identity, 'adj_type': adj_type,
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
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_RESIZE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster resize action queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_scale_out(self, context, identity, count=None):
        """Inflate the size of a cluster by then given number (optional).

        :param context: Request context for the call.
        :param identity: The name, ID or short ID of a cluster.
        :param count: The number of nodes to add to the cluster. When omitted,
            a policy gets a chance to decide the count number. When specified,
            a policy would have to respect this input.

        :return: A dict with the ID of the action fired.
        """

        # Validation
        db_cluster = self.cluster_find(context, identity)
        if count is not None:
            count = utils.parse_int_param('count', count, allow_zero=False)
            err = su.check_size_params(db_cluster,
                                       db_cluster.desired_capacity + count)
            if err:
                raise exception.BadRequest(msg=err)

            LOG.info(_LI('Scaling out cluster %(name)s by %(delta)s nodes'),
                     {'name': identity, 'delta': count})
            inputs = {'count': count}
        else:
            LOG.info(_LI('Scaling out cluster %s'), db_cluster.name)
            inputs = {}

        params = {
            'name': 'cluster_scale_out_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_SCALE_OUT,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster Scale out action queued: %s"), action_id)

        return {'action': action_id}

    @request_context
    def cluster_scale_in(self, context, identity, count=None):
        """Deflate the size of a cluster by given number (optional).

        :param context: Request context for the call.
        :param identity: The name, ID or short ID of a cluster.
        :param count: The number of nodes to remove from the cluster. When
            omitted, a policy gets a chance to decide the count number. When
            specified, a policy would have to respect this input.

        :return: A dict with the ID of the action fired.
        """

        db_cluster = self.cluster_find(context, identity)

        if count is not None:
            count = utils.parse_int_param('count', count, allow_zero=False)
            err = su.check_size_params(db_cluster,
                                       db_cluster.desired_capacity - count)
            if err:
                raise exception.BadRequest(msg=err)

            LOG.info(_LI('Scaling in cluster %(name)s by %(delta)s nodes'),
                     {'name': identity, 'delta': count})
            inputs = {'count': count}
        else:
            LOG.info(_LI('Scaling in cluster %s'), db_cluster.name)
            inputs = {}

        params = {
            'name': 'cluster_scale_in_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_SCALE_IN,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster Scale in action queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_collect(self, context, identity, path, project_safe=True):
        """Collect a certain attribute across a cluster.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a cluster.
        :param path: A JSONPath-alike string containing path for a particular
                     attribute to aggregate.
        :return: A list containing values of attribute collected from all
                 nodes.
        """
        # validate 'path' string and return a parser,
        # The function may raise a BadRequest exception.
        parser = utils.get_path_parser(path)
        cluster = self.cluster_find(context, identity)
        nodes = node_mod.Node.load_all(context, cluster_id=cluster.id,
                                       project_safe=project_safe)
        attrs = []
        for node in nodes:
            info = node.to_dict()
            if node.physical_id:
                info['details'] = node.get_details(context)
            matches = [m.value for m in parser.find(info)]
            if matches:
                attrs.append({'id': node.id, 'value': matches[0]})

        return {'cluster_attributes': attrs}

    @request_context
    def cluster_check(self, context, identity, params=None):
        """Check the status of a cluster.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a cluster.
        :param params: A dictionary containing additional parameters for
                       the check operation.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Checking Cluster '%(cluster)s'."),
                 {'cluster': identity})
        db_cluster = self.cluster_find(context, identity)

        params = {
            'name': 'cluster_check_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': params,
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_CHECK, **params)
        dispatcher.start_action()
        LOG.info(_LI("Cluster check action queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_recover(self, context, identity, params=None):
        """Recover a cluster to a healthy status.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a cluster.
        :param params: A dictionary containing additional parameters for
                       the check operation.
        :return: A dictionary containing the ID of the action triggered.
        """
        LOG.info(_LI("Recovering cluster '%s'."), identity)
        db_cluster = self.cluster_find(context, identity)

        params = {
            'name': 'cluster_recover_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': params,
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
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
        :return: A DB object of Node or an exception of `NodeNotFound` if no
                 matching object is found.
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
            raise exception.NodeNotFound(node=identity)

        return node

    @request_context
    def node_list(self, context, cluster_id=None, filters=None, sort=None,
                  limit=None, marker=None, project_safe=True):
        """List node records matching the specified criteria.

        :param context: An instance of the request context.
        :param cluster_id: An optional parameter specifying the ID of the
                           cluster from which nodes are chosen.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param limit: An integer specifying the maximum number of objects to
                      return in a response.
        :param marker: An UUID specifying the node after which the result
                       list starts.
        :param project_safe: A boolean indicating whether nodes from all
                             projects will be returned.
        :return: A list of `Node` object representations.
        """
        limit = utils.parse_int_param('limit', limit)
        utils.validate_sort_param(sort, consts.NODE_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()

        # Maybe the cluster_id is a name or a short ID
        if cluster_id:
            db_cluster = self.cluster_find(context, cluster_id)
            cluster_id = db_cluster.id
        nodes = node_mod.Node.load_all(context, cluster_id=cluster_id,
                                       limit=limit, marker=marker, sort=sort,
                                       filters=filters,
                                       project_safe=project_safe)

        return [node.to_dict() for node in nodes]

    @request_context
    def node_create(self, context, name, profile_id, cluster_id=None,
                    role=None, metadata=None):
        """Create a node with provided properties.

        :param context: An instance of the request context.
        :param name: Name for the node to be created.
        :param profile_id: The ID, name or short-id of the profile to be used.
        :param cluster_id: The ID, name or short-id of the cluster in which
                           the new node will be a member. This could be None
                           if the node is to be a orphan node.
        :param role: The role for the node to play in the cluster.
        :param metadata: A dictionary containing the key-value pairs to be
                         associated with the node.
        :return: A dictionary containing the details about the node to be
                 created along with the ID of the action triggered by this
                 request.
        """
        if cfg.CONF.name_unique:
            if node_obj.Node.get_by_name(context, name):
                msg = _("The node named (%(name)s) already exists."
                        ) % {"name": name}
                raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Creating node '%s'."), name)

        if cluster_id is None:
            cluster_id = ''

        try:
            node_profile = self.profile_find(context, profile_id)
        except exception.ProfileNotFound:
            msg = _("The specified profile (%s) is not found.") % profile_id
            raise exception.BadRequest(msg=msg)

        index = -1
        if cluster_id:
            try:
                db_cluster = self.cluster_find(context, cluster_id)
            except exception.ClusterNotFound:
                msg = _("The specified cluster (%s) is not found."
                        ) % cluster_id
                raise exception.BadRequest(msg=msg)

            cluster_id = db_cluster.id
            if node_profile.id != db_cluster.profile_id:
                cluster_profile = self.profile_find(context,
                                                    db_cluster.profile_id)
                if node_profile.type != cluster_profile.type:
                    msg = _('Node and cluster have different profile type, '
                            'operation aborted.')
                    LOG.error(msg)
                    raise exception.ProfileTypeNotMatch(message=msg)
            index = cluster_obj.Cluster.get_next_index(context, cluster_id)

        # Create a node instance
        kwargs = {
            'index': index,
            'role': role,
            'metadata': metadata or {},
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
        }

        # TODO(xuhaiwei) Handle the case 'host_cluster' is not None
        if node_profile.type == 'container.docker':
            host_node = node_profile.properties.get('host_node', None)
            if host_node:
                host = self.node_get(context, host_node, project_safe=True)
                kwargs['host'] = host

        node = node_mod.Node(name, node_profile.id, cluster_id, context,
                             **kwargs)
        node.store(context)

        params = {
            'name': 'node_create_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(context, node.id,
                                             consts.NODE_CREATE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Node create action queued: %s."), action_id)

        result = node.to_dict()
        result['action'] = action_id
        return result

    @request_context
    def node_get(self, context, identity, show_details=False):
        """Get the details about a node.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a node.
        :param show_details: Optional parameter indicating whether the details
                             about the physical object should be returned.
        :return: A dictionary containing the detailed information about a node
                 or an exception of `NodeNotFound` if no matching node could
                 be found.
        """
        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, db_node=db_node)
        res = node.to_dict()
        if show_details and node.physical_id:
            res['details'] = node.get_details(context)
        return res

    @request_context
    def node_update(self, context, identity, name=None, profile_id=None,
                    role=None, metadata=None):
        """Update a node with new propertye values.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the node.
        :param name: Optional string specifying the new name for the node.
        :param profile_id: The UUID, name or short-id of the new profile to
                           be used.
        :param role: The new role for the node, if specified.
        :param metadata: A dictionary of key-value pairs to be associated with
                         the node.
        :return: A dictionary containing the updated representation of the
                 node along with the ID of the action triggered by this
                 request.
        """
        LOG.info(_LI("Updating node '%s'."), identity)

        db_node = self.node_find(context, identity)

        if profile_id:
            try:
                db_profile = self.profile_find(context, profile_id)
            except exception.ProfileNotFound:
                msg = _("The specified profile (%s) is not found."
                        ) % profile_id
                raise exception.BadRequest(msg=msg)
            profile_id = db_profile.id

            # check if profile_type matches
            old_profile = self.profile_find(context, db_node.profile_id)
            if old_profile.type != db_profile.type:
                msg = _('Cannot update a node to a different profile type, '
                        'operation aborted.')
                LOG.error(msg)
                raise exception.ProfileTypeNotMatch(message=msg)

            inputs = {'new_profile_id': profile_id}
        else:
            inputs = {}

        if name is not None and name != db_node.name:
            inputs['name'] = name
        if role is not None and role != db_node.role:
            inputs['role'] = role
        if metadata is not None and metadata != db_node.metadata:
            inputs['metadata'] = metadata

        if not inputs:
            msg = _("No property needs an update.")
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'node_update_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs,
        }
        action_id = action_mod.Action.create(context, db_node.id,
                                             consts.NODE_UPDATE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Node update action is queued: %s."), action_id)

        node = node_mod.Node.load(context, db_node=db_node)
        resp = node.to_dict()
        resp['action'] = action_id

        return resp

    @request_context
    def node_delete(self, context, identity):
        """Delete the specified node.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the node.
        :return: A dictionary containing the ID of the action triggered by
                 this request.
        """
        LOG.info(_LI('Deleting node %s'), identity)

        db_node = self.node_find(context, identity)
        params = {
            'name': 'node_delete_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
        }
        action_id = action_mod.Action.create(context, db_node.id,
                                             consts.NODE_DELETE, **params)
        dispatcher.start_action()
        LOG.info(_LI("Node delete action is queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def node_check(self, context, identity, params=None):
        """Check the health status of specified node.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the node.
        :param params: An dictionary providing additional input parameters
                       for the checking operation.
        :return: A dictionary containing the ID of the action triggered by
                 this request.
        """
        LOG.info(_LI("Checking node '%s'."), identity)

        db_node = self.node_find(context, identity)

        kwargs = {
            'name': 'node_check_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': params,
        }
        action_id = action_mod.Action.create(context, db_node.id,
                                             consts.NODE_CHECK, **kwargs)
        dispatcher.start_action()
        LOG.info(_LI("Node check action is queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def node_recover(self, context, identity, params=None):
        """Recover the specified node.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a node.
        :param params: A dictionary containing the optional parameters for
                       the requested recover operation.
        :return: A dictionary containing the ID of the action triggered by the
                 recover request.
        """
        LOG.info(_LI("Recovering node '%s'."), identity)

        db_node = self.node_find(context, identity)

        kwargs = {
            'name': 'node_recover_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': params
        }
        action_id = action_mod.Action.create(context, db_node.id,
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

    @request_context
    def cluster_policy_attach(self, context, identity, policy, enabled=True):
        """Attach a policy to the specified cluster.

        This is done via an action because a cluster lock is needed.

        :param context: An instance of request context.
        :param identity: The ID, name or short ID of the target cluster.
        :param policy: The ID, name or short ID of the target policy.
        :param enabled: Optional parameter specifying whether the policy is
                        enabled when attached.
        :return: A dictionary containg the ID of the action fired.
        """
        LOG.info(_LI("Attaching policy (%(policy)s) to cluster "
                     "(%(cluster)s)."),
                 {'policy': policy, 'cluster': identity})

        db_cluster = self.cluster_find(context, identity)
        try:
            db_policy = self.policy_find(context, policy)
        except exception.PolicyNotFound:
            msg = _("The specified policy (%s) is not found.") % policy
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'attach_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {
                'policy_id': db_policy.id,
                'enabled': utils.parse_bool_param('enabled', enabled) or True,
            }
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_ATTACH_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Policy attach action queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_policy_detach(self, context, identity, policy):
        """Detach a policy from the specified cluster.

        This is done via an action because cluster lock is needed.

        :param context: An instance of request context.
        :param identity: The ID, name or short ID of the target cluster.
        :param policy: The ID, name or short ID of the target policy.
        :return: A dictionary containg the ID of the action fired.
        """
        LOG.info(_LI("Detaching policy '%(policy)s' from cluster "
                     "'%(cluster)s'."),
                 {'policy': policy, 'cluster': identity})

        db_cluster = self.cluster_find(context, identity)
        try:
            db_policy = self.policy_find(context, policy)
        except exception.PolicyNotFound:
            msg = _("The specified policy (%s) is not found.") % policy
            raise exception.BadRequest(msg=msg)

        binding = cp_obj.ClusterPolicy.get(context, db_cluster.id,
                                           db_policy.id)
        if binding is None:
            msg = _("The policy (%(p)s) is not attached to the specified "
                    "cluster (%(c)s).") % {'p': policy, 'c': identity}
            raise exception.BadRequest(msg=msg)

        params = {
            'name': 'detach_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {'policy_id': db_policy.id},
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_DETACH_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Policy dettach action queued: %s."), action_id)

        return {'action': action_id}

    @request_context
    def cluster_policy_update(self, context, identity, policy, enabled=None):
        """Update an existing policy binding on a cluster.

        This is done via an action because cluster lock is needed.
        :param context: An instance of request context.
        :param identity: The ID, name or short ID of the target cluster.
        :param policy: The ID, name or short ID of the target policy.
        :param enabled: Optional parameter specifying whether the policy is
                        enabled after the update.
        :return: A dictionary containg the ID of the action fired.
        """
        LOG.info(_LI("Updating policy '%(policy)s' on cluster '%(cluster)s.'"),
                 {'policy': policy, 'cluster': identity})

        db_cluster = self.cluster_find(context, identity)
        try:
            db_policy = self.policy_find(context, policy)
        except exception.PolicyNotFound:
            msg = _("The specified policy (%s) is not found.") % policy
            raise exception.BadRequest(msg=msg)

        binding = cp_obj.ClusterPolicy.get(context, db_cluster.id,
                                           db_policy.id)
        if binding is None:
            msg = _("The policy (%(p)s) is not attached to the specified "
                    "cluster (%(c)s).") % {'p': policy, 'c': identity}
            raise exception.BadRequest(msg=msg)

        inputs = {'policy_id': db_policy.id}
        if enabled is not None:
            inputs['enabled'] = utils.parse_bool_param('enabled', enabled)

        params = {
            'name': 'update_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': inputs
        }
        action_id = action_mod.Action.create(context, db_cluster.id,
                                             consts.CLUSTER_UPDATE_POLICY,
                                             **params)
        dispatcher.start_action()
        LOG.info(_LI("Policy update action queued: %s."), action_id)

        return {'action': action_id}

    def action_find(self, context, identity, project_safe=True):
        """Find an action with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an action.
        :return: A DB object of action or an exception `ActionNotFound` if no
                 matching action is found.
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
            raise exception.ActionNotFound(action=identity)

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
                 exception `ActionNotFound` if no matching action is found.
        """
        db_action = self.action_find(context, identity)
        action = action_mod.Action.load(context, db_action=db_action)
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
        except exception.ResourceBusyError:
            raise exception.ResourceInUse(resource_type='action',
                                          resource_id=db_action.id)

        LOG.info(_LI("Action '%s' is deleted."), identity)

    def receiver_find(self, context, identity, project_safe=True):
        """Find a receiver with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :param project_safe: A boolean indicating whether receiver from other
                             projects other than the requesting one can be
                             returned.
        :return: A DB object of receiver or an exception `ReceiverNotFound`
                 if no matching reciever is found.
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
            raise exception.ReceiverNotFound(receiver=identity)

        return receiver

    @request_context
    def receiver_list(self, context, limit=None, marker=None, sort=None,
                      filters=None, project_safe=True):
        """List receivers matching the specified criteria.

        :param context: An instance of the request context.
        :param limit: An integer specifying the maximum number of objects to
                      return in a response.
        :param marker: An UUID specifying the receiver after which the result
                       list starts.
        :param sort: A list of sorting keys (each optionally attached with a
                     sorting direction) separated by commas.
        :param filters: A dictionary of key-value pairs for filtering out the
                        result list.
        :param project_safe: A boolean indicating whether receivers from all
                             projects will be returned.
        :return: A list of `Receiver` object representations.
        """
        limit = utils.parse_int_param('limit', limit)
        utils.validate_sort_param(sort, consts.RECEIVER_SORT_KEYS)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        if not project_safe and not context.is_admin:
            raise exception.Forbidden()
        receivers = receiver_mod.Receiver.load_all(context, limit=limit,
                                                   marker=marker,
                                                   sort=sort, filters=filters,
                                                   project_safe=project_safe)
        return [r.to_dict() for r in receivers]

    @request_context
    def receiver_create(self, context, name, type_name, cluster_id, action,
                        actor=None, params=None):
        """Create a receiver.

        :param context: An instance of the request context.
        :param name: Name of the receiver.
        :param type_name: Name of the receiver type, subject to validation.
        :param cluster_id: UUID, name or short-id of a cluster.
        :param action: Name or ID of an action, currently only builtin action
                       names are supported.
        :param actor: Future extension.
        :param params: A dictionary containing key-value pairs as inputs to
                       the action.
        :return: A dictionary containing the details about the receiver
                 created.
        """
        if cfg.CONF.name_unique:
            if receiver_obj.Receiver.get_by_name(context, name):
                msg = _("A receiver named '%s' already exists.") % name
                raise exception.BadRequest(msg=msg)

        LOG.info(_LI("Creating receiver %(n)s: \n"
                     "  type: %(t)s\n  cluster: %(c)s\n  action: %(a)s."),
                 {'n': name, 't': type_name, 'c': cluster_id, 'a': action})

        rtype = type_name.lower()
        if rtype not in consts.RECEIVER_TYPES:
            msg = _("Receiver type '%s' is not supported.") % rtype
            raise exception.BadRequest(msg=msg)

        # Check whether cluster identified by cluster_id does exist
        cluster = None
        try:
            cluster = self.cluster_find(context, cluster_id)
        except exception.ClusterNotFound:
            msg = _("The referenced cluster '%s' is not found.") % cluster_id
            raise exception.BadRequest(msg=msg)

        # permission checking
        if not context.is_admin and context.user != cluster.user:
            raise exception.Forbidden()

        # Check action name
        if action not in consts.ACTION_NAMES:
            msg = _("Illegal action '%s' specified.") % action
            raise exception.BadRequest(msg=msg)

        if action.lower().split('_')[0] != 'cluster':
            msg = _("Action '%s' is not applicable to clusters.") % action
            raise exception.BadRequest(msg=msg)

        if not params:
            params = {}
        kwargs = {
            'name': name,
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'params': params
        }

        receiver = receiver_mod.Receiver.create(context, rtype, cluster,
                                                action, **kwargs)
        LOG.info(_LI("Receiver (%(n)s) is created: %(i)s."),
                 {'n': name, 'i': receiver.id})

        return receiver.to_dict()

    @request_context
    def receiver_get(self, context, identity, project_safe=True):
        """Get the details about a receiver.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :param project_safe: Whether matching object from other projects can
                             be returned.
        :return: A dictionary containing the details about a receiver or
                 an exception `ReceiverNotFound` if no matching object found.
        """
        db_receiver = self.receiver_find(context, identity,
                                         project_safe=project_safe)
        receiver = receiver_mod.Receiver.load(context,
                                              receiver_obj=db_receiver,
                                              project_safe=project_safe)
        return receiver.to_dict()

    @request_context
    def receiver_delete(self, context, identity):
        """Delete the specified receiver.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :return: None if successfully deleted the receiver or an exception of
                 `ReceiverNotFound` if the object could not be found.
        """
        db_receiver = self.receiver_find(context, identity)
        LOG.info(_LI("Deleting receiver %s."), identity)
        receiver_obj.Receiver.delete(context, db_receiver.id)
        LOG.info(_LI("Receiver %s is deleted."), identity)

    @request_context
    def webhook_trigger(self, context, identity, params=None):

        LOG.info(_LI("Triggering webhook (%s)."), identity)
        receiver = self.receiver_find(context, identity)

        try:
            cluster = self.cluster_find(context, receiver.cluster_id)
        except exception.ClusterNotFound:
            msg = _("The referenced cluster (%s) is not found."
                    ) % receiver.cluster_id
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
            raise exception.EventNotFound(event=identity)

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

        results = [event.as_dict() for event in all_events]
        return results

    @request_context
    def event_get(self, context, identity):
        """Get the details about a specified event.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an event.
        :return: A dictionary containing the details about the event or an
                 exception of `EventNotFound` if no matching record could be
                 found.
        """
        db_event = self.event_find(context, identity)
        return db_event.as_dict()
