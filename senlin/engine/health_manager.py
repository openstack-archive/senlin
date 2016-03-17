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
from senlin.db import api as db_api
from senlin.rpc import client as rpc_client


health_mgr_opts = [
    cfg.IntOpt('periodic_interval_max',
               default=60,
               help='Seconds between periodic tasks to be called'),
]

CONF = cfg.CONF
CONF.register_opts(health_mgr_opts)


class HealthManager(service.Service):

    def __init__(self, engine_service, topic, version):
        super(HealthManager, self).__init__()

        self.TG = threadgroup.ThreadGroup()
        self.engine_id = engine_service.engine_id
        self.topic = topic
        self.version = version
        self.ctx = context.get_admin_context()
        self.periodic_interval_max = CONF.periodic_interval_max
        self.rpc_client = rpc_client.EngineClient()
        self.rt = {
            'registries': [],
        }

    def _idle_task(self):
        pass

    def _periodic_check(self, cluster_id=None):
        """Tasks to be run at a periodic interval."""
        self.rpc_client.cluster_check(self.ctx, cluster_id)

    def start_periodic_tasks(self):
        """Tasks to be run at a periodic interval."""
        # TODO(anyone): start timers to check clusters
        # - get clusters that needs health management from DB
        # - get their checking options
        #   * if it is about node status polling, add a timer to trigger its
        #     do_check logic
        #   * if it is about listening to message queue, start a thread to
        #     listen events targeted at that cluster
        self.TG.add_timer(cfg.CONF.periodic_interval, self._idle_task)

        for registry in self.registries:
            if registry.get('check_type') == 'NODE_STATUS_POLLING':
                interval = min(registry.get('interval'),
                               self.periodic_interval_max)
                timer = self.TG.add_timer(interval, self._periodic_check, None,
                                          registry.get('cluster_id'))
                registry['timer'] = timer

    def start(self):
        super(HealthManager, self).start()
        self.target = oslo_messaging.Target(server=self.engine_id,
                                            topic=self.topic,
                                            version=self.version)
        server = rpc_messaging.get_rpc_server(self.target, self)
        server.start()
        self._load_runtime_registry()
        self.start_periodic_tasks()

    def _load_runtime_registry(self):
        db_registries = db_api.registry_claim(self.ctx, self.engine_id)

        for registry in db_registries:
            reg_cap = {
                'cluster_id': registry.cluster_id,
                'check_type': registry.check_type,
                'interval': registry.interval,
                'params': registry.params,
                'timer': None
            }
            self.rt['registries'].append(reg_cap)

    @property
    def registries(self):
        return self.rt['registries']

    def stop(self):
        self.TG.stop_timers()
        super(HealthManager, self).stop()

    def listening(self, ctx):
        """Respond to confirm that the rpc service is still alive."""
        return True

    def register_cluster(self, ctx, cluster_id, check_type, interval=None,
                         params=None):
        """Register cluster for health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be checked.
        :param check_type: A string indicating the type of checks.
        :param interval: An optional integer indicating the length of checking
                         periods in seconds.
        :param \*\*params: Other parameters for the health check.
        :return: None
        """
        params = params or {}
        registry = db_api.registry_create(ctx, cluster_id, check_type,
                                          interval, params, self.engine_id)

        timer = None
        if check_type == 'NODE_STATUS_POLLING':
            real_interval = min(interval, self.periodic_interval_max)
            timer = self.TG.add_timer(real_interval, self._periodic_check,
                                      None, cluster_id)

        reg_cap = {
            'cluster_id': registry.cluster_id,
            'check_type': registry.check_type,
            'interval': registry.interval,
            'params': registry.params,
            'timer': timer

        }
        self.rt['registries'].append(reg_cap)

    def unregister_cluster(self, ctx, cluster_id):
        """Unregister a cluster from health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluste to be unregistered.
        :return: None
        """
        for i in range(len(self.rt['registries']) - 1, -1, -1):
            registry = self.rt['registries'][i]
            if registry.get('cluster_id') == cluster_id:
                timer = registry.get('timer')
                timer.stop()
                self.TG.timer_done(timer)
                self.rt['registries'].pop(i)
        db_api.registry_delete(ctx, cluster_id)


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


def list_opts():
    yield None, health_mgr_opts
