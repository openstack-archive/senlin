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
import datetime
import functools
import uuid

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
from senlin.common import schema
from senlin.common import utils
from senlin.db import api as db_api
from senlin.engine.actions import base as action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import cluster_policy
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import event as event_mod
from senlin.engine import health_manager
from senlin.engine import node as node_mod
from senlin.engine import receiver as receiver_mod
from senlin.engine import scheduler
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
        self.engine_id = str(uuid.uuid4())
        self.init_tgm()

        # create a dispatcher greenthread for this engine.
        self.dispatcher = dispatcher.Dispatcher(self,
                                                self.dispatcher_topic,
                                                consts.RPC_API_VERSION,
                                                self.TG)
        LOG.info(_LI("Starting dispatcher for engine %s"), self.engine_id)
        self.dispatcher.start()

        # create a health manager greenthread for this engine.
        self.health_mgr = health_manager.Health_Manager(self,
                                                        self.health_mgr_topic,
                                                        consts.RPC_API_VERSION,
                                                        self.TG)
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
        svc = db_api.service_get(self.engine_id)
        if svc is None:
            params = dict(host=self.host,
                          binary='senlin-engine',
                          service_id=self.engine_id,
                          topic=self.topic)
            db_api.service_create(**params)
            LOG.debug('Service %s is started' % self.engine_id)
        else:
            try:
                db_api.service_update(self.engine_id)
                LOG.debug('Service %s is updated' % self.engine_id)
            except Exception as ex:
                LOG.error(_LE('Service %(service_id)s update '
                              'failed: %(error)s'),
                          {'service_id': self.engine_id, 'error': ex})

    def service_manage_cleanup(self):
        last_updated_window = (3 * cfg.CONF.periodic_interval)
        time_line = timeutils.utcnow() - datetime.timedelta(
            seconds=last_updated_window)
        svcs = db_api.service_get_all()
        for svc in svcs:
            if svc['id'] == self.engine_id:
                continue
            if svc['updated_at'] < time_line:
                # hasn't been updated, assuming it's died.
                LOG.info(_LI('Service %s was aborted'), svc['id'])
                db_api.service_delete(svc['id'])

    @request_context
    def get_revision(self, context):
        return cfg.CONF.revision['senlin_engine_revision']

    @request_context
    def profile_type_list(self, context):
        return environment.global_env().get_profile_types()

    @request_context
    def profile_type_get(self, context, type_name):
        profile = environment.global_env().get_profile(type_name)
        data = profile.get_schema()

        return {
            'name': type_name,
            'schema': data,
        }

    def profile_find(self, context, identity):
        '''Find a profile with the given identity (could be name or ID).'''
        if uuidutils.is_uuid_like(identity):
            profile = db_api.profile_get(context, identity)
            if not profile:
                profile = db_api.profile_get_by_name(context, identity)
        else:
            profile = db_api.profile_get_by_name(context, identity)
            if not profile:
                profile = db_api.profile_get_by_short_id(context, identity)

        if not profile:
            raise exception.ProfileNotFound(profile=identity)

        return profile

    @request_context
    def profile_list(self, context, limit=None, marker=None, sort=None,
                     filters=None, project_safe=True):
        if limit is not None:
            limit = utils.parse_int_param('limit', limit)
        profiles = profile_base.Profile.load_all(context,
                                                 limit=limit, marker=marker,
                                                 sort=sort, filters=filters,
                                                 project_safe=project_safe)

        return [p.to_dict() for p in profiles]

    @request_context
    def profile_create(self, context, name, spec, metadata=None):
        if cfg.CONF.name_unique:
            if db_api.profile_get_by_name(context, name):
                msg = _("The profile (%(name)s) already exists."
                        ) % {"name": name}
                raise exception.SenlinBadRequest(msg=msg)

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        try:
            plugin = environment.global_env().get_profile(type_str)
        except exception.ProfileTypeNotFound:
            msg = _("The specified profile type (%(name)s) is not supported."
                    ) % {"name": type_str}
            raise exception.SenlinBadRequest(msg=msg)

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
            raise exception.SenlinBadRequest(msg=msg)

        profile.store(context)

        LOG.info(_LI("Profile %(name)s is created: %(id)s."),
                 {'name': name, 'id': profile.id})

        return profile.to_dict()

    @request_context
    def profile_get(self, context, identity):
        db_profile = self.profile_find(context, identity)
        profile = profile_base.Profile.load(context, profile=db_profile)
        return profile.to_dict()

    @request_context
    def profile_update(self, context, profile_id, name=None, metadata=None):
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

        LOG.info(_LI("Profile '%(id)s' is updated."), {'id': profile_id})
        return profile.to_dict()

    @request_context
    def profile_delete(self, context, identity):
        db_profile = self.profile_find(context, identity)
        LOG.info(_LI("Deleting profile '%s'."), identity)
        try:
            profile_base.Profile.delete(context, db_profile.id)
        except exception.ResourceBusyError:
            LOG.error(_LI("Profile '%s' cannot be deleted."), identity)
            raise exception.ResourceInUse(resource_type='profile',
                                          resource_id=db_profile.id)

        LOG.info(_LI("Profile '%(id)s' is deleted."), {'id': identity})

    @request_context
    def policy_type_list(self, context):
        return environment.global_env().get_policy_types()

    @request_context
    def policy_type_get(self, context, type_name):
        policy_type = environment.global_env().get_policy(type_name)
        data = policy_type.get_schema()

        return {
            'name': type_name,
            'schema': data
        }

    def policy_find(self, context, identity):
        '''Find a policy with the given identity (could be name or ID).'''

        if uuidutils.is_uuid_like(identity):
            policy = db_api.policy_get(context, identity)
            if not policy:
                policy = db_api.policy_get_by_name(context, identity)
        else:
            policy = db_api.policy_get_by_name(context, identity)
            if not policy:
                policy = db_api.policy_get_by_short_id(context, identity)

        if not policy:
            raise exception.PolicyNotFound(policy=identity)

        return policy

    @request_context
    def policy_list(self, context, limit=None, marker=None, sort=None,
                    filters=None, project_safe=True):
        if limit is not None:
            limit = utils.parse_int_param('limit', limit)
        policies = policy_base.Policy.load_all(context,
                                               limit=limit, marker=marker,
                                               sort=sort, filters=filters,
                                               project_safe=project_safe)
        return [p.to_dict() for p in policies]

    @request_context
    def policy_create(self, context, name, spec):
        if cfg.CONF.name_unique:
            if db_api.policy_get_by_name(context, name):
                msg = _("The policy (%(name)s) already exists."
                        ) % {"name": name}
                raise exception.SenlinBadRequest(msg=msg)

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])
        try:
            plugin = environment.global_env().get_policy(type_str)
        except exception.PolicyTypeNotFound:
            msg = _("The specified policy type (%(name)s) is not supported."
                    ) % {"name": type_str}
            raise exception.SenlinBadRequest(msg=msg)

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
            raise exception.SenlinBadRequest(msg=msg)

        policy.store(context)
        LOG.info(_LI("Policy '%(name)s' is created: %(id)s."),
                 {'name': name, 'id': policy.id})
        return policy.to_dict()

    @request_context
    def policy_get(self, context, identity):
        db_policy = self.policy_find(context, identity)
        policy = policy_base.Policy.load(context, db_policy=db_policy)
        return policy.to_dict()

    @request_context
    def policy_update(self, context, identity, name):

        db_policy = self.policy_find(context, identity)
        policy = policy_base.Policy.load(context, db_policy=db_policy)

        if not name:
            msg = _('Policy name not specified.')
            raise exception.SenlinBadRequest(msg=msg)

        if name != policy.name:
            LOG.info(_LI("Updating policy '%s'."), identity)
            policy.name = name
            policy.store(context)
            LOG.info(_LI("Policy '%s' is updated."), identity)

        return policy.to_dict()

    @request_context
    def policy_delete(self, context, identity):
        db_policy = self.policy_find(context, identity)
        LOG.info(_LI("Delete policy '%s'."), identity)
        try:
            policy_base.Policy.delete(context, db_policy.id)
        except exception.ResourceBusyError:
            LOG.error(_LI("Policy '%s' cannot be deleted."), identity)
            raise exception.ResourceInUse(resource_type='policy',
                                          resource_id=db_policy.id)

        LOG.info(_LI("Policy '%s' is deleted."), identity)

    @request_context
    def cluster_list(self, context, limit=None, marker=None, sort=None,
                     filters=None, project_safe=True, show_nested=False):
        limit = utils.parse_int_param('limit', limit)
        project_safe = utils.parse_bool_param('project_safe', project_safe)
        show_nested = utils.parse_bool_param('show_nested', show_nested)
        clusters = cluster_mod.Cluster.load_all(context, limit=limit,
                                                marker=marker, sort=sort,
                                                filters=filters,
                                                project_safe=project_safe,
                                                show_nested=show_nested)

        return [cluster.to_dict() for cluster in clusters]

    def cluster_find(self, context, identity):
        '''Find a cluster with the given identity (could be name or ID).'''

        if uuidutils.is_uuid_like(identity):
            cluster = db_api.cluster_get(context, identity)
            if not cluster:
                cluster = db_api.cluster_get_by_name(context, identity)
        else:
            cluster = db_api.cluster_get_by_name(context, identity)
            # maybe it is a short form of UUID
            if not cluster:
                cluster = db_api.cluster_get_by_short_id(context, identity)

        if not cluster:
            raise exception.ClusterNotFound(cluster=identity)

        return cluster

    @request_context
    def cluster_get(self, context, identity):
        db_cluster = self.cluster_find(context, identity)
        cluster = cluster_mod.Cluster.load(context, cluster=db_cluster)
        return cluster.to_dict()

    def _validate_cluster_size_params(self, desired_capacity, min_size,
                                      max_size):
        # validate data type first
        if desired_capacity is not None:
            desired_capacity = utils.parse_int_param(
                consts.CLUSTER_DESIRED_CAPACITY, desired_capacity)
        if min_size is not None:
            min_size = utils.parse_int_param(consts.CLUSTER_MIN_SIZE, min_size)
        if max_size is not None:
            max_size = utils.parse_int_param(consts.CLUSTER_MAX_SIZE, max_size,
                                             allow_negative=True)

        # validate parameter range
        if min_size is not None and desired_capacity is not None:
            if min_size > desired_capacity:
                msg = _("Cluster min_size, if specified, must be lesser than "
                        "or equal to its desired_capacity.")
                raise exception.SenlinBadRequest(msg=msg)

        if max_size is not None and desired_capacity is not None:
            if max_size >= 0 and max_size < desired_capacity:
                msg = _("Cluster max_size, if specified, must be greater than"
                        " or equal to its desired_capacity. Setting max_size"
                        " to -1 means no upper limit on cluster size.")
                raise exception.SenlinBadRequest(msg=msg)

        if min_size is not None and max_size is not None:
            if max_size >= 0 and max_size < min_size:
                msg = _("Cluster max_size, if specified, must be greater than"
                        " or equal to its min_size. Setting max_size to -1"
                        " means no upper limit on cluster size.")
                raise exception.SenlinBadRequest(msg=msg)

        return (desired_capacity, min_size, max_size)

    @request_context
    def cluster_create(self, context, name, desired_capacity, profile_id,
                       min_size=None, max_size=None, parent=None,
                       metadata=None, timeout=None):
        if cfg.CONF.name_unique:
            if db_api.cluster_get_by_name(context, name):
                msg = _("The cluster (%(name)s) already exists."
                        ) % {"name": name}
                raise exception.SenlinBadRequest(msg=msg)

        try:
            db_profile = self.profile_find(context, profile_id)
        except exception.ProfileNotFound:
            msg = _("The specified profile '%s' is not found.") % profile_id
            raise exception.SenlinBadRequest(msg=msg)

        LOG.info(_LI("Creating cluster '%s'."), name)
        (init_size, min_size, max_size) = self._validate_cluster_size_params(
            desired_capacity, min_size, max_size)

        if timeout is not None:
            timeout = utils.parse_int_param(consts.CLUSTER_TIMEOUT, timeout)

        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'parent': parent,
            'min_size': min_size,
            'max_size': max_size,
            'timeout': timeout,
            'metadata': metadata,
        }

        cluster = cluster_mod.Cluster(name, init_size, db_profile.id, **kwargs)
        cluster.store(context)

        # Build an Action for cluster creation
        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'cluster_create_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC
        }
        action = action_mod.Action(cluster.id, consts.CLUSTER_CREATE, **kwargs)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster create action queued: %s."), action.id)

        return cluster.to_dict()

    @request_context
    def cluster_update(self, context, identity, name=None, profile_id=None,
                       parent=None, metadata=None, timeout=None):

        LOG.info(_LI("Updating cluster '%s'."), identity)
        # Get the database representation of the existing cluster
        db_cluster = self.cluster_find(context, identity)
        cluster = cluster_mod.Cluster.load(context, cluster=db_cluster)
        if cluster.status == cluster.ERROR:
            msg = _('Updating a cluster in error state')
            LOG.error(msg)
            raise exception.FeatureNotSupported(feature=msg)

        inputs = {}
        if profile_id is not None:
            old_profile = self.profile_find(context, cluster.profile_id)
            try:
                new_profile = self.profile_find(context, profile_id)
            except exception.ProfileNotFound:
                msg = _("The specified profile '%s' is "
                        "not found.") % profile_id
                raise exception.SenlinBadRequest(msg=msg)

            if new_profile.type != old_profile.type:
                msg = _('Cannot update a cluster to a different profile type, '
                        'operation aborted.')
                raise exception.ProfileTypeNotMatch(message=msg)
            if old_profile.id != new_profile.id:
                inputs['new_profile_id'] = new_profile.id

        if metadata is not None and metadata != cluster.metadata:
            md = cluster.metadata
            md.update(metadata)
            inputs['metadata'] = md

        if parent is not None:
            db_parent = self.cluster_find(context, parent)
            inputs['parent'] = db_parent.id

        if timeout is not None:
            timeout = utils.parse_int_param(consts.CLUSTER_TIMEOUT, timeout)
            inputs['timeout'] = timeout

        if name is not None:
            inputs['name'] = name

        kwargs = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'cluster_update_%s' % cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(cluster.id, consts.CLUSTER_UPDATE, **kwargs)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster update action queued: %s."), action.id)
        resp = cluster.to_dict()
        resp['action'] = action.id
        return resp

    @request_context
    def cluster_add_nodes(self, context, identity, nodes):

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
                elif db_node.cluster_id is not None:
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
            error = _("Profile type of nodes %s does not match with "
                      "cluster") % not_match_nodes
            LOG.error(error)
            raise exception.ProfileTypeNotMatch(message=error)
        elif len(owned_nodes) > 0:
            error = _("Nodes %s already owned by some cluster") % owned_nodes
            LOG.error(error)
            raise exception.NodeNotOrphan(message=error)
        elif len(bad_nodes) > 0:
            error = _("Nodes are not ACTIVE: %s") % bad_nodes
        elif len(not_found) > 0:
            error = _("Nodes not found: %s") % not_found
        elif len(found) == 0:
            error = _("No nodes to add: %s") % nodes

        if error is not None:
            LOG.error(error)
            raise exception.SenlinBadRequest(msg=error)

        action_name = 'cluster_add_nodes_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': {'nodes': found}
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_ADD_NODES,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)
        LOG.info(_LI("Cluster add nodes action queued: %s."), action.id)
        return {'action': action.id}

    @request_context
    def cluster_del_nodes(self, context, identity, nodes):
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
            error = _("Nodes not found: %s") % not_found
        elif len(bad_nodes):
            error = _("Nodes not members of specified cluster: %s") % bad_nodes
        elif len(found) == 0:
            error = _("No nodes specified.")

        if error is not None:
            LOG.error(error)
            raise exception.SenlinBadRequest(msg=error)

        action_name = 'cluster_del_nodes_%s' % db_cluster.id[:8]
        count = len(found)
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': {
                'candidates': found,
                'count': count
            }
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_DEL_NODES,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster delete nodes action queued: %s."), action.id)
        return {'action': action.id}

    @request_context
    def cluster_check(self, context, identity, **params):
        LOG.info(_LI("Checking Cluster '%(cluster)s'."),
                 {'cluster': identity})
        db_cluster = self.cluster_find(context, identity)

        action_name = 'cluster_check_%s' % db_cluster.id[:8]
        new_params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': params
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_CHECK,
                                   **new_params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)
        LOG.info(_LI("Cluster check action queued: %s."), action.id)
        return {'action': action.id}

    @request_context
    def cluster_recover(self, context, identity, **params):
        LOG.info(_LI("Recovering cluster '%(cluster)s'."),
                 {'cluster': identity})
        db_cluster = self.cluster_find(context, identity)

        action_name = 'cluster_recover_%s' % db_cluster.id[:8]
        new_params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': params
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_RECOVER,
                                   **new_params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)
        LOG.info(_LI("Cluster recover action queued: %s."), action.id)
        return {'action': action.id}

    @request_context
    def cluster_resize(self, context, identity, adj_type=None, number=None,
                       min_size=None, max_size=None, min_step=None,
                       strict=True):
        '''Adjust cluster size parameters.

        :param identity: cluster dentity which can be name, id or short ID;
        :param adj_type: optional; if specified, must be one of the strings
                         defined in consts.ADJUSTMENT_TYPES;
        :param number: number for adjustment. It is interpreted as the new
                       desired_capacity of the cluster if `adj_type` is set
                       to `EXACT_CAPACITY`; it is interpreted as the relative
                       number of nodes to add/remove when `adj_type` is set
                       to `CHANGE_IN_CAPACITY`; it is treated as a percentage
                       when `adj_type` is set to `CHANGE_IN_PERCENTAGE`.
                       This parameter is optional.
        :param min_size: new lower bound of the cluster size, if specified.
                         This parameter is optional.
        :param max_size: new upper bound of the cluster size, if specified;
                         A value of negative means no upper limit is imposed.
                         This parameter is optional.
        :param min_step: optional. It specifies the number of nodes to be
                         added or removed when `adj_type` is set to value
                         `CHANGE_IN_PERCENTAGE` and the number calculated is
                         less than 1 or so.
        :param strict: optional boolean value. It specifies whether Senlin
                       should try a best-effort style resizing or just
                       reject the request when scaling beyond its current
                       size constraint.
        '''

        # check adj_type
        if adj_type is not None:
            if adj_type not in consts.ADJUSTMENT_TYPES:
                raise exception.InvalidParameter(
                    name=consts.ADJUSTMENT_TYPE, value=adj_type)
            if number is None:
                msg = _('Missing number value for size adjustment.')
                raise exception.SenlinBadRequest(msg=msg)
        else:
            if number is not None:
                msg = _('Missing adjustment_type value for size adjustment.')
                raise exception.SenlinBadRequest(msg=msg)

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

        # validate min_size and max_size
        (_d, min_size, max_size) = self._validate_cluster_size_params(
            None, min_size, max_size)

        # Get the database representation of the existing cluster
        db_cluster = self.cluster_find(context, identity)

        fmt = _LI("Resizing cluster '%(cluster)s': type=%(adj_type)s, "
                  "number=%(number)s, min_size=%(min_size)s, "
                  "max_size=%(max_size)s, min_step=%(min_step)s, "
                  "strict=%(strict)s.")
        LOG.info(fmt, {'cluster': identity, 'adj_type': adj_type,
                       'number': number, 'min_size': min_size,
                       'max_size': max_size, 'min_step': min_step,
                       'strict': strict})

        inputs = {
            consts.ADJUSTMENT_TYPE: adj_type,
            consts.ADJUSTMENT_NUMBER: number,
            consts.ADJUSTMENT_MIN_SIZE: min_size,
            consts.ADJUSTMENT_MAX_SIZE: max_size,
            consts.ADJUSTMENT_MIN_STEP: min_step,
            consts.ADJUSTMENT_STRICT: strict
        }

        action_name = 'cluster_resize_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_RESIZE,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster resize action queued: %s."), action.id)

        return {'action': action.id}

    @request_context
    def cluster_scale_out(self, context, identity, count=None):

        LOG.info(_LI("Scaling out cluster '%s'."), identity)
        # Validation
        db_cluster = self.cluster_find(context, identity)
        delta = utils.parse_int_param('count', count, allow_zero=False)

        if delta is not None:
            LOG.info(_LI('Scaling out cluster %(name)s by %(delta)s nodes'),
                     {'name': identity, 'delta': delta})
            inputs = {'count': delta}
        else:
            LOG.info(_LI('Scaling out cluster %s'), db_cluster.name)
            inputs = {}

        action_name = 'cluster_scale_out_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_SCALE_OUT,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster Scale out action queued: %s"), action.id)

        return {'action': action.id}

    @request_context
    def cluster_scale_in(self, context, identity, count=None):

        LOG.info(_LI("Scaling in cluster '%s'."), identity)

        db_cluster = self.cluster_find(context, identity)
        # delta must be positive integer
        delta = utils.parse_int_param('count', count, allow_zero=False)

        if delta is not None:
            LOG.info(_LI('Scaling in cluster %(name)s by %(delta)s nodes'),
                     {'name': identity, 'delta': delta})
            inputs = {'count': delta}
        else:
            LOG.info(_LI('Scaling in cluster %s'), db_cluster.name)
            inputs = {}

        action_name = 'cluster_scale_in_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_SCALE_IN,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster Scale in action queued: %s."), action.id)

        return {'action': action.id}

    @request_context
    def cluster_delete(self, context, identity):

        LOG.info(_LI('Deleting cluster %s'), identity)

        db_cluster = self.cluster_find(context, identity)

        policies = db_api.cluster_policy_get_all(context, db_cluster.id)
        if len(policies) > 0:
            msg = _('Cluster %(id)s cannot be deleted without having all '
                    'policies detached.') % {'id': identity}
            LOG.error(msg)
            raise exception.SenlinBadRequest(msg=msg)

        receivers = db_api.receiver_get_all(context, filters={'cluster_id':
                                            db_cluster.id})
        if len(receivers) > 0:
            msg = _('Cluster %(id)s cannot be deleted without having all '
                    'receivers deleted.') % {'id': identity}
            LOG.error(msg)
            raise exception.SenlinBadRequest(msg=msg)

        action_name = 'cluster_delete_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_DELETE,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Cluster delete action queued: %s"), action.id)

        return db_cluster.id

    def node_find(self, context, identity):
        '''Find a node with the given identity (could be name or ID).'''

        if uuidutils.is_uuid_like(identity):
            node = db_api.node_get(context, identity)
            if not node:
                node = db_api.node_get_by_name(context, identity)
        else:
            node = db_api.node_get_by_name(context, identity)
            if not node:
                node = db_api.node_get_by_short_id(context, identity)

        if node is None:
            raise exception.NodeNotFound(node=identity)

        return node

    @request_context
    def node_list(self, context, cluster_id=None, filters=None, sort=None,
                  limit=None, marker=None, project_safe=True):

        limit = utils.parse_int_param('limit', limit)
        project_safe = utils.parse_bool_param('project_safe', project_safe)

        # Maybe the cluster_id is a name or a short ID
        if cluster_id is not None:
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
        if cfg.CONF.name_unique:
            if db_api.node_get_by_name(context, name):
                msg = _("The node (%(name)s) already exists.") % {"name": name}
                raise exception.SenlinBadRequest(msg=msg)

        LOG.info(_LI("Creating node '%s'."), name)

        if cluster_id is None:
            cluster_id = ''

        index = -1
        try:
            node_profile = self.profile_find(context, profile_id)
        except exception.ProfileNotFound:
            msg = _("The specified profile (%s) is not found.") % profile_id
            raise exception.SenlinBadRequest(msg=msg)

        if cluster_id:
            try:
                db_cluster = self.cluster_find(context, cluster_id)
            except exception.ClusterNotFound:
                msg = _("The specified cluster (%s) is not found."
                        ) % cluster_id
                raise exception.SenlinBadRequest(msg=msg)

            cluster_id = db_cluster.id
            if profile_id != db_cluster.profile_id:
                cluster_profile = self.profile_find(context,
                                                    db_cluster.profile_id)
                if node_profile.type != cluster_profile.type:
                    msg = _('Node and cluster have different profile type, '
                            'operation aborted.')
                    LOG.error(msg)
                    raise exception.ProfileTypeNotMatch(message=msg)
            index = db_api.cluster_next_index(context, cluster_id)

        # Create a node instance
        kwargs = {
            'index': index,
            'role': role,
            'metadata': metadata or {},
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
        }

        node = node_mod.Node(name, node_profile.id, cluster_id, context,
                             **kwargs)
        node.store(context)

        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'node_create_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC
        }
        action = action_mod.Action(node.id, consts.NODE_CREATE, **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Node create action queued: %s."), action.id)

        return node.to_dict()

    @request_context
    def node_get(self, context, identity, show_details=False):
        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, node=db_node)
        res = node.to_dict()
        if node.physical_id is not None and node.physical_id != '':
            if show_details:
                res['details'] = node.get_details(context)
            else:
                res['details'] = {}
        return res

    @request_context
    def node_update(self, context, identity, name=None, profile_id=None,
                    role=None, metadata=None):

        LOG.info(_LI("Updating node '%s'."), identity)

        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, node=db_node)

        if profile_id:
            try:
                db_profile = self.profile_find(context, profile_id)
            except exception.ProfileNotFound:
                msg = _("The specified profile (%s) is not found."
                        ) % profile_id
                raise exception.SenlinBadRequest(msg=msg)
            profile_id = db_profile.id

            # check if profile_type matches
            old_profile = self.profile_find(context, node.profile_id)
            if old_profile.type != db_profile.type:
                msg = _('Cannot update a node to a different profile type, '
                        'operation aborted.')
                LOG.error(msg)
                raise exception.ProfileTypeNotMatch(message=msg)

        inputs = {
            'new_profile_id': profile_id,
        }
        # TODO(xuhaiwei): Move all the attributes update into action execution
        if name is not None and name != node.name:
            inputs['name'] = name
        if role is not None and role != node.role:
            inputs['role'] = role
        if metadata is not None and metadata != node.metadata:
            inputs['metadata'] = metadata

        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'node_update_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(node.id, consts.NODE_UPDATE, **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Node update action is queued: %s."), action.id)

        return node.to_dict()

    @request_context
    def node_delete(self, context, identity, force=False):
        LOG.info(_LI('Deleting node %s'), identity)

        db_node = self.node_find(context, identity)
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'node_delete_%s' % db_node.id[:8],
            'cause': action_mod.CAUSE_RPC
        }
        action = action_mod.Action(db_node.id, consts.NODE_DELETE, **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Node delete action is queued: %s."), action.id)

        return db_node.id

    @request_context
    def node_check(self, context, identity, **params):

        LOG.info(_LI("Checking node '%s'."), identity)

        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, node=db_node)

        new_params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'node_check_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'inputs': params
        }
        action = action_mod.Action(node.id, consts.NODE_CHECK, **new_params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Node check action is queued: %s."), action.id)

        return node.to_dict()

    @request_context
    def node_recover(self, context, identity, **params):

        LOG.info(_LI("Recovering node '%s'."), identity)

        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, node=db_node)

        new_params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'node_recover_%s' % node.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'inputs': params
        }
        action = action_mod.Action(node.id, consts.NODE_RECOVER, **new_params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Node recover action is queued: %s."), action.id)

        return node.to_dict()

    @request_context
    def cluster_policy_list(self, context, identity, filters=None, sort=None):

        db_cluster = self.cluster_find(context, identity)
        bindings = cluster_policy.ClusterPolicy.load_all(
            context, db_cluster.id, filters=filters, sort=sort)

        return [binding.to_dict() for binding in bindings]

    @request_context
    def cluster_policy_get(self, context, identity, policy_id):
        db_cluster = self.cluster_find(context, identity)
        db_policy = self.policy_find(context, policy_id)

        try:
            binding = cluster_policy.ClusterPolicy.load(
                context, db_cluster.id, db_policy.id)
        except exception.PolicyNotAttached:
            raise exception.PolicyBindingNotFound(policy=policy_id,
                                                  identity=identity)

        return binding.to_dict()

    @request_context
    def cluster_policy_attach(self, context, identity, policy, enabled=True):
        '''Attach policy to cluster.

        This is done via an action because a cluster lock is needed.
        '''
        LOG.info(_LI("Attaching policy (%(policy)s) to cluster "
                     "(%(cluster)s)."),
                 {'policy': policy, 'cluster': identity})

        db_cluster = self.cluster_find(context, identity)
        try:
            db_policy = self.policy_find(context, policy)
        except exception.PolicyNotFound:
            msg = _("The specified policy (%s) is not found.") % policy
            raise exception.SenlinBadRequest(msg=msg)

        inputs = {
            'policy_id': db_policy.id,
            'enabled': utils.parse_bool_param('enabled', enabled) or True,
        }

        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': 'attach_policy_%s' % db_cluster.id[:8],
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_ATTACH_POLICY,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Policy attach action queued: %s."), action.id)

        return {'action': action.id}

    @request_context
    def cluster_policy_detach(self, context, identity, policy):
        '''Detach policy from cluster.

        This is done via an action because cluster lock is needed.
        '''

        LOG.info(_LI("Detaching policy '%(policy)s' from cluster "
                     "'%(cluster)s'."),
                 {'policy': policy, 'cluster': identity})

        db_cluster = self.cluster_find(context, identity)
        try:
            db_policy = self.policy_find(context, policy)
        except exception.PolicyNotFound:
            msg = _("The specified policy (%s) is not found.") % policy
            raise exception.SenlinBadRequest(msg=msg)

        binding = db_api.cluster_policy_get(context, db_cluster.id,
                                            db_policy.id)
        if binding is None:
            msg = _("The policy (%(p)s) is not attached to the specified "
                    "cluster (%(c)s).") % {'p': policy, 'c': identity}
            raise exception.SenlinBadRequest(msg=msg)

        action_name = 'detach_policy_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': {'policy_id': db_policy.id}
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_DETACH_POLICY,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Policy dettach action queued: %s."), action.id)

        return {'action': action.id}

    @request_context
    def cluster_policy_update(self, context, identity, policy, enabled=None):
        '''Update an existing policy binding on a cluster.

        This is done via an action because cluster lock is needed.
        '''
        LOG.info(_LI("Updating policy '%(policy)s' on cluster '%(cluster)s.'"),
                 {'policy': policy, 'cluster': identity})

        db_cluster = self.cluster_find(context, identity)
        try:
            db_policy = self.policy_find(context, policy)
        except exception.PolicyNotFound:
            msg = _("The specified policy (%s) is not found.") % policy
            raise exception.SenlinBadRequest(msg=msg)

        binding = db_api.cluster_policy_get(context, db_cluster.id,
                                            db_policy.id)
        if binding is None:
            msg = _("The policy (%(p)s) is not attached to the specified "
                    "cluster (%(c)s).") % {'p': policy, 'c': identity}
            raise exception.SenlinBadRequest(msg=msg)

        inputs = {'policy_id': db_policy.id}
        if enabled is not None:
            inputs['enabled'] = utils.parse_bool_param('enabled', enabled)

        action_name = 'update_policy_%s' % db_cluster.id[:8]
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': inputs
        }
        action = action_mod.Action(db_cluster.id, consts.CLUSTER_UPDATE_POLICY,
                                   **params)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Policy update action queued: %s."), action.id)

        return {'action': action.id}

    def action_find(self, context, identity):
        '''Find an action with the given identity (could be name or ID).'''
        if uuidutils.is_uuid_like(identity):
            action = db_api.action_get(context, identity)
            if not action:
                action = db_api.action_get_by_name(context, identity)
        else:
            action = db_api.action_get_by_name(context, identity)
            if not action:
                action = db_api.action_get_by_short_id(context, identity)

        if not action:
            raise exception.ActionNotFound(action=identity)

        return action

    @request_context
    def action_list(self, context, filters=None, limit=None, marker=None,
                    sort=None, project_safe=True):

        limit = utils.parse_int_param('limit', limit)
        all_actions = action_mod.Action.load_all(context, filters=filters,
                                                 limit=limit, marker=marker,
                                                 sort=sort,
                                                 project_safe=project_safe)

        return [a.to_dict() for a in all_actions]

    @request_context
    def action_create(self, context, name, target, action, inputs=None):
        LOG.info(_LI("Creating action '%s'."), name)

        # Create an action instance
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'name': name,
            'inputs': inputs
        }
        act = action_mod.Action(target.id, action, **params)
        act.status = act.READY
        act.store(context)

        # TODO(Anyone): Uncomment this to notify the dispatcher
        # dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Action '%(name)s' is created: %(id)s."),
                 {'name': name, 'id': act.id})
        return act.to_dict()

    @request_context
    def action_get(self, context, identity):
        db_action = self.action_find(context, identity)
        action = action_mod.Action.load(context, db_action=db_action)
        return action.to_dict()

    @request_context
    def action_delete(self, context, identity):
        db_action = self.action_find(context, identity)
        LOG.info(_LI("Deleting action '%s'."), identity)
        try:
            action_mod.Action.delete(context, db_action.id)
        except exception.ResourceBusyError:
            raise exception.ResourceInUse(resource_type='action',
                                          resource_id=db_action.id)

        LOG.info(_LI("Action '%s' is deleted."), identity)

    def receiver_find(self, context, identity, project_safe=True):
        """Find a receiver with the given identity (could be name or ID)."""
        if uuidutils.is_uuid_like(identity):
            receiver = db_api.receiver_get(context, identity,
                                           project_safe=project_safe)
            if not receiver:
                receiver = db_api.receiver_get_by_name(
                    context, identity, project_safe=project_safe)
        else:
            receiver = db_api.receiver_get_by_name(
                context, identity, project_safe=project_safe)
            if not receiver:
                receiver = db_api.receiver_get_by_short_id(
                    context, identity, project_safe=project_safe)

        if not receiver:
            raise exception.ReceiverNotFound(receiver=identity)

        return receiver

    @request_context
    def receiver_list(self, context, limit=None, marker=None, sort=None,
                      filters=None, project_safe=True):
        if limit is not None:
            limit = utils.parse_int_param('limit', limit)
        if project_safe is not None:
            project_safe = utils.parse_bool_param('project_safe', project_safe)

        receivers = receiver_mod.Receiver.load_all(context, limit=limit,
                                                   marker=marker,
                                                   sort=sort, filters=filters,
                                                   project_safe=project_safe)
        return [r.to_dict() for r in receivers]

    @request_context
    def receiver_create(self, context, name, type_name, cluster_id, action,
                        actor=None, params=None):
        """Create a receiver.

        :param context: RPC context.
        :param name: Name of the receiver.
        :param type_name: Name of the receiver type, subject to validation.
        :param cluster_id: Name or ID of a cluster.
        :param action: Name or ID of an action, currently only builtin action
                       names are supported.
        :param actor: Future extension.
        :param params: A dictionary containing key-value pairs as inputs to
                       the action.
        """
        if cfg.CONF.name_unique:
            if db_api.receiver_get_by_name(context, name):
                msg = _("A receiver named '%s' already exists.") % name
                raise exception.SenlinBadRequest(msg=msg)

        LOG.info(_LI("Creating receiver %(n)s: \n"
                     "  type: %(t)s\n  cluster: %(c)s\n  action: %(a)s."),
                 {'n': name, 't': type_name, 'c': cluster_id, 'a': action})

        rtype = type_name.lower()
        if rtype not in consts.RECEIVER_TYPES:
            msg = _("Receiver type '%s' is not supported.") % rtype
            raise exception.SenlinBadRequest(msg=msg)

        # Check whether cluster identified by cluster_id does exist
        cluster = None
        try:
            cluster = self.cluster_find(context, cluster_id)
        except exception.ClusterNotFound:
            msg = _("The referenced cluster '%s' is not found.") % cluster_id
            raise exception.SenlinBadRequest(msg=msg)

        # permission checking
        if not context.is_admin and context.user != cluster.user:
            raise exception.Forbidden()

        # Check action name
        if action not in consts.ACTION_NAMES:
            msg = _("Illegal action '%s' specified.") % action
            raise exception.SenlinBadRequest(msg=msg)

        if action.lower().split('_')[0] != 'cluster':
            msg = _("Action '%s' is not applicable to clusters.") % action
            raise exception.SenlinBadRequest(msg=msg)

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
        LOG.info(_LI("Webhook (%(n)s) is created: %(i)s."),
                 {'n': name, 'i': receiver.id})

        return receiver.to_dict()

    @request_context
    def receiver_get(self, context, identity, project_safe=True):
        db_receiver = self.receiver_find(context, identity,
                                         project_safe=project_safe)
        receiver = receiver_mod.Receiver.load(context,
                                              receiver_obj=db_receiver,
                                              project_safe=project_safe)
        return receiver.to_dict()

    @request_context
    def receiver_delete(self, context, identity):
        db_receiver = self.receiver_find(context, identity)
        LOG.info(_LI("Deleting receiver %s."), identity)
        db_api.receiver_delete(context, db_receiver.id)
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
            raise exception.SenlinBadRequest(msg=msg)

        data = copy.deepcopy(receiver.params)
        if params:
            data.update(params)

        action_name = 'webhook_%s' % receiver.id[:8]
        kwargs = {
            'name': action_name,
            'cause': action_mod.CAUSE_RPC,
            'inputs': data,
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
        }
        action = action_mod.Action(cluster.id, receiver.action, **kwargs)
        action.status = action.READY
        action.store(context)
        dispatcher.start_action(action_id=action.id)

        LOG.info(_LI("Webhook %(w)s' triggered with action queued: %(a)s."),
                 {'w': identity, 'a': action.id})

        return {'action': action.id}

    def event_find(self, context, identity):
        '''Find a event with the given identity (could ID or short ID).'''
        if uuidutils.is_uuid_like(identity):
            event = db_api.event_get(context, identity)
            if not event:
                event = db_api.event_get_by_short_id(context, identity)
        else:
            event = db_api.event_get_by_short_id(context, identity)

        if not event:
            raise exception.EventNotFound(event=identity)

        return event

    @request_context
    def event_list(self, context, filters=None, limit=None, marker=None,
                   sort=None, project_safe=True):
        all_events = event_mod.Event.load_all(context, filters=filters,
                                              limit=limit, marker=marker,
                                              sort=sort,
                                              project_safe=project_safe)

        results = [event.to_dict() for event in all_events]
        return results

    @request_context
    def event_get(self, context, identity):
        db_event = self.event_find(context, identity)
        event = event_mod.Event.load(context, db_event=db_event)
        return event.to_dict()
