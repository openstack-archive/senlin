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
from senlin.engine.thread_mgr import ThreadGroupManager
from senlin.openstack.common import log as logging
from senlin.openstack.common import service
from senlin.openstack.common import uuidutils

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
class EngineListener(service.Service):
    '''
    Listen on an AMQP queue named for the engine.  Allows individual
    engines to communicate with each other for multi-engine support.
    '''

    ACTIONS = (STOP_CLUSTER, SEND) = ('stop_cluster', 'send')

    def __init__(self, host, engine_id, thread_group_mgr):
        super(EngineListener, self).__init__()
        self.thread_group_mgr = thread_group_mgr
        self.engine_id = engine_id
        self.host = host

    def start(self):
        super(EngineListener, self).start()
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

    def stop_cluster(self, ctxt, cluster_id):
        '''Stop any active threads on a cluster.'''
        self.thread_group_mgr.stop(cluster_id)

    def send(self, ctxt, cluster_id, message):
        self.thread_group_mgr.send(cluster_id, message)


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
        self.host = host
        self.topic = topic

        # The following are initialized here, but assigned in start() which
        # happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.thread_group_mgr = None
        self.target = None

    def start(self):
        self.engine_id = senlin_lock.BaseLock.generate_engine_id()
        self.thread_group_mgr = ThreadGroupManager()
        self.listener = EngineListener(self.host, self.engine_id,
                                       self.thread_group_mgr)
        LOG.debug("Starting listener for engine %s" % self.engine_id)
        self.listener.start()

        target = messaging.Target(
            version=self.RPC_API_VERSION, server=self.host,
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

        # Wait for all active threads to be finished
        for cluster_id in self.thread_group_mgr.groups.keys():
            # Ignore dummy service task
            if cluster_id == cfg.CONF.periodic_interval:
                continue
            LOG.info(_LI("Waiting cluster %s processing to be finished"),
                     cluster_id)
            # Stop threads gracefully
            self.thread_group_mgr.stop(cluster_id, True)
            LOG.info(_LI("cluster %s processing was finished"), cluster_id)

        # Terminate the engine process
        LOG.info(_LI("All threads were gone, terminating engine"))
        super(EngineService, self).stop()

    @request_context
    def identify_cluster(self, cnxt, cluster_name):
        """
        The identify_cluster method returns the cluster id for a
        single, live cluster given the cluster name.

        :param cnxt: RPC context.
        :param cluster_name: Name or ID of the cluster to look up.
        """
        if uuidutils.is_uuid_like(cluster_name):
            db_cluster = db_api.cluster_get(cnxt, cluster_name,
                                            show_deleted=True)
            # may be the name is in uuid format, so if get by id returns None,
            # we should get the info by name again
            if not db_cluster:
                db_cluster = db_api.cluster_get_by_name(cnxt, cluster_name)
        else:
            db_cluster = db_api.cluster_get_by_name(cnxt, cluster_name)
        if db_cluster:
            cluster = clusters.Cluster.load(cnxt, cluster=db_cluster)
            return dict(cluster.id)
        else:
            raise exception.ClusterNotFound(cluster_name=cluster_name)

    def _get_cluster(self, cnxt, cluster_identity, show_deleted=False):
        """
        Get Cluster record in DB based on cluster id
        """
        # Currently, cluster_identity is cluster id OR cluster name
        # TODO: use full cluster identity as inpurt, e.g.
        #       *cluster_name/cluster_id*
        cluster_id = self.identify_cluster(cnxt, cluster_identity)

        db_cluster = db_api.cluster_get(cnxt, cluster_id,
                                        show_deleted=show_deleted,
                                        eager_load=True)

        if db_cluster is None:
            raise exception.ClusterNotFound(cluster_name=cluster_identity)

        return db_cluster

    @request_context
    def show_cluster(self, cnxt, cluster_identity):
        """
        Return detailed information about one or all clusters.

        :param cnxt: RPC context.
        :param cluster_identity: Name of the cluster you want to show, or None
            to show all
        """
        if cluster_identity is not None:
            db_cluster = self._get_cluster(cnxt, cluster_identity,
                                           show_deleted=True)
            cluster_list = clusters.Cluster.load(cnxt, cluster=db_cluster)
        else:
            cluster_list = clusters.Cluster.load_all(cnxt, show_deleted=True)

        # Format clusters info
        clusters_info = []
        for cluster in cluster_list:
            clusters_info.append(cluster.to_dict())

        return {'clusters': clusters_info}

    @request_context
    def list_clusters(self, cnxt, limit=None, marker=None, sort_keys=None,
                      sort_dir=None, filters=None, tenant_safe=True,
                      show_deleted=False, show_nested=False):
        """
        The list_clusters method returns attributes of all clusters.

        :param cnxt: RPC context
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
        cluster_list = clusters.Cluster.load_all(cnxt, limit, marker,
                                                 sort_keys, sort_dir,
                                                 filters, tenant_safe,
                                                 show_deleted, show_nested)

        # Format clusters info
        clusters_info = []
        for cluster in cluster_list:
            clusters_info.append(cluster.to_dict())

        return {'clusters': clusters_info}

    @request_context
    def create_cluster(self, cnxt, cluster_name, size, profile,
                       owner_id=None, nested_depth=0, user_creds_id=None,
                       cluster_user_project_id=None):
        """
        Handle request to perform a create action on a cluster

        :param cnxt: RPC context.
        :param cluster_name: Name of the cluster you want to create.
        :param size: Size of cluster you want to create.
        :param profile: Profile used to create cluster nodes.
        :param owner_id: parent cluster ID for nested clusters, only
                         expected when called from another senlin-engine
                         (not a user option)
        :param nested_depth: the nested depth for nested clusters, only
                             expected when called from another senlin-engine
        :param user_creds_id: the parent user_creds record for nested clusters
        :param cluster_user_project_id: the parent cluster_user_project_id for
                         nested clusters
        """
        LOG.info(_LI('Creating cluster %s'), cluster_name)

        # TODO: construct real kwargs based on input for cluster creating
        kwargs = {}
        kwargs['owner_id'] = owner_id
        kwargs['nested_depth'] = nested_depth
        kwargs['user_creds_id'] = user_creds_id
        kwargs['cluster_user_project_id'] = cluster_user_project_id

        cluster = clusters.Cluster(cluster_name, size, profile, **kwargs)
        action = actions.ClusterAction(cnxt, cluster, 'CREATE', **kwargs)

        self.thread_group_mgr.start_with_lock(cnxt, cluster, 'cluster',
                                              self.engine_id, action.execute)

        return cluster.id

    @request_context
    def update_cluster(self, cnxt, cluster_identity, profile):
        """
        Handle request to perform a update action on a cluster

        :param cnxt: RPC context.
        :param cluster_identity: Name of the cluster you want to create.
        :param size: Size of cluster you want to create.
        :param profile: Profile used to create cluster nodes.
        """
        # Get the database representation of the existing cluster
        db_cluster = self._get_cluster(cnxt, cluster_identity)
        LOG.info(_LI('Updating cluster %s'), db_cluster.name)

        cluster = clusters.Cluster.load(cnxt, cluster=db_cluster)
        if cluster.status == cluster.ERROR:
            msg = _('Updating a cluster when it is errored')
            raise exception.NotSupported(feature=msg)

        if cluster.status == cluster.DELETED:
            msg = _('Updating a cluster which has been deleted')
            raise exception.NotSupported(feature=msg)

        kwargs = {}
        kwargs['profile'] = profile
        action = actions.ClusterAction(cnxt, cluster, 'UPDATE', **kwargs)

        self.thread_group_mgr.start_with_lock(cnxt, cluster, 'cluster',
                                              self.engine_id, action.execute)

        return cluster.id

    @request_context
    def delete_cluster(self, cnxt, cluster_identity):
        """
        Handle request to perform a delete action on a cluster

        :param cnxt: RPC context.
        :param cluster_identity: Name or ID of the cluster you want to delete.
        """

        db_cluster = self._get_cluster(cnxt, cluster_identity)
        LOG.info(_LI('Deleting cluster %s'), db_cluster.name)

        # This is an operation on a cluster, so we try to acquire ClusterLock
        cluster = clusters.Cluster.load(cnxt, cluster=db_cluster)
        lock = senlin_lock.ClusterLock(cnxt, cluster, self.engine_id)
        with lock.try_thread_lock(cluster.id) as acquire_result:

            # Successfully acquired lock
            if acquire_result is None:
                self.thread_group_mgr.stop_timers(cluster.id)
                action = actions.ClusterAction(cnxt, cluster, 'DELETE')
                self.thread_group_mgr.start_with_acquired_lock(cluster, lock,
                                                               action.execute)
                return

        # Current engine has the lock
        if acquire_result == self.engine_id:
            # give threads which are almost complete an opportunity to
            # finish naturally before force stopping them
            eventlet.sleep(0.2)
            self.thread_group_mgr.stop(cluster.id)
        # Another active engine has the lock
        elif senlin_lock.ClusterLock.engine_alive(cnxt, acquire_result):
            stop_result = self._remote_call(
                cnxt, acquire_result, self.listener.STOP_CLUSTER,
                cluster_id=cluster.id)
            if stop_result is None:
                LOG.debug("Successfully stopped remote task on engine %s"
                          % acquire_result)
            else:
                raise exception.StopActionFailed(cluster_name=cluster.name,
                                                 engine_id=acquire_result)

        # There may be additional nodes that we don't know about
        # if an update was in-progress when the cluster was stopped, so
        # reload the cluster from the database.
        db_cluster = self._get_cluster(cnxt, cluster_identity)
        cluster = clusters.Cluster.load(cnxt, cluster=db_cluster)
        action = actions.ClusterAction(cnxt, cluster, 'DELETE')

        self.thread_group_mgr.start_with_lock(cnxt, cluster, 'cluster',
                                              self.engine_id, action.execute)

        return None

    @request_context
    def cluster_suspend(self, cnxt, cluster_identity):
        '''
        Handle request to perform suspend action on a cluster
        '''

        db_cluster = self._get_cluster(cnxt, cluster_identity)
        LOG.debug("suspending cluster %s" % db_cluster.name)

        cluster = clusters.Cluster.load(cnxt, cluster=db_cluster)
        action = actions.ClusterAction(cnxt, cluster, 'SUSPEND')

        self.thread_group_mgr.start_with_lock(cnxt, cluster, 'cluster',
                                              self.engine_id, action.execute)

    @request_context
    def cluster_resume(self, cnxt, cluster_identity):
        '''
        Handle request to perform a resume action on a cluster
        '''
        db_cluster = self._get_cluster(cnxt, cluster_identity)
        LOG.debug("resuming cluster %s" % db_cluster.name)

        cluster = clusters.Cluster.load(cnxt, cluster=db_cluster)
        action = actions.ClusterAction(cnxt, cluster, 'RESUME')

        self.thread_group_mgr.start_with_lock(cnxt, cluster, 'cluster',
                                              self.engine_id, action.execute)

    def _remote_call(self, cnxt, lock_engine_id, call, *args, **kwargs):
        self.cctxt = self._client.prepare(
            version='1.0',
            topic=lock_engine_id)
        try:
            self.cctxt.call(cnxt, call, *args, **kwargs)
        except messaging.MessagingTimeout:
            return False
