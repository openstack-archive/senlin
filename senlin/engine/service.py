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

from oslo import messaging
from oslo_config import cfg
from oslo_utils import uuidutils
from osprofiler import profiler

from senlin.common import attr
from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI
from senlin.common import messaging as rpc_messaging
from senlin.db import api as db_api
from senlin.engine.actions import base as base_action
from senlin.engine import cluster as clusters
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import node as nodes
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.openstack.common import log as logging
from senlin.openstack.common import service
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())
        try:
            return func(self, ctx, *args, **kwargs)
        except exception.SenlinException:
            raise messaging.rpc.dispatcher.ExpectedException()
    return wrapped


@profiler.trace_cls("rpc")
class EngineService(service.Service):
    """
    Manages the running instances from creation to destruction.
    All the methods in here are called from the RPC backend.  This is
    all done dynamically so if a call is made via RPC that does not
    have a corresponding method here, an exception will be thrown when
    it attempts to call into this class.  Arguments to these methods
    are also dynamically added and will be named as keyword arguments
    by the RPC caller.
    """

    def __init__(self, host, topic, manager=None):
        super(EngineService, self).__init__()
        # TODO(Qiming): call environment.initialize() when environment
        # is ready
        self.host = host
        self.topic = topic
        self.dispatcher_topic = attr.ENGINE_DISPATCHER_TOPIC

        # The following are initialized here, but assigned in start() which
        # happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.TG = None
        self.target = None

    def start(self):
        self.engine_id = senlin_lock.BaseLock.generate_engine_id()
        self.TG = scheduler.ThreadGroupManager()

        # TODO(Yanyan): create a dispatcher for this engine thread.
        # This dispatcher will run in a greenthread and it will not
        # stop until being notified or the engine is stopped.
        self.dispatcher = dispatcher.Dispatcher(self,
                                                self.dispatcher_topic,
                                                attr.RPC_API_VERSION,
                                                self.TG)
        LOG.debug("Starting dispatcher for engine %s" % self.engine_id)
        self.dispatcher.start()

        target = messaging.Target(version=attr.RPC_API_VERSION,
                                  server=self.host,
                                  topic=self.topic)
        self.target = target
        server = rpc_messaging.get_rpc_server(target, self)
        server.start()

        super(EngineService, self).start()

    def stop(self):
        # Stop rpc connection at first for preventing new requests
        LOG.info(_LI("Attempting to stop engine service..."))
        try:
            self.conn.close()
        except Exception:
            pass

        # Notify dispatcher to stop all action threads it started.
        self.dispatcher.stop()

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
    def profile_type_spec(self, context, type_name):
        return {}

    @request_context
    def profile_type_template(self, context, type_name):
        return {}

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
    def profile_create(self, context, name, type, spec, perm, tags):
        LOG.info(_LI('Creating profile %s:%s'), type, name)
        kwargs = {
            'spec': spec,
            'permission': perm,
            'tags': tags,
        }
        profile = profile_base.Profile(type, name, **kwargs)
        profile.store(context)
        return profile.to_dict()

    @request_context
    def profile_get(self, context, profile_id):
        profile = profile_base.Profile.load(context, profile_id)
        return profile

    @request_context
    def profile_update(self, context, profile_id, name, spec, perm, tags):
        return {}

    @request_context
    def profile_delete(self, context, profile_id):
        LOG.info(_LI('Delete profile: %s'), profile_id)
        profile_base.Profile.delete(context, profile_id)
        return None

    @request_context
    def policy_type_list(self, context):
        return environment.global_env().get_policy_types()

    @request_context
    def policy_type_spec(self, context, type_name):
        return {}

    @request_context
    def policy_type_template(self, context, type_name):
        return {}

    @request_context
    def cluster_list(self, context, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, tenant_safe=True,
                     show_deleted=False, show_nested=False):
        all_clusters = clusters.Cluster.load_all(context, limit, marker,
                                                 sort_keys, sort_dir,
                                                 filters, tenant_safe,
                                                 show_deleted, show_nested)

        return [c.to_dict() for c in all_clusters]

    @request_context
    def cluster_find(self, context, identity):
        '''
        Find a cluster with the given identity (could be name or ID).
        '''
        if uuidutils.is_uuid_like(identity):
            db_cluster = db_api.cluster_get(context, identity,
                                            show_deleted=True)
            # may be the name is in uuid format, so if get by id returns None,
            # we should get the info by name again
            if not db_cluster:
                db_cluster = db_api.cluster_get_by_name(context, identity)
        else:
            db_cluster = db_api.cluster_get_by_name(context, identity)
        if db_cluster:
            cluster = clusters.Cluster.load(context, cluster=db_cluster)
            return dict(cluster.id)
        else:
            raise exception.ClusterNotFound(cluster_name=identity)

    def _get_cluster(self, context, identity, show_deleted=False):
        cluster_id = self.cluster_find(context, identity)

        db_cluster = db_api.cluster_get(context, cluster_id,
                                        show_deleted=show_deleted,
                                        eager_load=True)

        if db_cluster is None:
            raise exception.ClusterNotFound(cluster_name=identity)

        return db_cluster

    @request_context
    def cluster_get(self, context, cluster_id):
        cluster = clusters.Cluster.load(context, cluster_id=cluster_id)
        return cluster.to_dict()

    @request_context
    def cluster_create(self, context, name, size, profile_id, parent=None,
                       tags=None, timeout=0):
        LOG.info(_LI('Creating cluster %s'), name)
        ctx = context.to_dict()
        kwargs = {
            'user': ctx.get('username', ''),
            'project': ctx.get('tenant_id', ''),
            'parent': parent,
            'timeout': timeout,
            'tags': tags
        }

        cluster = clusters.Cluster(name, profile_id, size, **kwargs)
        cluster.store(context)

        # Build an Action for cluster creation
        action = base_action.Action(context, 'CLUSTER_CREATE',
                                    target=cluster.id, cause='RPC Request')
        action.store(context)

        # Notify Dispatchers that a new action has been ready.
        # dispatcher.notify(context,
        #                   self.dispatcher.NEW_ACTION,
        #                   None,
        #                   action_id=action.id)
        cluster.set_status(context, clusters.Cluster.ACTIVE,
                           reason='Action dispatched')
        return action.to_dict()

    @request_context
    def cluster_update(self, context, identity, size, profile_id):
        # Get the database representation of the existing cluster
        db_cluster = self._get_cluster(context, identity)
        LOG.info(_LI('Updating cluster %s'), db_cluster.name)

        cluster = clusters.Cluster.load(context, cluster=db_cluster)
        if cluster.status == cluster.ERROR:
            msg = _('Updating a cluster when it is errored')
            raise exception.NotSupported(feature=msg)

        if cluster.status == cluster.DELETED:
            msg = _('Updating a cluster which has been deleted')
            raise exception.NotSupported(feature=msg)

        kwargs = {
            'profile_id': profile_id
        }

        # TODO(Qiming): Hande size changes here!
        action = base_action.Action(context, 'CLUSTER_UPDATE',
                                    target=cluster.id, cause='RPC Request'
                                    **kwargs)
        action.store(context)

        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                  None, action_id=action.id)

        return cluster.id

    @request_context
    def cluster_delete(self, context, identity):
        db_cluster = self._get_cluster(context, identity)
        LOG.info(_LI('Deleting cluster %s'), db_cluster.name)

        cluster = clusters.Cluster.load(context, cluster=db_cluster)
        action = base_action.Action(context, 'CLUSTER_DELETE',
                                    target=cluster.id, cause='RPC Request')
        action.store(context)
        # res = dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                        None, action_id=action.id)

        return action.to_dict()

    @request_context
    def node_list(self, context, cluster_id=None, show_deleted=False,
                  limit=None, marker=None, sort_keys=None, sort_dir=None,
                  filters=None, tenant_safe=True):

        all_nodes = nodes.Node.load_all(context, cluster_id, show_deleted,
                                        limit, marker, sort_keys, sort_dir,
                                        filters, tenant_safe)

        return [node.to_dict() for node in all_nodes]

    @request_context
    def node_create(self, context, name, cluster_id, profile_id, role, tags):
        LOG.info(_LI('Creating node %s'), name)

        # Create a node instance
        node = nodes.Node(context, name, profile_id, cluster_id=cluster_id,
                          role=role, tags=tags)
        node.store(context)

        action = base_action.Action(context, 'NODE_CREATE',
                                    target=node.id, cause='RPC Request')
        action.store(context)

        # TODO(Anyone): Uncomment this to notify the dispatcher
        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                   None, action_id=action.id)

        return action.to_dict()

    @request_context
    def node_get(self, context, node_id):
        # TODO(Qiming): Add conversion from name to id
        node = nodes.Node.load(context, node_id)
        return node

    @request_context
    def node_update(self, context, identity, name, profile_id, role, tags):
        return {}

    @request_context
    def node_delete(self, context, node_id, force=False):
        LOG.info(_LI('Deleting node %s'), node_id)

        node = nodes.Node.load(context, node_id)
        action = base_action.Action(context, 'NODE_DELETE',
                                    target=node.id, cause='RPC Request')
        action.store(context)
        # TODO(Anyone): Uncomment the following lines to send notifications
        # res = dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                        None, action_id=action.id)

        # TODO(anyone): Fix this behavior, node record cannot be deleted
        #               directly.
        nodes.Node.delete(context, node_id, force)
        return action.to_dict()

    @request_context
    def action_list(self, context, filters=None, limit=None, marker=None,
                    sort_keys=None, sort_dir=None, show_deleted=False):

        all_actions = base_action.Action.load_all(context, filters,
                                                  limit, marker,
                                                  sort_keys, sort_dir,
                                                  show_deleted)

        raw = [action.to_dict() for action in all_actions]
        for a in raw:
            del a['context']
            yield a

    @request_context
    def action_create(self, context, name, target, action, params):
        LOG.info(_LI('Creating action %s'), name)

        # Create a node instance
        act = base_action.Action(context, action, target,
                                 name=name, params=params)
        act.store(context)

        # TODO(Anyone): Uncomment this to notify the dispatcher
        # dispatcher.notify(context, self.dispatcher.NEW_ACTION,
        #                   None, action_id=action.id)

        return act.to_dict()

    @request_context
    def action_get(self, context, action_id):
        # TODO(Qiming): Add conversion from name to id
        return base_action.Action.load(context, action_id)
