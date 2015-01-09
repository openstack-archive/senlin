#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo.config import cfg
from oslo import messaging
from osprofiler import profiler

from senlin.common import context
from senlin.common.i18n import _LI
from senlin.common import messaging as rpc_messaging
from senlin.engine import scheduler
from senlin.engine import engine_service
from senlin.openstack.common import log as logging
from senlin.openstack.common import service
from senlin.rpc import api as rpc_api

LOG = logging.getLogger(__name__)


@profiler.trace_cls("rpc")
class Dispatcher(service.Service):
    '''
    Listen on an AMQP queue named for the engine.  Receive
    notification from engine services and schedule actions.
    '''

    OPERATIONS = (NEW_ACTION, CANCEL_ACTION, STOP) = (
        'new_action', 'cancel_action', 'stop')

    def __init__(self, engine_id, topic, version, thread_group_mgr):
        super(Dispatcher, self).__init__()
        self.TG = thread_group_mgr
        self.engine_id = engine_id
        self.topic = topic
        self.version = version

    def start(self):
        super(Dispatcher, self).start()
        self.target = messaging.Target(server=self.engine_id,
                                       topic=self.topic,
                                       version=self.version)
        server = rpc_messaging.get_rpc_server(self.target, self)
        server.start()

    def listening(self, ctxt):
        '''
        Respond affirmatively to confirm that the engine performing the
        action is still alive.
        '''
        return True

    def new_action(self, ctxt, action_id=None):
        '''New action has been ready, try to schedule it'''
        scheduler.start_action(ctxt, action_id, self.engine_id, self.TG)

    def cancel_action(self, ctxt, action_id):
        '''Cancel an action.'''
        scheduler.cancel_action(ctxt, action_id)

    def suspend_action(self, ctxt, action_id):
        '''Suspend an action.'''
        scheduler.suspend_action(ctxt, action_id)

    def resume_action(self, ctxt, action_id):
        '''Resume an action.'''
        scheduler.resume_action(ctxt, action_id)

    def stop(self):
        super(Dispatcher, self).stop()
        # Wait for all action threads to be finished
        LOG.info(_LI("Stopping all action threads of engine %s"),
                 self.engine_id)
        # Stop ThreadGroup gracefully
        self.TG.stop(True)
        LOG.info(_LI("All action threads have been finished"))
        # Notify dispatcher to stop all action threads it started.
        notify(context, self.STOP, self.engine_id)

        # Terminate the engine process
        LOG.info(_LI("All threads were gone, terminating engine"))
        super(engine_service.EngineService, self).stop()


def notify(self, cnxt, call, engine_id, *args, **kwargs):
    """
    Send notification to dispatcher

    :param cnxt: rpc request context
    :param call: remote method want to call
    :param engine_id: dispatcher want to notify, if None, broadcast
    """
    timeout = cfg.CONF.engine_life_check_timeout
    client = rpc_messaging.get_rpc_client(
        version=engine_service.EngineService.RPC_API_VERSION)

    if engine_id:
        # Notify specific dispatcher identified by engine_id
        cctxt = client.prepare(
            version=engine_service.EngineService.RPC_API_VERSION,
            timeout=timeout,
            topic=rpc_api.ENGINE_DISPATCHER_TOPIC,
            server=engine_id)
    else:
        # Broadcast to all disptachers
        cctxt = client.prepare(
            version=engine_service.EngineService.RPC_API_VERSION,
            timeout=timeout,
            topic=rpc_api.ENGINE_DISPATCHER_TOPIC,
            fanout=True)

    try:
        cctxt.call(cnxt, call, *args, **kwargs)
    except messaging.MessagingTimeout:
        return False
