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

from oslo_config import cfg
from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging as rpc_messaging
from senlin.engine import service
from senlin.objects import service as service_obj
from senlin.tests.unit.common import base


@mock.patch('senlin.engine.dispatcher.Dispatcher')
@mock.patch('senlin.engine.health_manager.HealthManager')
@mock.patch('oslo_messaging.Target')
class EngineBasicTest(base.SenlinTestCase):

    def setUp(self):

        super(EngineBasicTest, self).setUp()
        self.eng = service.EngineService('host-a', 'topic-a')
        self.fake_id = '4db0a14c-dc10-4131-8ed6-7573987ce9b0'
        self.gen_id = self.patchobject(uuidutils, 'generate_uuid',
                                       return_value=self.fake_id)

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
        self.assertEqual(self.fake_id, self.eng.engine_id)
        self.assertIsNotNone(self.eng.TG)

        mock_disp_cls.assert_called_once_with(self.eng,
                                              self.eng.dispatcher_topic,
                                              consts.RPC_API_VERSION,
                                              self.eng.TG)
        self.assertEqual(mock_disp, self.eng.dispatcher)
        mock_disp.start.assert_called_once_with()

        mock_hm_cls.assert_called_once_with(self.eng,
                                            self.eng.health_mgr_topic,
                                            consts.RPC_API_VERSION)
        self.assertEqual(mock_hm, self.eng.health_mgr)
        mock_hm.start.assert_called_once_with()

        mock_msg_cls.assert_called_once_with(version=consts.RPC_API_VERSION,
                                             server=self.eng.host,
                                             topic=self.eng.topic)

        self.get_rpc.assert_called_once_with(mock_target, self.eng,
                                             serializer=mock.ANY)

        self.assertEqual(self.fake_rpc_server, self.eng._rpc_server)
        self.fake_rpc_server.start.assert_called_once_with()

    @mock.patch.object(service_obj.Service, 'delete')
    def test_engine_stop(self, mock_delete, mock_msg_cls, mock_hm_cls,
                         mock_disp_cls):
        mock_disp = mock_disp_cls.return_value
        mock_hm = mock_hm_cls.return_value
        self.eng.start()

        self.eng.stop()

        self.fake_rpc_server.stop.assert_called_once_with()
        self.fake_rpc_server.wait.assert_called_once_with()

        mock_disp.stop.assert_called_once_with()
        mock_hm.stop.assert_called_once_with()

        mock_delete.assert_called_once_with(self.fake_id)

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


class EngineStatusTest(base.SenlinTestCase):

    def setUp(self):
        super(EngineStatusTest, self).setUp()
        self.eng = service.EngineService('host-a', 'topic-a')
        fake_id = '4db0a14c-dc10-4131-8ed6-7573987ce9b0'
        self.gen_id = self.patchobject(uuidutils, 'generate_uuid',
                                       return_value=fake_id)

        self.fake_rpc_server = mock.Mock()
        self.get_rpc = self.patchobject(rpc_messaging, 'get_rpc_server',
                                        return_value=self.fake_rpc_server)

    @mock.patch.object(service_obj.Service, 'update')
    def test_service_manage_report_update(self, mock_update):
        mock_update.return_value = mock.Mock()
        self.eng.service_manage_report()
        mock_update.assert_called_once_with(mock.ANY, self.eng.engine_id)

    @mock.patch.object(service_obj.Service, 'gc_by_engine')
    @mock.patch.object(service_obj.Service, 'get_all')
    @mock.patch.object(service_obj.Service, 'delete')
    def test__service_manage_cleanup(self, mock_delete, mock_get_all, mock_gc):
        delta = datetime.timedelta(seconds=2 * cfg.CONF.periodic_interval)
        ages_a_go = timeutils.utcnow(True) - delta
        mock_get_all.return_value = [{'id': 'foo', 'updated_at': ages_a_go}]
        self.eng._service_manage_cleanup()
        mock_delete.assert_called_once_with('foo')
        mock_gc.assert_called_once_with('foo')
