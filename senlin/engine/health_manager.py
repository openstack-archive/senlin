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

"""
Health Manager class.

Health Manager is responsible for monitoring the health of the clusters and
trigger corresponding actions to recover the clusters based on the pre-defined
health policies.
"""

from oslo_config import cfg
import oslo_messaging
from oslo_service import service
from oslo_service import threadgroup

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc_messaging
from senlin.objects import health_registry as hr
from senlin.rpc import client as rpc_client


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
        pass

    def _poll_cluster(self, cluster_id):
        """Routine to be executed for polling cluster status.

        @param cluster_id: The UUID of the cluster to be checked.
        @return Nothing.
        """
        self.rpc_client.cluster_check(self.ctx, cluster_id)

    def _start_check(self, entry):
        """Routine to call for starting the checking for a cluster.

        @param entry: A dict containing the data associated with the cluster.
        @return: An updated registry entry record.
        """
        if entry['check_type'] == consts.NODE_STATUS_POLLING:
            interval = min(entry['interval'], cfg.CONF.periodic_interval_max)
            timer = self.TG.add_timer(interval, self._poll_cluster, None,
                                      entry['cluster_id'])
            entry['timer'] = timer

        return entry

    def _load_runtime_registry(self):
        """Load the initial runtime registry with a DB scan."""
        db_registries = hr.HealthRegistry.claim(self.ctx, self.engine_id)

        for cluster in db_registries:
            entry = {
                'cluster_id': cluster.cluster_id,
                'check_type': cluster.check_type,
                'interval': cluster.interval,
                'params': cluster.params,
            }

            entry = self._start_check(entry)
            self.rt['registries'].append(entry)

    def start(self):
        super(HealthManager, self).start()
        self.target = oslo_messaging.Target(server=self.engine_id,
                                            topic=self.topic,
                                            version=self.version)
        server = rpc_messaging.get_rpc_server(self.target, self)
        server.start()
        self.TG.add_timer(cfg.CONF.periodic_interval, self._dummy_task)
        self._load_runtime_registry()

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
                         params=None):
        r"""Register cluster for health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be checked.
        :param check_type: A string indicating the type of checks.
        :param interval: An optional integer indicating the length of checking
                         periods in seconds.
        :param \*\*params: Other parameters for the health check.
        :return: None
        """
        params = params or {}

        registry = hr.HealthRegistry.create(ctx, cluster_id, check_type,
                                            interval, params, self.engine_id)

        entry = {
            'cluster_id': registry.cluster_id,
            'check_type': registry.check_type,
            'interval': registry.interval,
            'params': registry.params,
        }

        self._start_check(entry)
        self.rt['registries'].append(entry)

    def unregister_cluster(self, ctx, cluster_id):
        """Unregister a cluster from health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluste to be unregistered.
        :return: None
        """
        for i in range(len(self.rt['registries']) - 1, -1, -1):
            registry = self.rt['registries'][i]
            if registry.get('cluster_id') == cluster_id:
                timer = registry.get('timer', None)
                if timer:
                    timer.stop()
                    self.TG.timer_done(timer)
                self.rt['registries'].pop(i)
        hr.HealthRegistry.delete(ctx, cluster_id)


def notify(engine_id, method, **kwargs):
    """Send notification to health manager service.

    :param engine_id: dispatcher to notify; broadcast if value is None
    :param method: remote method to call
    """
    timeout = cfg.CONF.engine_life_check_timeout
    client = rpc_messaging.get_rpc_client(version=consts.RPC_API_VERSION)

    if engine_id:
        # Notify specific dispatcher identified by engine_id
        call_context = client.prepare(
            version=consts.RPC_API_VERSION,
            timeout=timeout,
            topic=consts.ENGINE_HEALTH_MGR_TOPIC,
            server=engine_id)
    else:
        # Broadcast to all disptachers
        call_context = client.prepare(
            version=consts.RPC_API_VERSION,
            timeout=timeout,
            topic=consts.ENGINE_HEALTH_MGR_TOPIC)

    ctx = context.get_admin_context()

    try:
        call_context.call(ctx, method, **kwargs)
        return True
    except oslo_messaging.MessagingTimeout:
        return False


def register(cluster_id, engine_id=None, **kwargs):
    params = kwargs.pop('params', {})
    interval = kwargs.pop('interval', cfg.CONF.periodic_interval)
    check_type = kwargs.pop('check_type', consts.NODE_STATUS_POLLING)
    return notify(engine_id, 'register_cluster',
                  cluster_id=cluster_id,
                  interval=interval,
                  check_type=check_type,
                  params=params)


def unregister(cluster_id, engine_id=None):
    return notify(engine_id,
                  'unregister_cluster',
                  cluster_id=cluster_id)
