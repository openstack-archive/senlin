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

import mock
from oslo_config import cfg
from oslo_context import context
import oslo_messaging

from senlin.common import consts
from senlin.common import messaging
from senlin.engine import dispatcher
from senlin.engine import scheduler
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestDispatcher(base.SenlinTestCase):

    def setUp(self):
        super(TestDispatcher, self).setUp()

        self.context = utils.dummy_context()

        self.thm = scheduler.ThreadGroupManager()
        self.svc = service.EngineService('HOST', 'TOPIC')
        self.svc.engine_id = '1234'

    def test_init(self):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)

        self.assertEqual(self.thm, disp.TG)
        self.assertEqual('1234', disp.engine_id)
        self.assertEqual('TOPIC', disp.topic)
        self.assertEqual('1', disp.version)

    @mock.patch.object(messaging, 'get_rpc_server')
    @mock.patch.object(oslo_messaging, 'Target')
    def test_start(self, mock_target, mock_server):
        mock_server.return_value = mock.Mock()
        mock_target.return_value = mock.Mock()

        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        disp.start()

        mock_target.assert_called_once_with(server='1234', topic='TOPIC',
                                            version='1')
        the_target = mock_target.return_value
        mock_server.assert_called_once_with(the_target, disp)

        the_server = mock_server.return_value
        the_server.start.assert_called_once_with()

    def test_listening(self):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        result = disp.listening(self.context)
        self.assertTrue(result)

    @mock.patch.object(scheduler.ThreadGroupManager, 'start_action')
    def test_start_action(self, mock_start):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        disp.start_action(self.context, action_id='FOO')

        mock_start.assert_called_once_with('1234', 'FOO')
        mock_start.reset_mock()

        disp.start_action(self.context)
        mock_start.assert_called_once_with('1234', None)

    @mock.patch.object(scheduler.ThreadGroupManager, 'cancel_action')
    def test_cancel_action(self, mock_cancel):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        disp.cancel_action(self.context, action_id='FOO')

        mock_cancel.assert_called_once_with('FOO')

    @mock.patch.object(scheduler.ThreadGroupManager, 'suspend_action')
    def test_suspend_action(self, mock_suspend):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        disp.suspend_action(self.context, action_id='FOO')

        mock_suspend.assert_called_once_with('FOO')

    @mock.patch.object(scheduler.ThreadGroupManager, 'resume_action')
    def test_resume_action(self, mock_resume):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        disp.resume_action(self.context, action_id='FOO')

        mock_resume.assert_called_once_with('FOO')

    @mock.patch.object(scheduler.ThreadGroupManager, 'stop')
    def test_stop(self, mock_stop):
        disp = dispatcher.Dispatcher(self.svc, 'TOPIC', '1', self.thm)
        disp.stop()

        mock_stop.assert_called_once_with(True)

    @mock.patch.object(context, 'get_current')
    @mock.patch.object(messaging, 'get_rpc_client')
    def test_notify_broadcast(self, mock_rpc, mock_get_current):
        cfg.CONF.set_override('host', 'HOSTNAME')
        fake_ctx = mock.Mock()
        mock_get_current.return_value = fake_ctx
        mock_rpc.return_value = mock.Mock()

        dispatcher.notify('METHOD')

        mock_rpc.assert_called_once_with(consts.DISPATCHER_TOPIC, 'HOSTNAME')
        mock_client = mock_rpc.return_value
        mock_client.prepare.assert_called_once_with(fanout=True)

        mock_context = mock_client.prepare.return_value
        mock_context.cast.assert_called_once_with(fake_ctx, 'METHOD')

    @mock.patch.object(context, 'get_current')
    @mock.patch.object(messaging, 'get_rpc_client')
    def test_notify_single_server(self, mock_rpc, mock_get_current):
        cfg.CONF.set_override('host', 'HOSTNAME')
        fake_ctx = mock.Mock()
        mock_get_current.return_value = fake_ctx
        mock_rpc.return_value = mock.Mock()

        result = dispatcher.notify('METHOD', 'FAKE_ENGINE')

        self.assertTrue(result)
        mock_rpc.assert_called_once_with(consts.DISPATCHER_TOPIC, 'HOSTNAME')
        mock_client = mock_rpc.return_value
        mock_client.prepare.assert_called_once_with(server='FAKE_ENGINE')

        mock_context = mock_client.prepare.return_value
        mock_context.cast.assert_called_once_with(fake_ctx, 'METHOD')

    @mock.patch.object(messaging, 'get_rpc_client')
    def test_notify_timeout(self, mock_rpc):
        cfg.CONF.set_override('host', 'HOSTNAME')
        mock_rpc.return_value = mock.Mock()
        mock_client = mock_rpc.return_value
        mock_context = mock_client.prepare.return_value
        mock_context.cast.side_effect = oslo_messaging.MessagingTimeout

        result = dispatcher.notify('METHOD')

        self.assertFalse(result)
        mock_rpc.assert_called_once_with(consts.DISPATCHER_TOPIC, 'HOSTNAME')
        mock_client.prepare.assert_called_once_with(fanout=True)

        mock_context.cast.assert_called_once_with(mock.ANY, 'METHOD')

    @mock.patch.object(dispatcher, 'notify')
    def test_start_action_function(self, mock_notify):
        dispatcher.start_action(engine_id='FAKE_ENGINE')

        mock_notify.assert_called_once_with(dispatcher.START_ACTION,
                                            'FAKE_ENGINE')
