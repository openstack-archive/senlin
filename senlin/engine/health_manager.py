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
import eventlet
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_utils import timeutils
import re
import tenacity

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc
from senlin.common import utils
from senlin.engine import node as node_mod
from senlin.engine.notifications import heat_endpoint
from senlin.engine.notifications import nova_endpoint
from senlin import objects
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


def chase_up(start_time, interval, name='Poller'):
    """Utility function to check if there are missed intervals.

    :param start_time: A time object representing the starting time.
    :param interval: An integer specifying the time interval in seconds.
    :param name: Name of the caller for identification in logs.
    :returns: Number of seconds to sleep before next round.
    """
    end_time = timeutils.utcnow(True)
    elapsed = timeutils.delta_seconds(start_time, end_time)
    # check if we have missed any intervals?
    missed = int((elapsed - 0.0000001) / interval)
    if missed >= 1:
        LOG.warning("%s missed %s intervals for checking", name, missed)
    return (missed + 1) * interval - elapsed


def ListenerProc(exchange, project_id, cluster_id, recover_action):
    """Thread procedure for running an event listener.

    :param exchange: The control exchange for a target service.
    :param project_id: The ID of the project to filter.
    :param cluster_id: The ID of the cluster to filter.
    :param recover_action: The health policy action name.
    """
    transport = messaging.get_notification_transport(cfg.CONF)

    if exchange == cfg.CONF.health_manager.nova_control_exchange:
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            project_id, cluster_id, recover_action
        )

    else:
        endpoint = heat_endpoint.HeatNotificationEndpoint(
            project_id, cluster_id, recover_action
        )

    listener = messaging.get_notification_listener(
        transport, [endpoint.target], [endpoint], executor='threading',
        pool='senlin-listeners'
    )

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
        elif detection_type == consts.HYPERVISOR_STATUS_POLLING:
            return HypervisorPollStatusHealthCheck(
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

            return (entity.do_healthcheck(ctx, consts.NODE_STATUS_POLLING) or
                    self._node_within_grace_period(node))
        except Exception as ex:
            LOG.warning(
                'Error when performing health check on node %s: %s',
                node.id, ex
            )

            # treat node as healthy when an exception is encountered
            return True


class HypervisorPollStatusHealthCheck(HealthCheckType):
    def run_health_check(self, ctx, node):
        """Routine to be executed for polling hypervisor status.

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

            return (entity.do_healthcheck(ctx,
                                          consts.HYPERVISOR_STATUS_POLLING) or
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
    def convert_detection_tuple(dictionary):
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
                LOG.info("%s for %s: connection error when polling URL (%s)",
                         consts.POLL_URL_FAIL, node.name, ex)
                return False
            else:
                LOG.info("%s for %s: ignoring connection error when polling "
                         "URL (%s)",
                         consts.POLL_URL_PASS, node.name, ex)
                return True

        if not re.search(expected_resp_str, result):
            LOG.info("%s for %s: did not find expected response string %s in "
                     "URL result (%s)",
                     consts.POLL_URL_FAIL, node.name, expected_resp_str,
                     result)
            return False

        LOG.info("%s for %s: matched expected response string.",
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
                LOG.info("%s for %s: node is not in ACTIVE state, so skip "
                         "poll url",
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
                "%s for %s: Ignoring error on poll URL: %s",
                consts.POLL_URL_PASS, node.name, ex
            )

            # treat node as healthy when an exception is encountered
            return True


class HealthCheck(object):

    def __init__(self, ctx, engine_id, cluster_id, check_type, interval,
                 node_update_timeout, params, enabled):
        self.rpc_client = rpc_client.get_engine_client()
        self.ctx = ctx
        self.engine_id = engine_id

        self.cluster_id = cluster_id
        self.check_type = check_type
        self.interval = interval
        self.node_update_timeout = node_update_timeout
        self.params = params
        self.enabled = enabled
        self.timer = None
        self.listener = None

        self.health_check_types = []
        self.recover_action = {}
        self.type = None
        self.get_health_check_types()
        self.get_recover_actions()

    def get_health_check_types(self):
        polling_types = [consts.NODE_STATUS_POLLING,
                         consts.NODE_STATUS_POLL_URL,
                         consts.HYPERVISOR_STATUS_POLLING]

        detection_types = self.check_type.split(',')
        if all(check in polling_types for check in detection_types):
            interval = min(self.interval, cfg.CONF.check_interval_max)
            for check in detection_types:
                self.health_check_types.append(
                    HealthCheckType.factory(
                        check, self.cluster_id, interval, self.params
                    )
                )
            self.type = consts.POLLING
        elif (len(detection_types) == 1 and
              detection_types[0] == consts.LIFECYCLE_EVENTS):
            self.type = consts.EVENTS

    def get_recover_actions(self):
        if 'node_delete_timeout' in self.params:
            self.recover_action['delete_timeout'] = self.params[
                'node_delete_timeout']
        if 'node_force_recreate' in self.params:
            self.recover_action['force_recreate'] = self.params[
                'node_force_recreate']
        if 'recover_action' in self.params:
            rac = self.params['recover_action']
            for operation in rac:
                self.recover_action['operation'] = operation.get('name')

    def execute_health_check(self):
        start_time = timeutils.utcnow(True)

        try:
            if not self.health_check_types:
                LOG.error("No health check types found for cluster: %s",
                          self.cluster_id)
                return chase_up(start_time, self.interval)

            cluster = objects.Cluster.get(self.ctx, self.cluster_id,
                                          project_safe=False)
            if not cluster:
                LOG.warning("Cluster (%s) is not found.", self.cluster_id)
                return chase_up(start_time, self.interval)

            ctx = context.get_service_context(user_id=cluster.user,
                                              project_id=cluster.project)

            actions = []

            # loop through nodes and run all health checks on each node
            nodes = objects.Node.get_all_by_cluster(ctx, self.cluster_id)

            for node in nodes:
                action = self._check_node_health(ctx, node, cluster)
                if action:
                    actions.append(action)

            for a in actions:
                # wait for action to complete
                res, reason = self._wait_for_action(
                    ctx, a['action'], self.node_update_timeout)
                if not res:
                    LOG.warning("Node recovery action %s did not complete "
                                "within specified timeout: %s", a['action'],
                                reason)

            if len(actions) == 0:
                LOG.info("Health check passed for all nodes in cluster %s.",
                         self.cluster_id)
        except Exception as ex:
            LOG.warning("Error while performing health check: %s", ex)

        finally:
            return chase_up(start_time, self.interval)

    def _check_node_health(self, ctx, node, cluster):
        node_is_healthy = True

        if self.params['recovery_conditional'] == consts.ANY_FAILED:
            # recovery happens if any detection mode fails
            # i.e. the inverse logic is that node is considered healthy
            # if all detection modes pass
            node_is_healthy = all(
                hc.run_health_check(ctx, node)
                for hc in self.health_check_types)
        elif self.params['recovery_conditional'] == consts.ALL_FAILED:
            # recovery happens if all detection modes fail
            # i.e. the inverse logic is that node is considered healthy
            # if any detection mode passes
            node_is_healthy = any(
                hc.run_health_check(ctx, node)
                for hc in self.health_check_types)
        else:
            raise Exception("%s is an invalid recovery conditional" %
                            self.params['recovery_conditional'])

        if not node_is_healthy:
            LOG.info("Health check failed for %s in %s and "
                     "recovery has started.",
                     node.name, cluster.name)
            return self._recover_node(ctx, node.id)

    def _wait_for_action(self, ctx, action_id, timeout):
        req = objects.ActionGetRequest(identity=action_id)
        action = {}
        with timeutils.StopWatch(timeout) as timeout_watch:
            while not timeout_watch.expired():
                action = self.rpc_client.call(ctx, 'action_get', req)
                if action['status'] in [consts.ACTION_SUCCEEDED,
                                        consts.ACTION_FAILED,
                                        consts.ACTION_CANCELLED]:
                    break
                eventlet.sleep(2)

        if not action:
            return False, "Failed to retrieve action."

        elif action['status'] == consts.ACTION_SUCCEEDED:
            return True, ""

        elif (action['status'] == consts.ACTION_FAILED or
              action['status'] == consts.ACTION_CANCELLED):
            return False, "Cluster check action failed or cancelled"

        return False, ("Timeout while waiting for node recovery action to "
                       "finish")

    def _recover_node(self, ctx, node_id):
        """Recover node

        :returns: Recover action
        """
        try:
            req = objects.NodeRecoverRequest(identity=node_id,
                                             params=self.recover_action)

            return self.rpc_client.call(ctx, 'node_recover', req)
        except Exception as ex:
            LOG.error("Error when performing node recovery for %s: %s",
                      node_id, ex)
            return None

    def db_create(self):
        try:
            objects.HealthRegistry.create(
                self.ctx, self.cluster_id, self.check_type, self.interval,
                self.params, self.engine_id, self.enabled)
            return True
        except Exception as ex:
            LOG.error("Error while adding health entry for cluster %s to "
                      "database: %s", self.cluster_id, ex)
            return False

    def db_delete(self):
        try:
            objects.HealthRegistry.delete(self.ctx, self.cluster_id)
            return True
        except Exception as ex:
            LOG.error("Error while removing health entry for cluster %s from "
                      "database: %s", self.cluster_id, ex)
            return False

    def enable(self):
        try:
            objects.HealthRegistry.update(self.ctx, self.cluster_id,
                                          {'enabled': True})
            self.enabled = True
            return True
        except Exception as ex:
            LOG.error("Error while enabling health entry for cluster %s: %s",
                      self.cluster_id, ex)
            return False

    def disable(self):
        try:
            objects.HealthRegistry.update(self.ctx, self.cluster_id,
                                          {'enabled': False})
            self.enabled = False
            return True
        except Exception as ex:
            LOG.error("Error while disabling health entry for cluster %s: %s",
                      self.cluster_id, ex)
            return False


class RuntimeHealthRegistry(object):
    def __init__(self, ctx, engine_id, thread_group):
        self.ctx = ctx
        self.engine_id = engine_id
        self.rt = {}
        self.tg = thread_group
        self.health_check_types = defaultdict(lambda: [])

    @property
    def registries(self):
        return self.rt

    def register_cluster(self, cluster_id, interval=None,
                         node_update_timeout=None, params=None,
                         enabled=True):
        """Register cluster to health registry.

        :param cluster_id: The ID of the cluster to be registered.
        :param interval: An optional integer indicating the length of checking
                         periods in seconds.
        :param node_update_timeout: Timeout to wait for node action to
                                    complete.
        :param dict params: Other parameters for the health check.
        :param enabled: Boolean indicating if the health check is enabled.
        :return: RuntimeHealthRegistry object for cluster
        """
        params = params or {}

        # extract check_type from params
        check_type = ""
        if 'detection_modes' in params:
            check_type = ','.join([
                NodePollUrlHealthCheck.convert_detection_tuple(d).type
                for d in params['detection_modes']
            ])

        # add node_update_timeout to params
        params['node_update_timeout'] = node_update_timeout
        entry = None
        try:
            entry = HealthCheck(
                ctx=self.ctx,
                engine_id=self.engine_id,
                cluster_id=cluster_id,
                check_type=check_type,
                interval=interval,
                node_update_timeout=node_update_timeout,
                params=params,
                enabled=enabled
            )
            if entry.db_create():
                self.registries[cluster_id] = entry
                self.add_health_check(self.registries[cluster_id])
        except Exception as ex:
            LOG.error("Error while trying to register cluster for health "
                      "check %s: %s", cluster_id, ex)
            if entry:
                entry.db_delete()

    def unregister_cluster(self, cluster_id):
        """Unregister a cluster from health registry.

        :param cluster_id: The ID of the cluster to be unregistered.
        :return: RuntimeHealthRegistry object for the cluster being
                 unregistered.
        """
        entry = None
        try:
            if cluster_id in self.registries:
                entry = self.registries.pop(cluster_id)
                entry.db_delete()
        except Exception as ex:
            LOG.error("Error while trying to unregister cluster from health "
                      "check %s: %s", cluster_id, ex)
        finally:
            if entry:
                self.remove_health_check(entry)

    def enable_cluster(self, cluster_id):
        """Update the status of a cluster to enabled in the health registry.

        :param cluster_id: The ID of the cluster to be enabled.
        """
        LOG.info("Enabling health check for cluster %s.", cluster_id)
        try:
            if cluster_id in self.registries:
                if self.registries[cluster_id].enable():
                    self.add_health_check(self.registries[cluster_id])
            else:
                LOG.error("Unable to enable cluster for health checking: %s",
                          cluster_id)
        except Exception as ex:
            LOG.error("Error while enabling health check for cluster %s: %s",
                      cluster_id, ex)
            if cluster_id in self.registries:
                self.remove_health_check(self.registries[cluster_id])

    def disable_cluster(self, cluster_id):
        """Update the status of a cluster to disabled in the health registry.

        :param cluster_id: The ID of the cluster to be disabled.
        :return: None.
        """
        LOG.info("Disabling health check for cluster %s.", cluster_id)
        try:
            if cluster_id in self.registries:
                self.registries[cluster_id].disable()
            else:
                LOG.error("Unable to disable cluster for health checking: %s",
                          cluster_id)
        except Exception as ex:
            LOG.error("Error while disabling health check for cluster %s: %s",
                      cluster_id, ex)
        finally:
            if cluster_id in self.registries:
                self.remove_health_check(self.registries[cluster_id])

    def _add_timer(self, cluster_id):
        entry = self.registries[cluster_id]
        if entry.timer:
            LOG.error("Health check for cluster %s already exists", cluster_id)
            return None
        timer = self.tg.add_dynamic_timer(entry.execute_health_check, None,
                                          None)
        if timer:
            entry.timer = timer
        else:
            LOG.error("Error creating timer for cluster: %s", cluster_id)

    def _add_listener(self, cluster_id):
        entry = self.registries[cluster_id]
        if entry.listener:
            LOG.error("Listener for cluster %s already exists", cluster_id)
            return

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
            return

        project = cluster.project
        listener = self.tg.add_thread(ListenerProc, exchange, project,
                                      cluster_id, entry.recover_action)
        if listener:
            entry.listener = listener
        else:
            LOG.error("Error creating listener for cluster: %s", cluster_id)

    def add_health_check(self, entry):
        """Add a health check to the RuntimeHealthRegistry.

        This method creates a timer/thread based on the type of health check
        being added.

        :param entry: Entry to add to the registry.
        :return: None
        """
        if entry.cluster_id in self.registries:
            if not entry.enabled:
                return
            elif entry.timer:
                LOG.error("Health check for cluster %s already exists",
                          entry.cluster_id)
                return
        else:
            LOG.error("Unable to add health check for cluster: %s",
                      entry.cluster_id)
            return

        if entry.type == consts.POLLING:
            self._add_timer(entry.cluster_id)
        elif entry.type == consts.EVENTS:
            LOG.info("Start listening events for cluster (%s).",
                     entry.cluster_id)
            self._add_listener(entry.cluster_id)
        else:
            LOG.error("Cluster %(id)s type %(type)s is invalid.",
                      {'id': entry.cluster_id, 'type': entry.type})

    def remove_health_check(self, entry):
        """Remove a health check for the RuntimeHealthRegistry.

        This method stops and removes the timer/thread based to the type of
        health check being removed.

        :param entry:
        :return: None
        """
        if entry.timer:
            # stop timer
            entry.timer.stop()

            try:
                # tell threadgroup to remove timer
                self.tg.timer_done(entry.timer)
            except ValueError:
                pass
            finally:
                entry.timer = None

        if entry.listener:
            try:
                self.tg.thread_done(entry.listener)
                entry.listener.stop()
            except ValueError:
                pass
            finally:
                entry.listener = None

    def load_runtime_registry(self):
        """Load the initial runtime registry with a DB scan."""
        db_registries = objects.HealthRegistry.claim(self.ctx, self.engine_id)

        for registry in db_registries:
            if registry.cluster_id in self.registries:
                LOG.warning("Skipping duplicate health check for cluster: %s",
                            registry.cluster_id)
            # Claiming indicates we claim a health registry who's engine was
            # dead, and we will update the health registry's engine_id with
            # current engine id. But we may not start check always.
            entry = HealthCheck(
                ctx=self.ctx,
                engine_id=self.engine_id,
                cluster_id=registry.cluster_id,
                check_type=registry.check_type,
                interval=registry.interval,
                node_update_timeout=registry.params['node_update_timeout'],
                params=registry.params,
                enabled=registry.enabled
            )

            LOG.info("Loading cluster %(c)s enabled=%(e)s for "
                     "health monitoring",
                     {'c': registry.cluster_id, 'e': registry.enabled})
            self.registries[registry.cluster_id] = entry
            if registry.enabled:
                self.add_health_check(self.registries[registry.cluster_id])


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
