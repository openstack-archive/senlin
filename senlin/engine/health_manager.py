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

"""Health Manager.

Health Manager is responsible for monitoring the health of the clusters and
trigger corresponding actions to recover the clusters based on the pre-defined
health policies.
"""

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_service import service
from oslo_service import threadgroup
from oslo_utils import timeutils
import six
import time

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc
from senlin import objects
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


def _chase_up(start_time, interval):
    """Utility function to check if there are missed intervals.

    :param start_time: A time object representing the starting time.
    :param interval: An integer specifying the time interval in seconds.
    :returns: Number of seconds to sleep before next round.
    """
    end_time = timeutils.utcnow(True)
    elapsed = timeutils.delta_seconds(start_time, end_time)
    # check if we have missed any intervals?
    missed = int((elapsed - 0.0000001) / interval)
    if missed >= 1:
        LOG.warning("Poller missed %s intervals for checking", missed)
    return (missed + 1) * interval - elapsed


class NovaNotificationEndpoint(object):

    VM_FAILURE_EVENTS = {
        'compute.instance.pause.end': 'PAUSE',
        'compute.instance.power_off.end': 'POWER_OFF',
        'compute.instance.rebuild.error': 'REBUILD',
        'compute.instance.shutdown.end': 'SHUTDOWN',
        'compute.instance.soft_delete.end': 'SOFT_DELETE',
    }

    def __init__(self, project_id, cluster_id, recover_action):
        self.filter_rule = messaging.NotificationFilter(
            publisher_id='^compute.*',
            event_type='^compute\.instance\..*',
            context={'project_id': '^%s$' % project_id})
        self.project_id = project_id
        self.cluster_id = cluster_id
        self.rpc = rpc_client.EngineClient()
        self.recover_action = recover_action

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        meta = payload['metadata']
        if meta.get('cluster_id') == self.cluster_id:
            if event_type not in self.VM_FAILURE_EVENTS:
                return
            params = {
                'event': self.VM_FAILURE_EVENTS[event_type],
                'state': payload.get('state', 'Unknown'),
                'instance_id': payload.get('instance_id', 'Unknown'),
                'timestamp': metadata['timestamp'],
                'publisher': publisher_id,
                'operation': self.recover_action['operation'],
            }
            node_id = meta.get('cluster_node_id')
            if node_id:
                LOG.info("Requesting node recovery: %s", node_id)
                ctx = context.get_service_context(project_id=self.project_id,
                                                  user_id=payload['user_id'])
                req = objects.NodeRecoverRequest(identity=node_id,
                                                 params=params)
                self.rpc.call(ctx, 'node_recover', req)

    def warn(self, ctxt, publisher_id, event_type, payload, metadata):
        meta = payload.get('metadata', {})
        if meta.get('cluster_id') == self.cluster_id:
            LOG.warning("publisher=%s", publisher_id)
            LOG.warning("event_type=%s", event_type)

    def debug(self, ctxt, publisher_id, event_type, payload, metadata):
        meta = payload.get('metadata', {})
        if meta.get('cluster_id') == self.cluster_id:
            LOG.debug("publisher=%s", publisher_id)
            LOG.debug("event_type=%s", event_type)


class HeatNotificationEndpoint(object):

    STACK_FAILURE_EVENTS = {
        'orchestration.stack.delete.end': 'DELETE',
    }

    def __init__(self, project_id, cluster_id, recover_action):
        self.filter_rule = messaging.NotificationFilter(
            publisher_id='^orchestration.*',
            event_type='^orchestration\.stack\..*',
            context={'project_id': '^%s$' % project_id})
        self.project_id = project_id
        self.cluster_id = cluster_id
        self.rpc = rpc_client.EngineClient()
        self.recover_action = recover_action

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        if event_type not in self.STACK_FAILURE_EVENTS:
            return

        tags = payload['tags']
        if tags is None or tags == []:
            return

        cluster_id = None
        node_id = None
        for tag in tags:
            if cluster_id is None:
                start = tag.find('cluster_id')
                if start == 0 and tag[11:] == self.cluster_id:
                    cluster_id = tag[11:]
            if node_id is None:
                start = tag.find('cluster_node_id')
                if start == 0:
                    node_id = tag[16:]

        if cluster_id is None or node_id is None:
            return

        params = {
            'event': self.STACK_FAILURE_EVENTS[event_type],
            'state': payload.get('state', 'Unknown'),
            'stack_id': payload.get('stack_identity', 'Unknown'),
            'timestamp': metadata['timestamp'],
            'publisher': publisher_id,
            'operation': self.recover_action['operation'],
        }
        LOG.info("Requesting stack recovery: %s", node_id)
        ctx = context.get_service_context(project_id=self.project_id,
                                          user_id=payload['user_identity'])
        req = objects.NodeRecoverRequest(identity=node_id, params=params)
        self.rpc.call(ctx, 'node_recover', req)


