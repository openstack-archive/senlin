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
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_utils import timeutils
from osprofiler import profiler

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc
from senlin.common import service
from senlin.engine import health_manager

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@profiler.trace_cls("rpc")
class HealthManagerService(service.Service):
    def __init__(self, host, topic):
        super(HealthManagerService, self).__init__(
            self.service_name, host, topic,
            threads=CONF.health_manager.threads
        )
        self.version = consts.RPC_API_VERSION

        self.ctx = context.get_admin_context()

        # The following are initialized here and will be assigned in start()
        # which happens after the fork when spawning multiple worker processes
        self.health_registry = None
        self.target = None
        self.cleanup_task_timer = None

    @property
    def service_name(self):
        return 'senlin-health-manager'

    def start(self):
        super(HealthManagerService, self).start()

        self.health_registry = health_manager.RuntimeHealthRegistry(
            ctx=self.ctx, engine_id=self.service_id,
            thread_group=self.tg
        )
        self.target = oslo_messaging.Target(server=self.service_id,
                                            topic=self.topic,
                                            version=self.version)
        self.server = rpc.get_rpc_server(self.target, self)
        self.server.start()

        self.tg.add_dynamic_timer(self.task, None, cfg.CONF.periodic_interval)
        self.cleanup_task_timer = self.tg.add_timer(
            CONF.health_manager.cleanup_interval, self.cleanup_task,
            initial_delay=CONF.health_manager.cleanup_interval
        )

    def stop(self, graceful=False):
        if self.cleanup_task_timer:
            self.cleanup_task_timer.stop()
            self.cleanup_task_timer = None
        if self.server:
            self.server.stop()
            self.server.wait()
        super(HealthManagerService, self).stop(graceful)

    def task(self):
        """Task that is queued on the health manager thread group.

        The task is here so that the service always has something to wait()
        on, or else the process will exit.
        """
        start_time = timeutils.utcnow(True)

        try:
            self.health_registry.load_runtime_registry()
        except Exception as ex:
            LOG.error("Failed when loading runtime for health manager: %s", ex)
        return health_manager.chase_up(
            start_time, cfg.CONF.periodic_interval, name='Health manager task'
        )

    def cleanup_task(self):
        LOG.debug('Running cleanup task')
        try:
            self.health_registry.cleanup_orphaned_healthchecks()
        except Exception as ex:
            LOG.error("Failed to run cleanup tasks for health manager: %s", ex)

    def listening(self, ctx):
        """Respond to confirm that the rpc service is still alive."""
        return True

    def register_cluster(self, ctx, cluster_id, interval=None,
                         node_update_timeout=None, params=None,
                         enabled=True):
        """Register a cluster for health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be unregistered.
        :param interval: Interval of the health check.
        :param node_update_timeout: Time to wait before declairing a node
        unhealthy.
        :param params: Params to be passed to health check.
        :param enabled: Set's if the health check is enabled or disabled.
        :return: None
        """
        LOG.info("Registering health check for cluster %s.", cluster_id)
        self.health_registry.register_cluster(
            cluster_id=cluster_id,
            interval=interval,
            node_update_timeout=node_update_timeout,
            params=params,
            enabled=enabled)

    def unregister_cluster(self, ctx, cluster_id):
        """Unregister a cluster from health checking.

        :param ctx: The context of notify request.
        :param cluster_id: The ID of the cluster to be unregistered.
        :return: None
        """
        LOG.info("Unregistering health check for cluster %s.", cluster_id)
        self.health_registry.unregister_cluster(cluster_id)

    def enable_cluster(self, ctx, cluster_id, params=None):
        self.health_registry.enable_cluster(cluster_id)

    def disable_cluster(self, ctx, cluster_id, params=None):
        self.health_registry.disable_cluster(cluster_id)
