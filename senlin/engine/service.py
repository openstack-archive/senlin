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
from oslo_utils import uuidutils
import six

from senlin.common import consts
from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
from senlin.common import messaging as rpc_messaging
from senlin.common import utils
from senlin.db import api as db_api
from senlin.engine.actions import base as action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import event as event_mod
from senlin.engine import health_manager
from senlin.engine import node as node_mod
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.openstack.common import service
from senlin.policies import base as policy_base
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())
        try:
            return func(self, ctx, *args, **kwargs)
        except exception.SenlinException:
            raise oslo_messaging.rpc.dispatcher.ExpectedException()
    return wrapped


class EngineService(service.Service):
    '''Lifecycle manager for a running service engine.

    - All the methods in here are called from the RPC client.
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

        # The following are initialized here, but assigned in start() which
        # happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.TG = None
        self.target = None
        self._rpc_server = None

        # Intialize the global environment
        environment.initialize()

    def init_tgm(self):
        self.TG = scheduler.ThreadGroupManager()

    def start(self):
        self.engine_id = senlin_lock.BaseLock.generate_engine_id()
        self.init_tgm()

        # create a dispatcher greenthread for this engine.
        self.dispatcher = dispatcher.Dispatcher(self,
                                                self.dispatcher_topic,
                                                consts.RPC_API_VERSION,
                                                self.TG)
        LOG.debug("Starting dispatcher for engine %s" % self.engine_id)

        self.dispatcher.start()

        # create a health manager greenthread for this engine.
        self.health_mgr = health_manager.Health_Manager(self,
                                                        self.health_mgr_topic,
                                                        consts.RPC_API_VERSION,
                                                        self.TG)
        LOG.debug("Starting health manager for engine %s" % self.engine_id)

        self.health_mgr.start()

        target = oslo_messaging.Target(version=consts.RPC_API_VERSION,
                                       server=self.host,
                                       topic=self.topic)
        self.target = target
        self._rpc_server = rpc_messaging.get_rpc_server(target, self)
        self._rpc_server.start()
        super(EngineService, self).start()

    def _stop_rpc_server(self):
        # Stop RPC connection to prevent new requests
        LOG.debug(_("Attempting to stop engine service..."))
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
        self.dispatcher.stop()

        # Notify health_manager to stop
        self.health_mgr.stop()

        # Terminate the engine process
        LOG.info(_LI("All threads were gone, terminating engine"))
        super(EngineService, self).stop()

    @request_context
    def get_revision(self, context):
        return cfg.CONF.revision['senlin_engine_revision']

    @request_context
    def profile_type_list(self, context):
        return environment.global_env().get_profile_types()

    @request_context
    def profile_type_schema(self, context, type_name):
        profile = environment.global_env().get_profile(type_name)

        data = dict((name, dict(schema))
                    for name, schema in profile.spec_schema.items())
        return {'spec': data}

    @request_context
    def profile_find(self, context, identity, show_deleted=False):
        '''Find a profile with the given identity (could be name or ID).'''
        if uuidutils.is_uuid_like(identity):
            profile = db_api.profile_get(context, identity,
                                         show_deleted=show_deleted)
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
    def profile_list(self, context, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, show_deleted=False):
        profiles = profile_base.Profile.load_all(context, limit=limit,
                                                 marker=marker,
                                                 sort_keys=sort_keys,
                                                 sort_dir=sort_dir,
                                                 filters=filters,
                                                 show_deleted=show_deleted)

        return [p.to_dict() for p in profiles]

    @request_context
    def profile_create(self, context, name, type, spec, perm=None, tags=None):
        LOG.info(_LI('Creating profile %s: %s'), type, name)
        plugin = environment.global_env().get_profile(type)

        kwargs = {
            'spec': spec,
            'permission': perm,
            'tags': tags,
        }
        profile = plugin(context, type, name, **kwargs)
        profile.validate()
        profile.store(context)
        return profile.to_dict()

    @request_context
    def profile_get(self, context, identity):
        db_profile = self.profile_find(context, identity)
        profile = profile_base.Profile.load(context, profile=db_profile)
        return profile.to_dict()

    @request_context
    def profile_update(self, context, profile_id, name=None, spec=None,
                       permission=None, tags=None):
        db_profile = self.profile_find(context, profile_id)
        if spec is None:
            profile = profile_base.Profile.load(context, profile=db_profile)
            changed = False
            if name is not None and name != profile.name:
                profile.name = name
                changed = True
            if permission is not None and permission != profile.permission:
                profile.permission = permission
                changed = True
            if tags is not None and tags != profile.tags:
                profile.tags = tags
                changed = True
            if changed:
                profile.store(context)
            return profile.to_dict()

        plugin = environment.global_env().get_profile(db_profile.type)

        new_spec = copy.deepcopy(db_profile.spec)
        new_spec.update(spec)
        kwargs = {
            'spec': new_spec,
            'permission': permission or db_profile.permission,
            'tags': tags or db_profile.tags,
        }

        new_name = name or db_profile.name
        profile = plugin(context, db_profile.type, new_name, **kwargs)
        profile.validate()
        profile.store(context)
        return profile.to_dict()

    @request_context
    def profile_delete(self, context, identity):
        db_profile = self.profile_find(context, identity)
        LOG.info(_LI('Deleting profile: %s'), identity)
        profile_base.Profile.delete(context, db_profile.id)
        return None

    @request_context
    def policy_type_list(self, context):
        return environment.global_env().get_policy_types()

    @request_context
    def policy_type_schema(self, context, type_name):
        policy_type = environment.global_env().get_policy(type_name)

        data = dict((name, dict(schema))
                    for name, schema in policy_type.spec_schema.items())
        return {'spec': data}

    @request_context
    def policy_find(self, context, identity, show_deleted=False):
        '''Find a policy with the given identity (could be name or ID).'''

        if uuidutils.is_uuid_like(identity):
            policy = db_api.policy_get(context, identity,
                                       show_deleted=show_deleted)
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
    def policy_list(self, context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, show_deleted=None):
        limit = utils.parse_int_param('limit', limit)
        show_deleted = utils.parse_bool_param('show_deleted', show_deleted)
        policies = policy_base.Policy.load_all(context, limit=limit,
                                               marker=marker,
                                               sort_keys=sort_keys,
                                               sort_dir=sort_dir,
                                               filters=filters,
                                               show_deleted=show_deleted)

        return [p.to_dict() for p in policies]

    @request_context
    def policy_create(self, context, name, type, spec, level=None,
                      cooldown=None):
        level = utils.parse_int_param('level', level)
        cooldown = utils.parse_int_param('cooldown', cooldown)
        plugin = environment.global_env().get_policy(type)

        LOG.info(_LI('Creating policy %s:%s'), type, name)

        kwargs = {
            'spec': spec,
            'level': level,
            'cooldown': cooldown,
        }
        policy = plugin(type, name, **kwargs)
        policy.validate()
        policy.store(context)
        return policy.to_dict()

    @request_context
    def policy_get(self, context, identity):
        db_policy = self.policy_find(context, identity)
        policy = policy_base.Policy.load(context, policy=db_policy)
        return policy.to_dict()

    @request_context
    def policy_update(self, context, identity, name=None, level=None,
                      cooldown=None):

        db_policy = self.policy_find(context, identity)
        policy = policy_base.Policy.load(context, policy=db_policy)
        changed = False

        if name is not None and name != policy.name:
            policy.name = name
            changed = True
        if level is not None and level != policy.level:
            policy.level = level
            changed = True
        if cooldown is not None and cooldown != policy.cooldown:
            policy.cooldown = cooldown
            changed = True

        if changed:
            policy.store(context)

        return policy.to_dict()

    @request_context
    def policy_delete(self, context, identity):
        db_policy = self.policy_find(context, identity)
        LOG.info(_LI('Delete policy: %s'), identity)
        policy_base.Policy.delete(context, db_policy.id)
        return None

    @request_context
    def cluster_list(self, context, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, tenant_safe=True,
                     show_deleted=False, show_nested=False):
        limit = utils.parse_int_param('limit', limit)
        tenant_safe = utils.parse_bool_param('tenant_safe', tenant_safe)
        show_deleted = utils.parse_bool_param('show_deleted', show_deleted)
        show_nested = utils.parse_bool_param('show_nested', show_nested)
        clusters = cluster_mod.Cluster.load_all(context, limit=limit,
                                                marker=marker,
                                                sort_keys=sort_keys,
                                                sort_dir=sort_dir,
                                                filters=filters,
                                                tenant_safe=tenant_safe,
                                                show_deleted=show_deleted,
                                                show_nested=show_nested)

        return [cluster.to_dict() for cluster in clusters]

    def cluster_find(self, context, identity, show_deleted=False):
        '''Find a cluster with the given identity (could be name or ID).'''

        if uuidutils.is_uuid_like(identity):
            cluster = db_api.cluster_get(context, identity,
                                         show_deleted=show_deleted)
            # maybe the name is in uuid format, so if get by id returns None,
            # we should get the info by name again
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

    @request_context
    def cluster_create(self, context, name, size, profile_id, parent=None,
                       tags=None, timeout=None):
        db_profile = self.profile_find(context, profile_id)

        size = utils.parse_int_param(consts.CLUSTER_SIZE, size)
        timeout = utils.parse_int_param(consts.CLUSTER_TIMEOUT, timeout)

        LOG.info(_LI('Creating cluster %s'), name)
        ctx = context.to_dict()
        kwargs = {
            'user': ctx.get('username', ''),
            'project': ctx.get('tenant_id', ''),
            'parent': parent,
            'timeout': timeout,
            'tags': tags
        }

        cluster = cluster_mod.Cluster(name, db_profile.id, size, **kwargs)
        cluster.store(context)

        # Build an Action for cluster creation
        action = action_mod.Action(context, 'CLUSTER_CREATE',
                                   name='cluster_create_%s' % cluster.id[:8],
                                   target=cluster.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)

        # Notify Dispatchers that a new action has been ready.
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        # We return a cluster dictionary with an additional key carried
        result = cluster.to_dict()
        result['action'] = action.id
        return result

    @request_context
    def cluster_update(self, context, identity, name=None, profile_id=None,
                       parent=None, tags=None, timeout=None):
        def update_cluster_properties(cluster):
            changed = False
            # Check out if fields other than profile_id have to be changed
            if name is not None and name != cluster.name:
                cluster.name = name
                changed = True

            if parent is not None:
                db_parent = self.cluster_find(context, parent)
                if cluster.parent != db_parent.id:
                    cluster.parent = db_parent.id
                    changed = True

            if tags is not None and tags != cluster.tags:
                cluster.tags = tags
                changed = True

            if timeout is not None and timeout != cluster.timeout:
                cluster.timeout = timeout
                changed = True

            if changed is True:
                cluster.store(context)

            return

        # Get the database representation of the existing cluster
        db_cluster = self.cluster_find(context, identity)
        cluster = cluster_mod.Cluster.load(context, cluster=db_cluster)

        if cluster.status == cluster.DELETED:
            msg = _('Updating a cluster which has been deleted')
            raise exception.NotSupported(feature=msg)

        update_cluster_properties(cluster)

        if profile_id is None or profile_id == cluster.profile_id:
            return

        if cluster.status == cluster.ERROR:
            msg = _('Updating a cluster when it is in error state')
            raise exception.NotSupported(feature=msg)

        new_profile = self.profile_find(context, profile_id)
        old_profile = self.profile_find(context, cluster.profile_id)
        if new_profile.type != old_profile.type:
            msg = _('Cannot update a cluster to a different profile type, '
                    'operation aborted.')
            raise exception.ProfileTypeNotMatch(message=msg)

        LOG.info(_LI("Updating cluster '%(cluster)s' to profile "
                     "'%(profile)s'.") % {'cluster': identity,
                                          'profile': profile_id})

        action = action_mod.Action(context, 'CLUSTER_UPDATE',
                                   target=cluster.id,
                                   cause=action_mod.CAUSE_RPC,
                                   inputs={'profile_id': new_profile.id})
        action.store(context)

        # TODO(anyone): Uncomment the following line when update action
        # is implemented.
        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                   None, action_id=action.id)

        return

    @request_context
    def cluster_add_nodes(self, context, identity, nodes):
        db_cluster = self.cluster_find(context, identity)
        found = []
        not_found = []
        bad_nodes = []
        owned_nodes = []
        for node in nodes:
            try:
                db_node = self.node_find(context, node)
                # Skip node in the same cluster already
                if db_node.status != node_mod.Node.ACTIVE:
                    bad_nodes.append(db_node.id)
                elif db_node.cluster_id is not None:
                    owned_nodes.append(node)
                else:
                    found.append(db_node.id)
            except exception.NodeNotFound:
                not_found.append(node)
                pass

        error = None
        if len(bad_nodes) > 0:
            error = _("Nodes are not ACTIVE: %s") % bad_nodes
        elif len(owned_nodes) > 0:
            error = _("Nodes %s owned by other cluster, need to delete "
                      "them from those clusters first.") % owned_nodes
        elif len(not_found) > 0:
            error = _("Nodes not found: %s") % not_found
        elif len(found) == 0:
            error = _("No nodes to add: %s") % nodes

        if error is not None:
            raise exception.SenlinBadRequest(msg=error)

        action_name = 'cluster_add_nodes_%s' % db_cluster.id[:8]
        action = action_mod.Action(context, 'CLUSTER_ADD_NODES',
                                   name=action_name,
                                   target=db_cluster.id,
                                   cause=action_mod.CAUSE_RPC,
                                   inputs={'nodes': found})
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_del_nodes(self, context, identity, nodes):
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
        if len(not_found) > 0:
            error = _("Nodes %s not found") % nodes
        elif len(bad_nodes) > 0:
            error = _("Nodes %s not member of specified cluster") % bad_nodes
        elif len(found) == 0:
            error = _("No nodes specified") % nodes

        if error is not None:
            raise exception.SenlinBadRequest(msg=error)

        action_name = 'cluster_del_nodes_%s' % db_cluster.id[:8]
        action = action_mod.Action(context, 'CLUSTER_DEL_NODES',
                                   name=action_name,
                                   target=db_cluster.id,
                                   cause=action_mod.CAUSE_RPC,
                                   inputs={'nodes': found})
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_scale_out(self, context, identity, count=None):
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
        action = action_mod.Action(context, 'CLUSTER_SCALE_OUT',
                                   name=action_name,
                                   target=db_cluster.id,
                                   inputs=inputs,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_scale_in(self, context, identity, count=None):
        db_cluster = self.cluster_find(context, identity)
        delta = utils.parse_int_param('count', count, allow_zero=False)

        if delta is not None:
            LOG.info(_LI('Scaling in cluster %(name)s by %(delta)s nodes'),
                     {'name': identity, 'delta': delta})
            inputs = {'count': delta}
        else:
            LOG.info(_LI('Scaling in cluster %s'), db_cluster.name)
            inputs = {}

        action_name = 'cluster_scale_in_%s' % db_cluster.id[:8]
        action = action_mod.Action(context, 'CLUSTER_SCALE_IN',
                                   name=action_name,
                                   target=db_cluster.id,
                                   inputs=inputs,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_delete(self, context, identity):
        cluster = self.cluster_find(context, identity)
        LOG.info(_LI('Deleting cluster %s'), cluster.name)

        action = action_mod.Action(context, 'CLUSTER_DELETE',
                                   name='cluster_delete_%s' % cluster.id[:8],
                                   target=cluster.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    def node_find(self, context, identity, show_deleted=False):
        '''Find a cluster with the given identity (could be name or ID).'''

        if uuidutils.is_uuid_like(identity):
            node = db_api.node_get(context, identity,
                                   show_deleted=show_deleted)
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
    def node_list(self, context, cluster_id=None, show_deleted=False,
                  limit=None, marker=None, sort_keys=None, sort_dir=None,
                  filters=None, tenant_safe=True):
        # Maybe the cluster_id is a name or a short ID
        if cluster_id is not None:
            db_cluster = self.cluster_find(context, cluster_id)
            cluster_id = db_cluster.id
        nodes = node_mod.Node.load_all(context, cluster_id=cluster_id,
                                       show_deleted=show_deleted,
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       tenant_safe=tenant_safe)

        return [node.to_dict() for node in nodes]

    @request_context
    def node_create(self, context, name, profile_id, cluster_id=None,
                    role=None, tags=None):
        db_profile = self.profile_find(context, profile_id)
        if cluster_id is not None:
            db_cluster = self.cluster_find(context, cluster_id)
            cluster_id = db_cluster.id

            if context.project_id != db_cluster.project:
                msg = _('Node and cluster are from different project, '
                        'operation is disallowed.')
                raise exception.ProjectNotMatch(message=msg)

            if profile_id != db_cluster.profile_id:
                node_profile = self.profile_find(context, profile_id)
                cluster_profile = self.profile_find(context,
                                                    db_cluster.profile_id)
                if node_profile.type != cluster_profile.type:
                    msg = _('Node and cluster have different profile type, '
                            'operation aborted.')
                    raise exception.ProfileTypeNotMatch(message=msg)

        LOG.info(_LI('Creating node %s'), name)

        # Create a node instance
        tags = tags or {}
        node = node_mod.Node(name, db_profile.id, cluster_id, context,
                             role=role, tags=tags)
        node.store(context)

        action = action_mod.Action(context, 'NODE_CREATE',
                                   name='node_create_%s' % node.id[:8],
                                   target=node.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)

        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        # We return a node dictionary with an additional key (action) carried
        result = node.to_dict()
        result['action'] = action.id
        return result

    @request_context
    def node_get(self, context, identity):
        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, node=db_node)
        return node.to_dict()

    @request_context
    def node_update(self, context, identity, name=None, profile_id=None,
                    role=None, tags=None):
        db_node = self.node_find(context, identity)
        node = node_mod.Node.load(context, node=db_node)

        changed = False
        if name is not None and name != node.name:
            node.name = name
            changed = True

        if role is not None and role != node.role:
            node.role = role
            changed = True

        if tags is not None and tags != node.tags:
            node.tags = tags
            changed = True

        if changed is True:
            node.store(context)

        if profile_id is None:
            return

        # The profile_id could be a name or a short ID, check it
        db_profile = self.profile_find(context, profile_id)
        profile_id = db_profile.id

        # check if profile_type matches
        node_profile = self.profile_find(context, node.profile_id)
        if node_profile.type != db_profile.type:
            msg = _('Cannot update a cluster to a different profile type, '
                    'operation aborted.')
            raise exception.ProfileTypeNotMatch(message=msg)

        LOG.info(_LI('Updating node %s'), identity)

        action = action_mod.Action(context, 'NODE_UPDATE',
                                   name='node_update_%s' % node.id[:8],
                                   target=node.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)

        # TODO(someone): uncomment this when it is implemented
        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                  None, action_id=action.id)
        return

    @request_context
    def node_delete(self, context, identity, force=False):
        db_node = self.node_find(context, identity)
        LOG.info(_LI('Deleting node %s'), identity)

        node = node_mod.Node.load(context, node=db_node)
        action = action_mod.Action(context, 'NODE_DELETE',
                                   name='node_delete_%s' % node.id[:8],
                                   target=node.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return action.to_dict()

    @request_context
    def node_join(self, context, identity, cluster_id):
        db_node = self.node_find(context, identity)
        db_cluster = self.cluster_find(context, cluster_id)

        if db_node.project != db_cluster.project:
            msg = _('Node and cluster are from different project, operation '
                    'is not allowed.')
            raise exception.ProjectNotMatch(message=msg)

        if db_node.profile_id != db_cluster.profile_id:
            node_profile = self.profile_find(db_node.profile_id)
            cluster_profile = self.profile_find(db_cluster.profile_id)
            if node_profile.type != cluster_profile.type:
                msg = _('Node and cluster have different profile type, '
                        'operation aborted.')
                raise exception.ProfileTypeNotMatch(message=msg)

        LOG.info(_LI('Joining node %(node)s to cluster %(cluster)s'),
                 {'node': identity, 'cluster': cluster_id})

        action = action_mod.Action(context, 'NODE_JOIN',
                                   name='node_join_%s' % db_node.id[:8],
                                   target=db_node.id,
                                   cause=action_mod.CAUSE_RPC,
                                   inputs={'cluster_id': db_cluster.id})
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def node_leave(self, context, identity):
        db_node = self.node_find(context, identity)
        LOG.info(_LI('Node %(node)s leaving cluster'), {'node': identity})

        action = action_mod.Action(context, 'NODE_LEAVE',
                                   name='node_leave_%s' % db_node.id[:8],
                                   target=db_node.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_policy_list(self, context, identity, filters=None,
                            sort_keys=None, sort_dir=None):
        db_cluster = self.cluster_find(context, identity)
        bindings = db_api.cluster_policy_get_all(context, db_cluster.id,
                                                 filters=filters,
                                                 sort_keys=sort_keys,
                                                 sort_dir=sort_dir)
        result = []
        for binding in bindings:
            result.append({
                'id': binding.id,
                'cluster_id': binding.cluster_id,
                'cluster_name': binding.cluster.name,
                'policy_id': binding.policy_id,
                'policy_name': binding.policy.name,
                'policy_type': binding.policy.type,
                'priority': binding.priority,
                'level': binding.level,
                'cooldown': binding.cooldown,
                'enabled': binding.enabled,
            })
        return result

    @request_context
    def cluster_policy_get(self, context, identity, policy_id):
        db_cluster = self.cluster_find(context, identity)
        db_policy = self.policy_find(context, policy_id)
        binding = db_api.cluster_policy_get(context, db_cluster.id,
                                            db_policy.id)
        return {
            'id': binding.id,
            'cluster_id': binding.cluster_id,
            'cluster_name': binding.cluster.name,
            'policy_id': binding.policy_id,
            'policy_name': binding.policy.name,
            'policy_type': binding.policy.type,
            'priority': binding.priority,
            'level': binding.level,
            'cooldown': binding.cooldown,
            'enabled': binding.enabled,
        }

    @request_context
    def cluster_policy_attach(self, context, identity, policy, priority=None,
                              level=None, cooldown=None, enabled=True):
        db_cluster = self.cluster_find(context, identity)
        db_policy = self.policy_find(context, policy)
        priority = utils.parse_int_param('priority', priority) or 50
        level = utils.parse_int_param('level', level) or 50
        cooldown = utils.parse_int_param('cooldown', cooldown) or 0
        enabled = utils.parse_bool_param('cooldown', enabled)

        LOG.info(_LI('Attaching policy %(policy)s to cluster %(cluster)s'),
                 {'policy': policy, 'cluster': identity})

        inputs = {
            'policy_id': db_policy.id,
            'priority': priority,
            'level': level,
            'cooldown': cooldown,
            'enabled': enabled,
        }
        action_name = 'cluster_attach_policy_%s' % db_cluster.id[:8]
        action = action_mod.Action(context, consts.CLUSTER_ATTACH_POLICY,
                                   name=action_name,
                                   target=db_cluster.id,
                                   inputs=inputs,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_policy_detach(self, context, identity, policy):
        db_cluster = self.cluster_find(context, identity)
        db_policy = self.policy_find(context, policy)

        LOG.info(_LI('Detaching policy %(policy)s from cluster %(cluster)s'),
                 {'policy': policy, 'cluster': identity})

        action_name = 'cluster_detach_policy_%s' % db_cluster.id[:8]
        action = action_mod.Action(context, consts.CLUSTER_DETACH_POLICY,
                                   name=action_name,
                                   target=db_cluster.id,
                                   inputs={'policy_id': db_policy.id},
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

        return {'action': action.id}

    @request_context
    def cluster_policy_update(self, context, identity, policy, priority=None,
                              level=None, cooldown=None, enabled=None):
        db_cluster = self.cluster_find(context, identity)
        db_policy = self.policy_find(context, policy)

        inputs = {'policy_id': db_policy.id}
        if priority is not None:
            inputs['priority'] = utils.parse_int_param('priority', priority)
        if level is not None:
            inputs['level'] = utils.parse_int_param('level', level)
        if cooldown is not None:
            inputs['cooldown'] = utils.parse_int_param('cooldown', cooldown)
        if enabled is not None:
            inputs['enabled'] = utils.parse_bool_param('cooldown', enabled)

        LOG.info(_LI('Updating policy %(policy)s on cluster %(cluster)s'),
                 {'policy': policy, 'cluster': identity})

        action_name = 'cluster_update_policy_%s' % db_cluster.id[:8]
        action = action_mod.Action(context, consts.CLUSTER_UPDATE_POLICY,
                                   name=action_name,
                                   target=db_cluster.id,
                                   inputs=inputs,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)
        dispatcher.notify(context, self.dispatcher.NEW_ACTION,
                          None, action_id=action.id)

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
                    sort_keys=None, sort_dir=None, show_deleted=False):

        limit = utils.parse_int_param('limit', limit)
        show_deleted = utils.parse_bool_param('show_deleted', show_deleted)
        all_actions = action_mod.Action.load_all(context, filters=filters,
                                                 limit=limit, marker=marker,
                                                 sort_keys=sort_keys,
                                                 sort_dir=sort_dir,
                                                 show_deleted=show_deleted)

        results = []
        for action in all_actions:
            raw = action.to_dict()
            del raw['context']
            results.append(raw)

        return results

    @request_context
    def action_create(self, context, name, target, action, params):
        LOG.info(_LI('Creating action %s'), name)

        # Create a node instance
        act = action_mod.Action(context, action, target,
                                name=name, params=params)
        act.store(context)

        # TODO(Anyone): Uncomment this to notify the dispatcher
        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                   None, action_id=action.id)

        return act.to_dict()

    @request_context
    def action_get(self, context, identity):
        db_action = self.action_find(context, identity)
        action = action_mod.Action.load(context, action=db_action)
        return action.to_dict()

    def event_find(self, context, identity, show_deleted=False):
        '''Find a event with the given identity (could be name or ID).'''
        if uuidutils.is_uuid_like(identity):
            event = db_api.event_get(context, identity)
            if not event:
                event = db_api.event_get_by_short_id(context, identity)
        else:
            event = db_api.event_get_by_short_id(context, identity)

        if not event:
            raise exception.EventNotFound(action=identity)

        return event

    @request_context
    def event_list(self, context, filters=None, limit=None, marker=None,
                   sort_keys=None, sort_dir=None, tenant_safe=True,
                   show_deleted=False):
        all_actions = event_mod.Event.load_all(context, filters=filters,
                                               limit=limit, marker=marker,
                                               sort_keys=sort_keys,
                                               sort_dir=sort_dir,
                                               tenant_safe=tenant_safe,
                                               show_deleted=show_deleted)

        results = [action.to_dict() for action in all_actions]
        return results

    @request_context
    def event_get(self, context, identity):
        db_event = self.event_find(context, identity)
        event = event_mod.Event.load(context, db_event=db_event)
        return event.to_dict()
