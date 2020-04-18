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

from unittest import mock

from oslo_config import cfg
import oslo_messaging
from oslo_utils import uuidutils

from senlin.common import consts
from senlin.common import context
from senlin.engine import health_manager as hm
from senlin.health_manager import service
from senlin.objects import health_registry as hr
from senlin.objects import service as obj_service
from senlin.objects import service as service_obj
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestHealthManager(base.SenlinTestCase):
    def setUp(self):
        super(TestHealthManager, self).setUp()
        self.context = utils.dummy_context()

        self.service_id = '4db0a14c-dc10-4131-8ed6-7573987ce9b0'
        self.tg = mock.Mock()
        self.topic = consts.HEALTH_MANAGER_TOPIC

        self.svc = service.HealthManagerService('HOST', self.topic)
        self.svc.service_id = self.service_id
        self.svc.tg = self.tg

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers(self, mock_service_init):
        service.HealthManagerService('HOST', self.topic)

        mock_service_init.assert_called_once_with(1000)

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers_override(self, mock_service_init):
        cfg.CONF.set_override('threads', 100, group='health_manager')

        service.HealthManagerService('HOST', self.topic)

        mock_service_init.assert_called_once_with(100)

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers_override_legacy(self, mock_service_init):
        cfg.CONF.set_override('health_manager_thread_pool_size', 101)

        service.HealthManagerService('HOST', self.topic)

        mock_service_init.assert_called_once_with(101)

    def test_init(self):
        self.assertEqual(self.service_id, self.svc.service_id)
        self.assertEqual(self.tg, self.svc.tg)
        self.assertEqual(self.topic, self.svc.topic)

        self.assertEqual(consts.RPC_API_VERSION, self.svc.version)

    @mock.patch.object(uuidutils, 'generate_uuid')
    @mock.patch.object(oslo_messaging, 'get_rpc_server')
    @mock.patch.object(obj_service.Service, 'create')
    def test_service_start(self, mock_service_create, mock_rpc_server,
                           mock_uuid):
        service_uuid = '4db0a14c-dc10-4131-8ed6-7573987ce9b1'
        mock_uuid.return_value = service_uuid

        self.svc.start()

        mock_uuid.assert_called_once()
        mock_service_create.assert_called_once()
        self.svc.server.start.assert_called_once()

        self.assertEqual(service_uuid, self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'delete')
    def test_service_stop(self, mock_delete):
        self.svc.server = mock.Mock()

        self.svc.stop()

        self.svc.server.stop.assert_called_once()
        self.svc.server.wait.assert_called_once()

        mock_delete.assert_called_once_with(self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'delete')
    def test_service_stop_not_yet_started(self, mock_delete):
        self.svc.server = None

        self.svc.stop()

        mock_delete.assert_called_once_with(self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'update')
    def test_service_manage_report_update(self, mock_update):
        mock_update.return_value = mock.Mock()
        self.svc.service_manage_report()
        mock_update.assert_called_once_with(mock.ANY,
                                            self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'update')
    def test_service_manage_report_with_exception(self, mock_update):
        mock_update.side_effect = Exception('blah')
        self.svc.service_manage_report()
        self.assertEqual(mock_update.call_count, 1)

    def test_listening(self):
        self.assertTrue(self.svc.listening(self.context))

    def test_task(self):
        self.svc.health_registry = mock.Mock()
        self.svc.task()
        self.svc.health_registry.load_runtime_registry.assert_called_once_with(
        )

    def test_task_with_exception(self):
        self.svc.health_registry = mock.Mock()
        self.svc.health_registry.load_runtime_registry.side_effect = Exception(
            'blah'
        )
        self.svc.task()
        self.svc.health_registry.load_runtime_registry.assert_called_once_with(
        )

    def test_enable_cluster(self):
        self.svc.health_registry = mock.Mock()
        self.svc.enable_cluster(self.context, 'CID')
        self.svc.health_registry.enable_cluster.assert_called_once_with(
            'CID')

    def test_disable_cluster(self):
        self.svc.health_registry = mock.Mock()
        self.svc.disable_cluster(self.context, 'CID')
        self.svc.health_registry.disable_cluster.assert_called_once_with(
            'CID')

    def test_register_cluster(self):
        self.svc.health_registry = mock.Mock()
        self.svc.register_cluster(self.context, 'CID', 60, 160, {}, True)
        self.svc.health_registry.register_cluster.assert_called_once_with(
            cluster_id='CID',
            enabled=True,
            interval=60,
            node_update_timeout=160,
            params={})

    def test_unregister_cluster(self):
        self.svc.health_registry = mock.Mock()
        self.svc.unregister_cluster(self.context, 'CID')
        self.svc.health_registry.unregister_cluster.assert_called_once_with(
            'CID')

    @mock.patch.object(context, 'get_admin_context')
    @mock.patch.object(hr.HealthRegistry, 'get')
    def test_get_manager_engine(self, mock_get, mock_ctx):
        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        registry = mock.Mock(engine_id='fake')
        mock_get.return_value = registry

        result = hm.get_manager_engine('CID')

        self.assertEqual(result, 'fake')

        mock_get.assert_called_once_with(ctx, 'CID')
        self.assertTrue(mock_ctx.called)

    @mock.patch.object(context, 'get_admin_context')
    @mock.patch.object(hr.HealthRegistry, 'get')
    def test_get_manager_engine_none(self, mock_get, mock_ctx):
        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        mock_get.return_value = None

        result = hm.get_manager_engine('CID')

        self.assertIsNone(result)

        mock_get.assert_called_once_with(ctx, 'CID')
        self.assertTrue(mock_ctx.called)
