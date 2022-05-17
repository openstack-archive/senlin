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
from unittest import mock

import eventlet
from oslo_config import cfg
import oslo_messaging
from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin.common import consts
from senlin.conductor import service
from senlin.objects.requests import build_info as vorb
from senlin.objects import service as service_obj
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ConductorTest(base.SenlinTestCase):
    def setUp(self):
        super(ConductorTest, self).setUp()
        self.context = utils.dummy_context()

        self.service_id = '4db0a14c-dc10-4131-8ed6-7573987ce9b0'
        self.tg = mock.Mock()
        self.topic = consts.HEALTH_MANAGER_TOPIC

        self.svc = service.ConductorService('HOST', self.topic)
        self.svc.service_id = self.service_id
        self.svc.tg = self.tg

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers(self, mock_service_init):
        service.ConductorService('HOST', self.topic)

        mock_service_init.assert_called_once_with(1000)

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers_override(self, mock_service_init):
        cfg.CONF.set_override('threads', 100, group='conductor')

        service.ConductorService('HOST', self.topic)

        mock_service_init.assert_called_once_with(100)

    def test_init(self):
        self.assertEqual(self.service_id, self.svc.service_id)
        self.assertEqual(self.tg, self.svc.tg)
        self.assertEqual(self.topic, self.svc.topic)

    @mock.patch.object(uuidutils, 'generate_uuid')
    @mock.patch.object(oslo_messaging, 'get_rpc_server')
    @mock.patch.object(service_obj.Service, 'create')
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

        mock_delete.assert_called_once_with(self.service_id)

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

    def test_get_revision(self):
        self.assertEqual(
            cfg.CONF.revision['senlin_engine_revision'],
            self.svc.get_revision(
                self.context, vorb.GetRevisionRequest().obj_to_primitive()
            )
        )


class ConductorCleanupTest(base.SenlinTestCase):
    def setUp(self):
        super(ConductorCleanupTest, self).setUp()

        self.service_id = '4db0a14c-dc10-4131-8ed6-7573987ce9b0'
        self.topic = consts.HEALTH_MANAGER_TOPIC

    @mock.patch.object(service_obj.Service, 'update')
    def test_conductor_manage_report(self, mock_update):
        cfg.CONF.set_override('periodic_interval', 0.1)

        self.svc = service.ConductorService('HOST', self.topic)
        self.svc.service_id = self.service_id

        # start engine and verify that update is being called more than once
        self.svc.start()
        eventlet.sleep(0.6)
        self.assertGreater(mock_update.call_count, 1)
        self.svc.stop()

    @mock.patch.object(service_obj.Service, 'update')
    def test_conductor_manage_report_with_exception(self, mock_update):
        cfg.CONF.set_override('periodic_interval', 0.1)

        self.svc = service.ConductorService('HOST', self.topic)
        self.svc.service_id = self.service_id

        # start engine and verify that update is being called more than once
        # even with the exception being thrown
        mock_update.side_effect = Exception('blah')
        self.svc.start()
        eventlet.sleep(0.6)
        self.assertGreater(mock_update.call_count, 1)
        self.svc.stop()

    @mock.patch.object(service_obj.Service, 'gc_by_engine')
    @mock.patch.object(service_obj.Service, 'get_all_expired')
    @mock.patch.object(service_obj.Service, 'delete')
    def test_service_manage_cleanup(self, mock_delete, mock_get_all_expired,
                                    mock_gc):
        self.svc = service.ConductorService('HOST', self.topic)
        self.svc.service_id = self.service_id
        delta = datetime.timedelta(seconds=2.2 * cfg.CONF.periodic_interval)
        ages_a_go = timeutils.utcnow(True) - delta
        mock_get_all_expired.return_value = [
            {'id': 'foo', 'updated_at': ages_a_go}
        ]
        self.svc.service_manage_cleanup()
        mock_delete.assert_called_once_with('foo')
        mock_gc.assert_called_once_with('foo')

    @mock.patch.object(service_obj.Service, 'get_all_expired')
    def test_service_manage_cleanup_without_exception(self,
                                                      mock_get_all_expired):
        cfg.CONF.set_override('periodic_interval', 0.1)

        self.svc = service.ConductorService('HOST', self.topic)
        self.svc.service_id = self.service_id

        # start engine and verify that get_all is being called more than once
        self.svc.start()
        eventlet.sleep(0.6)
        self.assertGreater(mock_get_all_expired.call_count, 1)
        self.svc.stop()

    @mock.patch.object(service_obj.Service, 'get_all_expired')
    def test_service_manage_cleanup_with_exception(self, mock_get_all_expired):
        cfg.CONF.set_override('periodic_interval', 0.1)

        self.svc = service.ConductorService('HOST', self.topic)
        self.svc.service_id = self.service_id

        # start engine and verify that get_all is being called more than once
        # even with the exception being thrown
        mock_get_all_expired.side_effect = Exception('blah')
        self.svc.start()
        eventlet.sleep(0.6)
        self.assertGreater(mock_get_all_expired.call_count, 1)
        self.svc.stop()