def ListenerProc(exchange, project_id, cluster_id, recover_action):
    """Thread procedure for running a event listener.

    :param exchange: The control exchange for a target service.
    :param project_id: The ID of the project to filter.
    :param cluster_id: The ID of the cluster to filter.
    :param recover_action: The health policy action name.
    """
    transport = messaging.get_notification_transport(cfg.CONF)

    if exchange == cfg.CONF.health_manager.nova_control_exchange:
        targets = [
            messaging.Target(topic='versioned_notifications',
                             exchange=exchange),
        ]
        endpoints = [
            NovaNotificationEndpoint(project_id, cluster_id, recover_action),
        ]
    else:  # heat notification
        targets = [
            messaging.Target(topic='notifications', exchange=exchange),
        ]
        endpoints = [
            HeatNotificationEndpoint(project_id, cluster_id, recover_action),
        ]

    listener = messaging.get_notification_listener(
        transport, targets, endpoints, executor='threading',
        pool="senlin-listeners")

    listener.start()


class HealthManager(service.Service):

    def __init__(self, engine_service, topic, version):
        super(HealthManager, self).__init__()

        self.TG = threadgroup.ThreadGroup()
        self.engine_id = engine_service.engine_id
        self.topic = topic
        self.version = version
        self.ctx = context.get_admin_context()
        self.rpc_client = rpc_client.EngineClient()
        self.rt = {
            'registries': [],
        }

    def _dummy_task(self):
        """A Dummy task that is queued on the health manager thread group.

        The task is here so that the service always has something to wait()
        on, or else the process will exit.
        """
        self._load_runtime_registry()

    def _wait_for_action(self, ctx, action_id, timeout):
        done = False
        req = objects.ActionGetRequest(identity=action_id)
        with timeutils.StopWatch(timeout) as timeout_watch:
            while timeout > 0:
                action = self.rpc_client.call(ctx, 'action_get', req)
                if action['status'] in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    if action['status'] == 'SUCCEEDED':
                        done = True
                    break
                time.sleep(2)
                timeout = timeout_watch.leftover(True)

        if done:
            return True, ""
        elif timeout <= 0:
            return False, "Timeout while polling cluster status"
        else:
            return False, "Cluster check action failed or cancelled"

    def _poll_cluster(self, cluster_id, timeout, recover_action):
        """Routine to be executed for polling cluster status.

        :param cluster_id: The UUID of the cluster to be checked.
        :param timeout: The maximum number of seconds to wait.
        :param recover_action: The health policy action name.
        :returns: Nothing.
        """
        start_time = timeutils.utcnow(True)
        cluster = objects.Cluster.get(self.ctx, cluster_id, project_safe=False)
        if not cluster:
            LOG.warning("Cluster (%s) is not found.", cluster_id)
            return _chase_up(start_time, timeout)

        ctx = context.get_service_context(user_id=cluster.user,
                                          project_id=cluster.project)
        params = {'delete_check_action': True}
        try:
            req = objects.ClusterCheckRequest(identity=cluster_id,
                                              params=params)
            action = self.rpc_client.call(ctx, 'cluster_check', req)
        except Exception as ex:
            LOG.warning("Failed in triggering 'cluster_check' RPC for "
                        "'%(c)s': %(r)s",
                        {'c': cluster_id, 'r': six.text_type(ex)})
            return _chase_up(start_time, timeout)

        # wait for action to complete
        res, reason = self._wait_for_action(ctx, action['action'], timeout)
        if not res:
            LOG.warning("%s", reason)
            return _chase_up(start_time, timeout)

        # loop through nodes to trigger recovery
        nodes = objects.Node.get_all_by_cluster(ctx, cluster_id)
        for node in nodes:
            if node.status != 'ACTIVE':
                LOG.info("Requesting node recovery: %s", node.id)
                req = objects.NodeRecoverRequest(identity=node.id,
                                                 params=recover_action)
                self.rpc_client.call(ctx, 'node_recover', req)

        return _chase_up(start_time, timeout)

    def _add_listener(self, cluster_id, recover_action):
        """Routine to be executed for adding cluster listener.

        :param cluster_id: The UUID of the cluster to be filtered.
        :param recover_action: The health policy action name.
        :returns: Nothing.
        """
        cluster = objects.Cluster.get(self.ctx, cluster_id, project_safe=False)
        if not cluster:
            LOG.warning("Cluster (%s) is not found.", cluster_id)
            return
        profile = objects.Profile.get(self.ctx, cluster.profile_id,
                                      project_safe=False)
        profile_type = profile.type.split('-')[0]
        if profile_type == 'os.nova.server':
            exchange = cfg.CONF.health_manager.nova_control_exchange
        elif profile_type == 'os.heat.stack':
            exchange = cfg.CONF.health_manager.heat_control_exchange
        else:
            return None

        project = cluster.project
        return self.TG.add_thread(ListenerProc, exchange, project, cluster_id,
                                  recover_action)

    def _start_check(self, entry):
        """Routine for starting the checking for a cluster.

        :param entry: A dict containing the data associated with the cluster.
        :returns: An updated registry entry record.
        """
        cid = entry['cluster_id']
        ctype = entry['check_type']
        # Get the recover action parameter from the entry params
        params = entry['params']
        recover_action = {}
        if 'recover_action' in params:
            rac = params['recover_action']
            for operation in rac:
                recover_action['operation'] = operation.get('name')

        if ctype == consts.NODE_STATUS_POLLING:
            interval = min(entry['interval'], cfg.CONF.check_interval_max)
            timer = self.TG.add_dynamic_timer(self._poll_cluster,
                                              None,  # initial_delay
                                              None,  # check_interval_max
                                              cid, interval, recover_action)
            entry['timer'] = timer
        elif ctype == consts.LIFECYCLE_EVENTS:
            LOG.info("Start listening events for cluster (%s).", cid)
            listener = self._add_listener(cid, recover_action)
            if listener:
                entry['listener'] = listener
            else:
                LOG.warning("Error creating listener for cluster %s", cid)
                return None
        else:
            LOG.warning("Cluster %(id)s check type %(type)s is invalid.",
                        {'id': cid, 'type': ctype})
            return None

        return entry

    def _stop_check(self, entry):
        """Routine for stopping the checking for a cluster.

        :param entry: A dict containing the data associated with the cluster.
        :returns: ``None``.
        """
        timer = entry.get('timer', None)
        if timer:
            timer.stop()
            self.TG.timer_done(timer)
            return

        listener = entry.get('listener', None)
        if listener:
            self.TG.thread_done(listener)
            listener.stop()
            return

    def _load_runtime_registry(self):
        """Load the initial runtime registry with a DB scan."""
        db_registries = objects.HealthRegistry.claim(self.ctx, self.engine_id)

        for r in db_registries:
            # Claiming indicates we claim a health registry who's engine was
            # dead, and we will update the health registry's engine_id with
            # current engine id. But we may not start check always.
            entry = {
                'cluster_id': r.cluster_id,
                'check_type': r.check_type,
                'interval': r.interval,
                'params': r.params,
                'enabled': r.enabled,
            }

            LOG.info("Loading cluster %(c)s enabled=%(e)s for "
                     "health monitoring",
                     {'c': r.cluster_id, 'e': r.enabled})

            if r.enabled:
                entry = self._start_check(entry)
            if entry:
                self.rt['registries'].append(entry)

    def start(self):
        """Start the health manager RPC server.

        Note that the health manager server uses JSON serializer for parameter
        passing. We should be careful when changing this interface.
        """
        super(HealthManager, self).start()
        self.target = messaging.Target(server=self.engine_id, topic=self.topic,
                                       version=self.version)
        server = rpc.get_rpc_server(self.target, self)
        server.start()
        self.TG.add_timer(cfg.CONF.periodic_interval, self._dummy_task)

    def stop(self):
        self.TG.stop_timers()
        super(HealthManager, self).stop()

    @property
    def registries(self):
        return self.rt['registries']

    def listening(self, ctx):
        """Respond to confirm that the rpc service is still alive."""
        return True

    def register_cluster(self, ctx, cluster_id, check_type, interval=None,
                         params=None, enabled=True):
        """Register cluster for health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be checked.
        :param check_type: A string indicating the type of checks.
        :param interval: An optional integer indicating the length of checking
                         periods in seconds.
        :param dict params: Other parameters for the health check.
        :return: None
        """
        params = params or {}

        registry = objects.HealthRegistry.create(ctx, cluster_id, check_type,
                                                 interval, params,
                                                 self.engine_id,
                                                 enabled=enabled)

        entry = {
            'cluster_id': registry.cluster_id,
            'check_type': registry.check_type,
            'interval': registry.interval,
            'params': registry.params,
            'enabled': registry.enabled
        }

        if registry.enabled:
            self._start_check(entry)

        self.rt['registries'].append(entry)

    def unregister_cluster(self, ctx, cluster_id):
        """Unregister a cluster from health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be unregistered.
        :return: None
        """
        for i in range(len(self.rt['registries']) - 1, -1, -1):
            entry = self.rt['registries'][i]
            if entry.get('cluster_id') == cluster_id:
                self._stop_check(entry)
                self.rt['registries'].pop(i)
        objects.HealthRegistry.delete(ctx, cluster_id)

    def enable_cluster(self, ctx, cluster_id, params=None):
        for c in self.rt['registries']:
            if c['cluster_id'] == cluster_id and not c['enabled']:
                c['enabled'] = True
                objects.HealthRegistry.update(ctx, cluster_id,
                                              {'enabled': True})
                self._start_check(c)

    def disable_cluster(self, ctx, cluster_id, params=None):
        for c in self.rt['registries']:
            if c['cluster_id'] == cluster_id and c['enabled']:
                c['enabled'] = False
                objects.HealthRegistry.update(ctx, cluster_id,
                                              {'enabled': False})
                self._stop_check(c)


