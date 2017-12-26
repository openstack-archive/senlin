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
import oslo_messaging as messaging

from senlin.common import context
from senlin.engine.notifications import base
from senlin import objects
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class NovaNotificationEndpoint(base.Endpoints):

    VM_FAILURE_EVENTS = {
        'compute.instance.pause.end': 'PAUSE',
        'compute.instance.power_off.end': 'POWER_OFF',
        'compute.instance.rebuild.error': 'REBUILD',
        'compute.instance.shutdown.end': 'SHUTDOWN',
        'compute.instance.soft_delete.end': 'SOFT_DELETE',
    }

    def __init__(self, project_id, engine_id, recover_action):
        self.filter_rule = messaging.NotificationFilter(
            publisher_id='^compute.*',
            event_type='^compute\.instance\..*',
            context={'project_id': '^%s$' % project_id})
        self.project_id = project_id
        self.engine_id = engine_id
        self.rpc = rpc_client.EngineClient()
        self.recover_action = recover_action
        self.exchange = cfg.CONF.health_manager.nova_control_exchange
        self.target = messaging.Target(topic='versioned_notifications',
                                       exchange=self.exchange)

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        meta = payload['metadata']
        cluster_id = meta.get('cluster_id')
        if not cluster_id:
            return

        if event_type not in self.VM_FAILURE_EVENTS:
            return

        ctx = context.get_service_context(project=self.project_id,
                                          user=payload['user_id'])
        enabled = self._check_registry_status(ctx, self.engine_id, cluster_id)
        if enabled is False:
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
