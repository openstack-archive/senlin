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

import uuid

import mock

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc_messaging
from senlin.engine import service
from senlin.tests.unit.common import base


@mock.patch('senlin.engine.dispatcher.Dispatcher')
@mock.patch('senlin.engine.health_manager.Health_Manager')
@mock.patch('oslo_messaging.Target')
class EngineBasicTest(base.SenlinTestCase):

    def setUp(self):

        super(EngineBasicTest, self).setUp()
        self.eng = service.EngineService('host-a', 'topic-a')
        self.gen_id = self.patchobject(uuid, 'uuid4', return_value='1234')

        self.fake_rpc_server = mock.Mock()
        self.get_rpc = self.patchobject(rpc_messaging, 'get_rpc_server',
                                        return_value=self.fake_rpc_server)

    # TODO(Yanyan Hu): Remove this decorator after DB session related
    # work is done.
    @mock.patch.object(context, 'RequestContext')
    def test_engine_start(self, mock_context, mock_msg_cls, mock_hm_cls,
                          mock_disp_cls):

        mock_disp = mock_disp_cls.return_value
        mock_hm = mock_hm_cls.return_value
        mock_target = mock_msg_cls.return_value

        self.eng.start()

        self.gen_id.assert_called_once_with()
        self.assertEqual('1234', self.eng.engine_id)
        self.assertIsNotNone(self.eng.TG)

        mock_disp_cls.assert_called_once_with(self.eng,
                                              self.eng.dispatcher_topic,
                                              consts.RPC_API_VERSION,
                                              self.eng.TG)
        self.assertEqual(mock_disp, self.eng.dispatcher)
        mock_disp.start.assert_called_once_with()

        mock_hm_cls.assert_called_once_with(self.eng,
                                            self.eng.health_mgr_topic,
                                            consts.RPC_API_VERSION,
                                            self.eng.TG)
        self.assertEqual(mock_hm, self.eng.health_mgr)
        mock_hm.start.assert_called_once_with()

        mock_msg_cls.assert_called_once_with(version=consts.RPC_API_VERSION,
                                             server=self.eng.host,
                                             topic=self.eng.topic)
        self.assertEqual(mock_target, self.eng.target)

        self.get_rpc.assert_called_once_with(mock_target, self.eng)
        self.assertEqual(self.fake_rpc_server, self.eng._rpc_server)
        self.fake_rpc_server.start.assert_called_once_with()

    def test_engine_stop(self, mock_msg_cls, mock_hm_cls, mock_disp_cls):
        mock_disp = mock_disp_cls.return_value
        mock_hm = mock_hm_cls.return_value
        self.eng.start()

        self.eng.stop()

        self.fake_rpc_server.stop.assert_called_once_with()
        self.fake_rpc_server.wait.assert_called_once_with()

        mock_disp.stop.assert_called_once_with()
        mock_hm.stop.assert_called_once_with()

    def test_engine_stop_with_exception(self, mock_msg_cls, mock_hm_cls,
                                        mock_disp_cls):
        mock_disp = mock_disp_cls.return_value
        mock_hm = mock_hm_cls.return_value
        self.fake_rpc_server.wait.side_effect = Exception('blah')

        self.eng.start()
        self.eng.stop()

        # on exception, both methods are still invoked
        self.fake_rpc_server.stop.assert_called_once_with()
        self.fake_rpc_server.wait.assert_called_once_with()

        mock_disp.stop.assert_called_once_with()
        mock_hm.stop.assert_called_once_with()