def notify(engine_id, method, **kwargs):
    """Send notification to health manager service.

    Note that the health manager only handles JSON type of parameter passing.

    :param engine_id: dispatcher to notify; broadcast if value is None
    :param method: remote method to call
    """
    timeout = cfg.CONF.engine_life_check_timeout
    client = rpc.get_rpc_client(consts.HEALTH_MANAGER_TOPIC, None)

    if engine_id:
        # Notify specific dispatcher identified by engine_id
        call_context = client.prepare(timeout=timeout, server=engine_id)
    else:
        # Broadcast to all disptachers
        call_context = client.prepare(timeout=timeout)

    ctx = context.get_admin_context()

    try:
        call_context.call(ctx, method, **kwargs)
        return True
    except messaging.MessagingTimeout:
        return False


def register(cluster_id, engine_id=None, **kwargs):
    params = kwargs.pop('params', {})
    interval = kwargs.pop('interval', cfg.CONF.periodic_interval)
    check_type = kwargs.pop('check_type', consts.NODE_STATUS_POLLING)
    enabled = kwargs.pop('enabled', True)
    return notify(engine_id, 'register_cluster',
                  cluster_id=cluster_id,
                  interval=interval,
                  check_type=check_type,
                  params=params,
                  enabled=enabled)


def unregister(cluster_id):
    engine_id = get_manager_engine(cluster_id)
    if engine_id:
        return notify(engine_id, 'unregister_cluster', cluster_id=cluster_id)
    return True


def enable(cluster_id, **kwargs):
    engine_id = get_manager_engine(cluster_id)
    if engine_id:
        return notify(engine_id, 'enable_cluster', cluster_id=cluster_id,
                      params=kwargs)
    return False


def disable(cluster_id, **kwargs):
    engine_id = get_manager_engine(cluster_id)
    if engine_id:
        return notify(engine_id, 'disable_cluster', cluster_id=cluster_id,
                      params=kwargs)
    return False


def get_manager_engine(cluster_id):
    ctx = context.get_admin_context()

    registry = objects.HealthRegistry.get(ctx, cluster_id)
    if not registry:
        return None

    return registry.engine_id
