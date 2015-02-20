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

import functools
import random
import six

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_utils import uuidutils
from osprofiler import profiler

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
from senlin.engine import node as node_mod
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.openstack.common import service
from senlin.policies import base as policy_base
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)

service_opts = [
    cfg.IntOpt('periodic_interval_max',
               default=60,
               help='Seconds between periodic tasks to be called'),
    cfg.BoolOpt('periodic_enable',
                default=True,
                help='Enable periodic tasks'),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=60,
               help='Range of seconds to randomly delay when starting the'
                    ' periodic task scheduler to reduce stampeding.'
                    ' (Disable by setting to 0)'),
]

CONF = cfg.CONF
CONF.register_opts(service_opts)


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


@profiler.trace_cls("rpc")
class EngineService(service.Service):
    '''Manages the running instances from creation to destruction.

    All the methods in here are called from the RPC backend.  This is
    all done dynamically so if a call is made via RPC that does not
    have a corresponding method here, an exception will be thrown when
    it attempts to call into this class.  Arguments to these methods
    are also dynamically added and will be named as keyword arguments
    by the RPC caller.
    '''

    def __init__(self, host, topic, manager=None,
                 periodic_enable=None, periodic_fuzzy_delay=None,
                 periodic_interval_max=None):

        super(EngineService, self).__init__()
        self.host = host
        self.topic = topic
        self.dispatcher_topic = consts.ENGINE_DISPATCHER_TOPIC

        #params for periodic running task
        if periodic_interval_max is None:
            periodic_interval_max = CONF.periodic_interval_max
        if periodic_enable is None:
            periodic_enable = CONF.periodic_enable
        if periodic_fuzzy_delay is None:
            periodic_fuzzy_delay = CONF.periodic_fuzzy_delay

        self.periodic_interval_max = periodic_interval_max
        self.periodic_enable = periodic_enable
        self.periodic_fuzzy_delay = periodic_fuzzy_delay

        # The following are initialized here, but assigned in start() which
        # happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.TG = None
        self.target = None
        self._rpc_server = None

    def start(self):
        self.engine_id = senlin_lock.BaseLock.generate_engine_id()
        self.TG = scheduler.ThreadGroupManager()

        # TODO(Yanyan): create a dispatcher for this engine thread.
        # This dispatcher will run in a greenthread and it will not
        # stop until being notified or the engine is stopped.
        self.dispatcher = dispatcher.Dispatcher(self,
                                                self.dispatcher_topic,
                                                consts.RPC_API_VERSION,
                                                self.TG)
        LOG.debug("Starting dispatcher for engine %s" % self.engine_id)

        if self.periodic_enable:
            if self.periodic_fuzzy_delay:
                initial_delay = random.randint(0, self.periodic_fuzzy_delay)
            else:
                initial_delay = None

            self.tg.add_dynamic_timer(self.periodic_tasks,
                                      initial_delay=initial_delay,
                                      periodic_interval_max=
                                      self.periodic_interval_max)

        self.dispatcher.start()

        target = oslo_messaging.Target(version=consts.RPC_API_VERSION,
                                       server=self.host,
                                       topic=self.topic)
        self.target = target
        self._rpc_server = rpc_messaging.get_rpc_server(target, self)
        self._rpc_server.start()
        environment.initialize()
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

        # Terminate the engine process
        LOG.info(_LI("All threads were gone, terminating engine"))
        super(EngineService, self).stop()

    def periodic_tasks(self, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        #TODO(anyone): iterate clusters and call their periodic_tasks
        return self.periodic_interval_max

    @request_context
    def get_revision(self, context):
        return cfg.CONF.revision['senlin_engine_revision']

    @request_context
    def profile_type_list(self, context):
        return environment.global_env().get_profile_types()

    @request_context
    def profile_type_spec(self, context, type_name):
        profile = environment.global_env().get_profile(type_name)

        data = dict((name, dict(schema))
                    for name, schema in profile.spec_schema.items())
        return {'schema': data}

    @request_context
    def profile_type_template(self, context, type_name):
        return {}

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
                     sort_dir=None, filters=None, show_deleted=None):
        show_deleted = utils.parse_bool_param('show_deleted', show_deleted)
        limit = utils.parse_int_param('limit', limit)
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
        profile = plugin(type, name, **kwargs)
        profile.validate()
        profile.store(context)
        return profile.to_dict()

    @request_context
    def profile_get(self, context, identity):
        db_profile = self.profile_find(context, identity)
        profile = profile_base.Profile.load(context, profile=db_profile)
        return profile.to_dict()

    @request_context
    def profile_update(self, context, profile_id, name, spec, perm, tags):

        return {}

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
    def policy_type_spec(self, context, type_name):
        policy_type = environment.global_env().get_policy(type_name)

        data = dict((name, dict(schema))
                    for name, schema in policy_type.spec_schema.items())
        return {'schema': data}

    @request_context
    def policy_type_template(self, context, type_name):
        return {}

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
    def policy_update(self, context, identity, name, spec=None, level=None,
                      cooldown=None):
        return {}

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

        size = utils.parse_int_param(consts.SIZE, size)
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
    def cluster_update(self, context, identity, profile_id):
        # Get the database representation of the existing cluster
        db_cluster = self.cluster_find(context, identity)
        db_profile = self.profile_find(context, profile_id)

        LOG.info(_LI('Updating cluster %s'), db_cluster.name)

        cluster = cluster_mod.Cluster.load(context, cluster=db_cluster)
        if cluster.status == cluster.ERROR:
            msg = _('Updating a cluster when it is error')
            raise exception.NotSupported(feature=msg)

        if cluster.status == cluster.DELETED:
            msg = _('Updating a cluster which has been deleted')
            raise exception.NotSupported(feature=msg)

        kwargs = {
            'profile_id': db_profile.id
        }

        action = action_mod.Action(context, 'CLUSTER_UPDATE',
                                   target=cluster.id,
                                   cause=action_mod.CAUSE_RPC,
                                   **kwargs)
        action.store(context)

        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                  None, action_id=action.id)

        return cluster.id

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
        show_deleted = utils.parse_bool_param('show_deleted', show_deleted)
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

        LOG.info(_LI('Creating node %s'), name)

        # Create a node instance
        node = node_mod.Node(name, db_profile.id, cluster_id, role=role,
                             tags=tags)
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
    def node_update(self, context, identity, name, profile_id=None, role=None,
                    tags=None):
        db_node = self.node_find(context, identity)
        if profile_id is not None:
            db_profile = self.profile_find(context, profile_id)
            profile_id = db_profile.id

        LOG.info(_LI('Updating node %s'), identity)

        # Find the node instance
        node = node_mod.Node.load(context, node=db_node)

        action = action_mod.Action(context, 'NODE_UPDATE',
                                   name='node_update_%s' % node.id[:8],
                                   target=node.id,
                                   cause=action_mod.CAUSE_RPC)
        action.store(context)

        # TODO(someone): uncomment this when it is implemented
        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                  None, action_id=action.id)

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

        return action.to_dict()

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

        return action.to_dict()

    @request_context
    def cluster_policy_list(self, context, identity, filters=None,
                            limit=None, marker=None,
                            sort_keys=None, sort_dir=None):
        limit = utils.parse_int_param('limit', limit)
        db_cluster = self.cluster_find(context, identity)
        bindings = db_api.cluster_policy_get_all(context, db_cluster.id,
                                                 filters=filters,
                                                 limit=limit, marker=marker,
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

    def action_find(self, context, identity, show_deleted=False):
        '''Find a cluster with the given identity (could be name or ID).'''
        # TODO(Qiming): add show_deleted support
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
