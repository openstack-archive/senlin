#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools

import eventlet
from oslo.config import cfg
from oslo import messaging
from oslo.utils import uuidutils
from osprofiler import profiler

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI
from senlin.common import messaging as rpc_messaging
from senlin.db import api as db_api
from senlin.engine import action as actions
from senlin.engine import cluster as clusters
from senlin.engine import senlin_lock
from senlin.engine import scheduler
from senlin.openstack.common import log as logging
from senlin.openstack.common import service

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
class Dispatcher(service.Service):
    '''
    Listen on an AMQP queue named for the engine.  Receive
    notification from engine services and schedule actions.
    '''

    OPERATIONS = (NEW_ACTION, CANCEL_ACTION, SEND, STOP) = (
        'new_action', 'cancel_action', 'send', 'stop')

    def __init__(self, host, engine_id, thread_group_mgr):
        super(Dispatcher, self).__init__()
        self.TG = thread_group_mgr
        self.engine_id = engine_id
        self.host = host

    def start(self):
        super(Dispatcher, self).start()
        self.target = messaging.Target(
            server=self.host, topic=self.engine_id)
        server = rpc_messaging.get_rpc_server(self.target, self)
        server.start()

    def listening(self, ctxt):
        '''
        Respond affirmatively to confirm that the engine performing the
        action is still alive.
        '''
        return True

    def new_action(self, ctxt, action_id=None):
        '''New action has been ready, try to schedule it'''
        self.TG.start_action(ctxt, action_id, self.engine_id)

    def cancel_action(self, ctxt, action_id):
        '''Cancel an action.'''
        self.TG.cancel_action(ctxt, action_id)

    def suspend_action(self, ctxt, action_id):
        '''Suspend an action.'''
        raise NotImplementedError

    def resume_action(self, ctxt, action_id):
        '''Resume an action.'''
        raise NotImplementedError

    def stop(self):
        super(Dispatcher, self).stop()
        # Wait for all action threads to be finished
        LOG.info(_LI("Stopping all action threads of engine %s"), 
                 self.engine_id)
        # Stop ThreadGroup gracefully
        self.TG.stop(True)
        LOG.info(_LI("All action threads have been finished"))

    def send(self, ctxt, action_id, message):
        self.TG.send(action_id, message)


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

    RPC_API_VERSION = '1.0'

    def __init__(self, host, topic, manager=None):
        super(EngineService, self).__init__()
        # TODO(Qiming): call environment.initialize() when environment
        # is ready
        self.host = host
        self.topic = topic

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
        self.dispatcher = Dispatcher(self.host, self.engine_id, self.TG)
        LOG.debug("Starting dispatcher for engine %s" % self.engine_id)
        self.dispatcher.start()

        target = messaging.Target(
            version=self.RPC_API_VERSION, server=self.host,
            topic=self.topic)
        self.target = target
        server = rpc_messaging.get_rpc_server(target, self)
        server.start()

        self._client = rpc_messaging.get_rpc_client(
            version=self.RPC_API_VERSION)

        super(EngineService, self).start()

    def stop(self):
        # Stop rpc connection at first for preventing new requests
        LOG.info(_LI("Attempting to stop engine service..."))
        try:
            self.conn.close()
        except Exception:
            pass

        # Notify dispatcher to stop all action threads it started.
        res = self._notify_dispatcher(context, 
                                      self.engine_id, 
                                      self.dispatcher.STOP)

        # Terminate the engine process
        LOG.info(_LI("All threads were gone, terminating engine"))
        super(EngineService, self).stop()

    @request_context
    def identify_cluster(self, context, cluster_name):
        """
        The identify_cluster method returns the cluster id for a
        single, live cluster given the cluster name.

        :param context: RPC context.
        :param cluster_name: Name or ID of the cluster to look up.
        """
        if uuidutils.is_uuid_like(cluster_name):
            db_cluster = db_api.cluster_get(context, cluster_name,
                                            show_deleted=True)
            # may be the name is in uuid format, so if get by id returns None,
            # we should get the info by name again
            if not db_cluster:
                db_cluster = db_api.cluster_get_by_name(context, cluster_name)
        else:
            db_cluster = db_api.cluster_get_by_name(context, cluster_name)
        if db_cluster:
            cluster = clusters.Cluster.load(context, cluster=db_cluster)
            return dict(cluster.id)
        else:
            raise exception.ClusterNotFound(cluster_name=cluster_name)

    def _get_cluster(self, context, cluster_identity, show_deleted=False):
        """
        Get Cluster record in DB based on cluster id
        """
        # Currently, cluster_identity is cluster id OR cluster name
        # TODO(Yanyan): use full cluster identity as input, e.g.
        #       *cluster_name/cluster_id*
        cluster_id = self.identify_cluster(context, cluster_identity)

        db_cluster = db_api.cluster_get(context, cluster_id,
                                        show_deleted=show_deleted,
                                        eager_load=True)

        if db_cluster is None:
            raise exception.ClusterNotFound(cluster_name=cluster_identity)

        return db_cluster

    @request_context
    def show_cluster(self, context, cluster_identity):
        """
        Return detailed information about one or all clusters.

        :param context: RPC context.
        :param cluster_identity: Name of the cluster you want to show, or None
            to show all
        """
        if cluster_identity is not None:
            db_cluster = self._get_cluster(context, cluster_identity,
                                           show_deleted=True)
            cluster_list = clusters.Cluster.load(context, cluster=db_cluster)
        else:
            cluster_list = clusters.Cluster.load_all(context,
                                                     show_deleted=True)

        # Format clusters info
        clusters_info = []
        for cluster in cluster_list:
            clusters_info.append(cluster.to_dict())

        return {'clusters': clusters_info}

    @request_context
    def list_clusters(self, context, limit=None, marker=None, sort_keys=None,
                      sort_dir=None, filters=None, tenant_safe=True,
                      show_deleted=False, show_nested=False):
        """
        The list_clusters method returns attributes of all clusters.

        :param context: RPC context
        :param limit: the number of clusters to list (integer or string)
        :param marker: the ID of the last item in the previous page
        :param sort_keys: an array of fields used to sort the list
        :param sort_dir: the direction of the sort ('asc' or 'desc')
        :param filters: a dict with attribute:value to filter the list
        :param tenant_safe: if true, scope the request by the current tenant
        :param show_deleted: if true, show soft-deleted clusters
        :param show_nested: if true, show nested clusters
        :returns: a list of formatted clusters
        """
        cluster_list = clusters.Cluster.load_all(context, limit, marker,
                                                 sort_keys, sort_dir,
                                                 filters, tenant_safe,
                                                 show_deleted, show_nested)

        # Format clusters info
        clusters_info = []
        for cluster in cluster_list:
            clusters_info.append(cluster.to_dict())

        return {'clusters': clusters_info}

    @request_context
    def create_cluster(self, context, name, profile_id, size, args):
        '''
        Handle request to perform a create action on a cluster

        :param cntxt: RPC context.
        :param name: Name of the cluster to created.
        :param profile_id: Profile used to create cluster nodes.
        :param size: Desired size of cluster to be created.
        :param args: A dictionary of other parameters
        '''
        LOG.info(_LI('Creating cluster %s'), name)

        kwargs = {
            'parent': args.get('parent', ''),
            'user': context.get('username', ''),
            'project': context.get('tenant_id', ''),
            'timeout': args.get('timeout', 0),
            'tags': args.get('tags', {}),
        }

        # Create a Cluster instance
        cluster = clusters.Cluster(name, profile_id, size, **kwargs)
        cluster.store()
        # Build an Action for Cluster creating
        action = actions.Action(context, cluster, 'CLUSTER_CREATE', **kwargs)
        action.store()
        # Notify Dispatcher that a new action has been ready.
        # TODO(Yanyan): We should broadcast this new action 
        # coming to all active Dispatchers.
        res = self._notify_dispatcher(
            context, self.engine_id, self.dispatcher.NEW_ACTION,
            action_id=action.id)

        return cluster.id

    @request_context
    def update_cluster(self, context, cluster_identity, profile_id):
        """
        Handle request to perform a update action on a cluster

        :param context: RPC context.
        :param cluster_identity: Name of the cluster you want to create.
        :param size: Size of cluster you want to create.
        :param profile: Profile used to create cluster nodes.
        """
        # Get the database representation of the existing cluster
        db_cluster = self._get_cluster(context, cluster_identity)
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

        action = actions.Action(context, cluster, 'CLUSTER_UPDATE', **kwargs)
        res = self._notify_dispatcher(
            context, self.engine_id, self.dispatcher.NEW_ACTION,
            action_id=action.id)

        return cluster.id

    @request_context
    def delete_cluster(self, context, cluster_identity):
        """
        Handle request to perform a delete action on a cluster

        :param context: RPC context.
        :param cluster_identity: Name or ID of the cluster you want to delete.
        """

        db_cluster = self._get_cluster(context, cluster_identity)
        LOG.info(_LI('Deleting cluster %s'), db_cluster.name)

        # This is an operation on a cluster, so we try to acquire ClusterLock
        cluster = clusters.Cluster.load(context, cluster=db_cluster)
        action = actions.Action(context, cluster, 'CLUSTER_DELETE')
        res = self._notify_dispatcher(
            context, self.engine_id, self.dispatcher.NEW_ACTION,
            action_id=action.id)

        return res

    def _notify_dispatcher(self, cnxt, engine_id, call, *args, **kwargs):
        '''Send notification to specific dispatcher'''
        timeout = cfg.CONF.engine_life_check_timeout
        self.cctxt = self._client.prepare(
            version='1.0',
            timeout=timeout,
            topic=engine_id)
        try:
            self.cctxt.call(cnxt, call, *args, **kwargs)
        except messaging.MessagingTimeout:
            return False

    def _broadcast_dispatcher(self, cnxt, engine_id, call, *args,
                               **kwargs):
        '''Broadcast the notification to all active dispatchers'''
        raise NotImplementedError
