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

from collections import defaultdict
from collections import namedtuple
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_service import service
from oslo_service import threadgroup
from oslo_utils import timeutils
import re
import tenacity
import time

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc
from senlin.common import utils
from senlin.engine import node as node_mod
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
    """Thread procedure for running an event listener.

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


class HealthCheckType(object):
    @staticmethod
    def factory(detection_type, cid, interval, params):
        node_update_timeout = params['node_update_timeout']
        detection_params = [
            p for p in params['detection_modes']
            if p['type'] == detection_type
        ]
        if len(detection_params) != 1:
            raise Exception(
                'The same detection mode cannot be used more than once in the '
                'same policy. Encountered {} instances of '
                'type {}.'.format(len(detection_params), detection_type)
            )

        if detection_type == consts.NODE_STATUS_POLLING:
            return NodePollStatusHealthCheck(
                cid, interval, node_update_timeout, detection_params[0])
        elif detection_type == consts.NODE_STATUS_POLL_URL:
            return NodePollUrlHealthCheck(
                cid, interval, node_update_timeout, detection_params[0])
        else:
            raise Exception(
                'Invalid detection type: {}'.format(detection_type))

    def __init__(self, cluster_id, interval, node_update_timeout, params):
        """Initialize HealthCheckType

        :param ctx:
        :param cluster_id: The UUID of the cluster to be checked.
        :param params: Parameters specific to poll url or recovery action.
        """
        self.cluster_id = cluster_id
        self.interval = interval
        self.node_update_timeout = node_update_timeout
        self.params = params

    def run_health_check(self, ctx, node):
        """Run health check on node

        :returns: True if node is healthy. False otherwise.
        """
        pass

    def _node_within_grace_period(self, node):
        """Check if current time is within the node_update_timeout grace period

        :returns: True if current time is less than node_update_timeout since
            last node update action. False otherwise.
        """

        node_last_updated = node.updated_at or node.init_at
        if timeutils.is_older_than(node_last_updated,
                                   self.node_update_timeout):
            # node was last updated more than node_update_timeout seconds ago
            # -> we are outside the grace period
            LOG.info("%s was updated at %s which is more "
                     "than %d secs ago. Mark node as unhealthy.",
                     node.name, node_last_updated,
                     self.node_update_timeout)
            return False
        else:
            # node was last updated less than node_update_timeout seconds ago
            # -> we are inside the grace period
            LOG.info("%s was updated at %s which is less "
                     "than %d secs ago. Mark node as healthy.",
                     node.name, node_last_updated,
                     self.node_update_timeout)
            return True


class NodePollStatusHealthCheck(HealthCheckType):
    def run_health_check(self, ctx, node):
        """Routine to be executed for polling node status.

        :returns: True if node is healthy. False otherwise.
        """
        try:
            # create engine node from db node
            entity = node_mod.Node._from_object(ctx, node)

            # If health check returns True, return True to mark node as
            # healthy. Else return True to mark node as healthy if we are still
            # within the node's grace period to allow the node to warm-up.
            # Return False to mark the node as unhealthy if we are outside the
            # grace period.

            return (entity.do_healthcheck(ctx) or
                    self._node_within_grace_period(node))
        except Exception as ex:
            LOG.warning(
                'Error when performing health check on node %s: %s',
                node.id, ex
            )

            # treat node as healthy when an exception is encountered
            return True


class NodePollUrlHealthCheck(HealthCheckType):
    @staticmethod
    def _convert_detection_tuple(dictionary):
        return namedtuple('DetectionMode', dictionary.keys())(**dictionary)

    def _expand_url_template(self, url_template, node):
        """Expands parameters in an URL template

        :param url_template:
            A string containing parameters that will be expanded. Currently
            only the {nodename} parameter is supported, which will be replaced
            by the actual node name.
        :param node: The DB object for the node to use for parameter expansion
        :returns: A string containing the expanded URL
        """

        nodename_pattern = re.compile("(\{nodename\})")
        url = nodename_pattern.sub(node.name, url_template)

        return url

    def _poll_url(self, url, node):
        verify_ssl = self.params['poll_url_ssl_verify']
        conn_error_as_unhealthy = self.params[
            'poll_url_conn_error_as_unhealthy']
        expected_resp_str = self.params['poll_url_healthy_response']
        retry_interval = self.params['poll_url_retry_interval']

        timeout = max(retry_interval * 0.1, 1)

        try:
            result = utils.url_fetch(url, timeout=timeout,
                                     verify=verify_ssl)
        except Exception as ex:
            if conn_error_as_unhealthy:
                LOG.info('%s for %s: connection error when polling URL (%s)',
                         consts.POLL_URL_FAIL, node.name, ex)
                return False
            else:
                LOG.info('%s for %s: ignoring connection error when polling '
                         'URL (%s)',
                         consts.POLL_URL_PASS, node.name, ex)
                return True

        if not re.search(expected_resp_str, result):
            LOG.info('%s for %s: did not find expected response string %s in '
                     'URL result (%s)',
                     consts.POLL_URL_FAIL, node.name, expected_resp_str,
                     result)
            return False

        LOG.info('%s for %s: matched expected response string.',
                 consts.POLL_URL_PASS, node.name)
        return True

    def run_health_check(self, ctx, node):
        """Routine to check a node status from a url and recovery if necessary

        :param node: The node to be checked.
        :returns: True if node is healthy. False otherwise.
        """

        max_unhealthy_retry = self.params['poll_url_retry_limit']
        retry_interval = self.params['poll_url_retry_interval']

        def _return_last_value(retry_state):
            return retry_state.outcome.result()

        @tenacity.retry(
            retry=tenacity.retry_if_result(lambda x: x is False),
            wait=tenacity.wait_fixed(retry_interval),
            retry_error_callback=_return_last_value,
            stop=tenacity.stop_after_attempt(max_unhealthy_retry)
        )
        def _poll_url_with_retry(url):
            return self._poll_url(url, node)

        try:
            if node.status != consts.NS_ACTIVE:
                LOG.info('%s for %s: node is not in ACTIVE state, so skip '
                         'poll url',
                         consts.POLL_URL_PASS, node.name)
                return True

            url_template = self.params['poll_url']
            url = self._expand_url_template(url_template, node)

            # If health check returns True, return True to mark node as
            # healthy. Else return True to mark node as healthy if we are still
            # within the node's grace period to allow the node to warm-up.
            # Return False to mark the node as unhealthy if we are outside the
            # grace period.

            return (_poll_url_with_retry(url) or
                    self._node_within_grace_period(node))
        except Exception as ex:
            LOG.warning(
                '%s for %s: Ignoring error on poll URL: %s',
                consts.POLL_URL_PASS, node.name, ex
            )

            # treat node as healthy when an exception is encountered
            return True


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
        self.health_check_types = defaultdict(lambda: [])

    def _dummy_task(self):
        """A Dummy task that is queued on the health manager thread group.

        The task is here so that the service always has something to wait()
        on, or else the process will exit.
        """

        try:
            self._load_runtime_registry()
        except Exception as ex:
            LOG.error("Failed when running '_load_runtime_registry': %s", ex)

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

    def _recover_node(self, node_id, ctx, recover_action):
        """Recover node

        :returns: Recover action
        """
        try:
            req = objects.NodeRecoverRequest(identity=node_id,
                                             params=recover_action)

            return self.rpc_client.call(ctx, 'node_recover', req)
        except Exception as ex:
            LOG.error('Error when performing node recovery for %s: %s',
                      node_id, ex)
            return None

    def _wait_for_action(self, ctx, action_id, timeout):
        req = objects.ActionGetRequest(identity=action_id)
        with timeutils.StopWatch(timeout) as timeout_watch:
            while not timeout_watch.expired():
                action = self.rpc_client.call(ctx, 'action_get', req)
                if action['status'] in [
                    consts.ACTION_SUCCEEDED, consts.ACTION_FAILED,
                        consts.ACTION_CANCELLED]:
                    break
                time.sleep(2)

        if action['status'] == consts.ACTION_SUCCEEDED:
            return True, ""

        if (action['status'] == consts.ACTION_FAILED or
                action['status'] == consts.ACTION_CANCELLED):
            return False, "Cluster check action failed or cancelled"

        return False, ("Timeout while waiting for node recovery action to "
                       "finish")

    def _add_health_check(self, cluster_id, health_check):
        self.health_check_types[cluster_id].append(health_check)

    def _execute_health_check(self, interval, cluster_id,
                              recover_action, recovery_cond,
                              node_update_timeout):
        start_time = timeutils.utcnow(True)

        try:
            if cluster_id not in self.health_check_types:
                LOG.error("Cluster (%s) is not found in health_check_types.",
                          self.cluster_id)
                return _chase_up(start_time, interval)

            if len(self.health_check_types[cluster_id]) == 0:
                LOG.error("No health check types found for Cluster (%s).",
                          self.cluster_id)
                return _chase_up(start_time, interval)

            cluster = objects.Cluster.get(self.ctx, cluster_id,
                                          project_safe=False)
            if not cluster:
                LOG.warning("Cluster (%s) is not found.", self.cluster_id)
                return _chase_up(start_time, interval)

            ctx = context.get_service_context(user_id=cluster.user,
                                              project_id=cluster.project)

            actions = []

            # loop through nodes and run all health checks on each node
            nodes = objects.Node.get_all_by_cluster(ctx, cluster_id)

            for node in nodes:
                node_is_healthy = True

                if recovery_cond == consts.ANY_FAILED:
                    # recovery happens if any detection mode fails
                    # i.e. the inverse logic is that node is considered healthy
                    # if all detection modes pass
                    node_is_healthy = all(
                        hc.run_health_check(ctx, node)
                        for hc in self.health_check_types[cluster_id])
                elif recovery_cond == consts.ALL_FAILED:
                    # recovery happens if all detection modes fail
                    # i.e. the inverse logic is that node is considered healthy
                    # if any detection mode passes
                    node_is_healthy = any(
                        hc.run_health_check(ctx, node)
                        for hc in self.health_check_types[cluster_id])
                else:
                    raise Exception(
                        '{} is an invalid recovery conditional'.format(
                            recovery_cond))

                if not node_is_healthy:
                    LOG.info("Health check failed for %s in %s and "
                             "recovery has started.",
                             node.name, cluster.name)
                    action = self._recover_node(node.id, ctx,
                                                recover_action)
                    actions.append(action)

            for a in actions:
                # wait for action to complete
                res, reason = self._wait_for_action(
                    ctx, a['action'], node_update_timeout)
                if not res:
                    LOG.warning("Node recovery action %s did not complete "
                                "within specified timeout: %s", a['action'],
                                reason)

            if len(actions) == 0:
                LOG.info('Health check passed for all nodes in cluster %s.',
                         cluster_id)
        except Exception as ex:
            LOG.warning('Error while performing health check: %s', ex)

        return _chase_up(start_time, interval)

    def _start_check(self, entry):
        """Routine for starting the checking for a cluster.

        :param entry: A dict containing the data associated with the cluster.
        :returns: An updated registry entry record.
        """
        LOG.info('Enabling health check for cluster %s.', entry['cluster_id'])

        cid = entry['cluster_id']
        ctype = entry['check_type']
        # Get the recover action parameter from the entry params
        params = entry['params']

        recover_action = {}
        if 'node_delete_timeout' in params:
            recover_action['delete_timeout'] = params['node_delete_timeout']
        if 'node_force_recreate' in params:
            recover_action['force_recreate'] = params['node_force_recreate']
        if 'recover_action' in params:
            rac = params['recover_action']
            for operation in rac:
                recover_action['operation'] = operation.get('name')

        polling_types = [consts.NODE_STATUS_POLLING,
                         consts.NODE_STATUS_POLL_URL]

        detection_types = ctype.split(',')
        if all(check in polling_types for check in detection_types):
            interval = min(entry['interval'], cfg.CONF.check_interval_max)
            for check in ctype.split(','):
                self._add_health_check(cid, HealthCheckType.factory(
                    check, cid, interval, params))
            timer = self.TG.add_dynamic_timer(self._execute_health_check,
                                              None, None, interval, cid,
                                              recover_action,
                                              params['recovery_conditional'],
                                              params['node_update_timeout'])

            entry['timer'] = timer
        elif (len(detection_types) == 1 and
              detection_types[0] == consts.LIFECYCLE_EVENTS):
            LOG.info("Start listening events for cluster (%s).", cid)
            listener = self._add_listener(cid, recover_action)
            if listener:
                entry['listener'] = listener
            else:
                LOG.warning("Error creating listener for cluster %s", cid)
                return None
        else:
            LOG.error("Cluster %(id)s check type %(type)s is invalid.",
                      {'id': cid, 'type': ctype})
            return None

        return entry

    def _stop_check(self, entry):
        """Routine for stopping the checking for a cluster.

        :param entry: A dict containing the data associated with the cluster.
        :returns: ``None``.
        """
        LOG.info('Disabling health check for cluster %s.', entry['cluster_id'])

        timer = entry.get('timer', None)
        if timer:
            # stop timer
            timer.stop()

            # tell threadgroup to remove timer
            self.TG.timer_done(timer)
            if entry['cluster_id'] in self.health_check_types:
                self.health_check_types.pop(entry['cluster_id'])
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

    def register_cluster(self, ctx, cluster_id, interval=None,
                         node_update_timeout=None, params=None,
                         enabled=True):
        """Register cluster for health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be checked.
        :param interval: An optional integer indicating the length of checking
                         periods in seconds.
        :param dict params: Other parameters for the health check.
        :return: None
        """
        params = params or {}

        # extract check_type from params
        check_type = ""
        if 'detection_modes' in params:
            check_type = ','.join([
                NodePollUrlHealthCheck._convert_detection_tuple(d).type
                for d in params['detection_modes']
            ])

        # add node_update_timeout to params
        params['node_update_timeout'] = node_update_timeout

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
        LOG.debug('unregister done')

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
    node_update_timeout = kwargs.pop('node_update_timeout', 300)
    enabled = kwargs.pop('enabled', True)
    return notify(engine_id, 'register_cluster',
                  cluster_id=cluster_id,
                  interval=interval,
                  node_update_timeout=node_update_timeout,
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
