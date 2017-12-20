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


class HeatNotificationEndpoint(base.Endpoints):

    STACK_FAILURE_EVENTS = {
        'orchestration.stack.delete.end': 'DELETE',
    }

    def __init__(self, project_id, engine_id, recover_action):
        self.filter_rule = messaging.NotificationFilter(
            publisher_id='^orchestration.*',
            event_type='^orchestration\.stack\..*',
            context={'project_id': '^%s$' % project_id})
        self.project_id = project_id
        self.engine_id = engine_id
        self.rpc = rpc_client.EngineClient()
        self.recover_action = recover_action
        self.exchange = cfg.CONF.health_manager.heat_control_exchange
        self.target = messaging.Target(topic='notifications',
                                       exchange=self.exchange)

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
                if start == 0 and tag[11:]:
                    cluster_id = tag[11:]
            if node_id is None:
                start = tag.find('cluster_node_id')
                if start == 0:
                    node_id = tag[16:]

        if cluster_id is None or node_id is None:
            return

        ctx = context.get_service_context(project=self.project_id,
                                          user=payload['user_identity'])
        enabled = self._check_registry_status(ctx, self.engine_id, cluster_id)
        if enabled is False:
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
        req = objects.NodeRecoverRequest(identity=node_id, params=params)
        self.rpc.call(ctx, 'node_recover', req)
