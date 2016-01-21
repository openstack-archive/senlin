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

import datetime
import mock
import uuid

from oslo_utils import timeutils

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc_messaging
from senlin.db import api as db_api
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

    @mock.patch.object(db_api, 'service_create')
    @mock.patch.object(db_api, 'service_update')
    @mock.patch.object(db_api, 'service_get')
    def test_service_manage_report(self, mock_get, mock_update,
                                   mock_create, mock_msg_cls,
                                   mock_hm_cls, mock_disp_cls):
        mock_get.side_effect = [
            None,
            mock.Mock()
        ]
        self.eng.service_manage_report()
        expected_args = dict(host=self.eng.host,
                             binary='senlin-engine',
                             service_id=self.eng.engine_id,
                             topic=self.eng.topic)
        mock_create.assert_called_once_with(**expected_args)
        self.eng.service_manage_report()
        self.assertTrue(mock_update.called)

    @mock.patch.object(db_api, 'service_get_all')
    @mock.patch.object(db_api, 'service_delete')
    def test_service_manage_report_cleanup(self, mock_delete, mock_get_all,
                                           mock_msg_cls, mock_hm_cls,
                                           mock_disp_cls):
        ages_a_go = timeutils.utcnow() - datetime.timedelta(
            seconds=4000)
        mock_get_all.return_value = [{'id': 'foo',
                                      'updated_at': ages_a_go}]
        self.eng.service_manage_cleanup()
        mock_delete.assert_called_once_with('foo')
