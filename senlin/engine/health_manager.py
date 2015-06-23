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

'''
Health Manager class.

Health Manager is responsible for monitoring the health of the clusters and
take corresponding actions to recover the clusters based on the pre-defined
health policies.
'''

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service

from senlin.common import consts
from senlin.common import messaging as rpc_messaging

health_mgr_opts = [
    cfg.IntOpt('periodic_interval_max',
               default=60,
               help='Seconds between periodic tasks to be called'),
    cfg.BoolOpt('periodic_enable',
                default=True,
                help='Enable periodic tasks'),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=60,
               help='Range of seconds to randomly delay when starting the'
                    ' periodic task scheduler to reduce stampeding.'
                    ' (Disable by setting to 0)'),
]

CONF = cfg.CONF
CONF.register_opts(health_mgr_opts)

LOG = logging.getLogger(__name__)


class Health_Manager(service.Service):

    def __init__(self, engine_service, topic, version, thread_group_mgr):
        super(Health_Manager, self).__init__()
        self.threadgroup = thread_group_mgr
        self.engine_id = engine_service.engine_id
        self.topic = topic
        self.version = version

        # params for periodic running task
        self.periodic_interval_max = CONF.periodic_interval_max
        self.periodic_enable = CONF.periodic_enable
        self.periodic_fuzzy_delay = CONF.periodic_fuzzy_delay

    def periodic_tasks(self, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        # TODO(anyone): iterate clusters and call their periodic_tasks
        return self.periodic_interval_max

    def start(self):
        super(Health_Manager, self).start()
        self.target = oslo_messaging.Target(server=self.engine_id,
                                            topic=self.topic,
                                            version=self.version)
        server = rpc_messaging.get_rpc_server(self.target, self)
        server.start()

        if self.periodic_enable:
            # if self.periodic_fuzzy_delay:
            #    initial_delay = random.randint(0, self.periodic_fuzzy_delay)
            # else:
            #    initial_delay = None

            self.threadgroup.add_timer(self.periodic_interval_max,
                                       self.periodic_tasks)

    def listening(self, context):
        '''Respond to confirm that the engine is still alive.'''
        return True

    def stop(self):
        super(Health_Manager, self).stop()


def notify(context, method, engine_id, *args, **kwargs):
    '''Send notification to dispatcher

    :param context: rpc request context
    :param method: remote method to call
    :param engine_id: dispatcher to notify; broadcast if value is None
    '''

    timeout = cfg.CONF.engine_life_check_timeout
    client = rpc_messaging.get_rpc_client(version=consts.RPC_API_VERSION)

    if engine_id:
        # Notify specific dispatcher identified by engine_id
        call_context = client.prepare(
            version=consts.RPC_API_VERSION,
            timeout=timeout,
            topic=consts.ENGINE_DISPATCHER_TOPIC,
            server=engine_id)
    else:
        # Broadcast to all disptachers
        call_context = client.prepare(
            version=consts.RPC_API_VERSION,
            timeout=timeout,
            topic=consts.ENGINE_DISPATCHER_TOPIC)

    try:
        call_context.call(context, method, *args, **kwargs)
        return True
    except oslo_messaging.MessagingTimeout:
        return False
