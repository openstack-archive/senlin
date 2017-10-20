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
from oslo_context import context as oslo_context
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service

from senlin.common import consts
from senlin.common import messaging

LOG = logging.getLogger(__name__)

OPERATIONS = (
    START_ACTION, CANCEL_ACTION, STOP
) = (
    'start_action', 'cancel_action', 'stop'
)


class Dispatcher(service.Service):
    """RPC server for dispatching actions.

    Receive notification from engine services and schedule actions.
    """
    def __init__(self, engine_service, topic, version, thread_group_mgr):
        super(Dispatcher, self).__init__()
        self.TG = thread_group_mgr
        self.engine_id = engine_service.engine_id
        self.topic = topic
        self.version = version

    def start(self):
        """Start the dispatcher.

        Note that dispatcher is an engine-internal server, we are not using
        versioned object for parameter passing.
        """
        super(Dispatcher, self).start()
        self.target = oslo_messaging.Target(server=self.engine_id,
                                            topic=self.topic,
                                            version=self.version)

        server = messaging.get_rpc_server(self.target, self)
        server.start()

    def listening(self, ctxt):
        '''Respond affirmatively to confirm that engine is still alive.'''
        return True

    def start_action(self, ctxt, action_id=None):
        self.TG.start_action(self.engine_id, action_id)

    def cancel_action(self, ctxt, action_id):
        '''Cancel an action.'''
        self.TG.cancel_action(action_id)

    def suspend_action(self, ctxt, action_id):
        '''Suspend an action.'''
        self.TG.suspend_action(action_id)

    def resume_action(self, ctxt, action_id):
        '''Resume an action.'''
        self.TG.resume_action(action_id)

    def stop(self):
        super(Dispatcher, self).stop()
        # Wait for all action threads to be finished
        LOG.info("Stopping all action threads of engine %s",
                 self.engine_id)
        # Stop ThreadGroup gracefully
        self.TG.stop(True)
        LOG.info("All action threads have been finished")


def notify(method, engine_id=None, **kwargs):
    """Send notification to dispatcher.

    Note that dispatcher is an engine internal communication. We are not using
    versioned object serialization at this level.

    :param method: remote method to call
    :param engine_id: dispatcher to notify; None implies broadcast
    """
    client = messaging.get_rpc_client(consts.DISPATCHER_TOPIC, cfg.CONF.host)

    if engine_id:
        # Notify specific dispatcher identified by engine_id
        call_context = client.prepare(server=engine_id)
    else:
        # Broadcast to all disptachers
        call_context = client.prepare(fanout=True)

    try:
        # We don't use ctext parameter in action progress
        # actually. But since RPCClient.call needs this param,
        # we use oslo current context here.
        call_context.cast(oslo_context.get_current(), method, **kwargs)
        return True
    except oslo_messaging.MessagingTimeout:
        return False


def start_action(engine_id=None, **kwargs):
    return notify(START_ACTION, engine_id, **kwargs)
