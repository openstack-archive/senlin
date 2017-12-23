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
import testtools

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import health_registry as hro


class TestHealthRegistry(testtools.TestCase):

    def setUp(self):
        super(TestHealthRegistry, self).setUp()
        self.ctx = mock.Mock()

    @mock.patch.object(base.SenlinObject, '_from_db_object')
    @mock.patch.object(db_api, 'registry_create')
    def test_create(self, mock_create, mock_from):
        x_registry = mock.Mock()
        mock_create.return_value = x_registry
        x_obj = mock.Mock()
        mock_from.return_value = x_obj

        result = hro.HealthRegistry.create(
            self.ctx, "FAKE_ID", "FAKE_TYPE", 123, {'foo': 'bar'},
            'FAKE_ENGINE')

        self.assertEqual(x_obj, result)
        mock_create.assert_called_once_with(
            self.ctx, "FAKE_ID", "FAKE_TYPE", 123, {'foo': 'bar'},
            "FAKE_ENGINE", enabled=True)
        mock_from.assert_called_once_with(self.ctx, mock.ANY, x_registry)

    @mock.patch.object(db_api, 'registry_update')
    def test_update(self, mock_update):
        hro.HealthRegistry.update(self.ctx, "FAKE_ID", {"foo": "bar"})

        mock_update.assert_called_once_with(
            self.ctx, "FAKE_ID", {"foo": "bar"})

    @mock.patch.object(base.SenlinObject, '_from_db_object')
    @mock.patch.object(db_api, 'registry_claim')
    def test_claim(self, mock_claim, mock_from):
        x_registry = mock.Mock()
        mock_claim.return_value = [x_registry]
        x_obj = mock.Mock()
        mock_from.side_effect = [x_obj]

        result = hro.HealthRegistry.claim(self.ctx, "FAKE_ENGINE")

        self.assertEqual([x_obj], result)
        mock_claim.assert_called_once_with(self.ctx, "FAKE_ENGINE")
        mock_from.assert_called_once_with(self.ctx, mock.ANY, x_registry)

    @mock.patch.object(db_api, 'registry_delete')
    def test_delete(self, mock_delete):
        hro.HealthRegistry.delete(self.ctx, "FAKE_ID")

        mock_delete.assert_called_once_with(self.ctx, "FAKE_ID")

    @mock.patch.object(base.SenlinObject, '_from_db_object')
    @mock.patch.object(db_api, 'registry_get')
    def test_get(self, mock_get, mock_from):
        x_registry = mock.Mock()
        x_registry.cluster_id = 'FAKE'
        mock_get.return_value = x_registry

        x_obj = mock.Mock()
        mock_from.return_value = x_obj

        result = hro.HealthRegistry.get(self.ctx, 'FAKE')

        self.assertEqual(x_obj, result)
        mock_get.assert_called_once_with(self.ctx, 'FAKE')
        mock_from.assert_called_once_with(self.ctx, mock.ANY, x_registry)

    @mock.patch.object(base.SenlinObject, '_from_db_object')
    @mock.patch.object(db_api, 'registry_get_by_param')
    def test_get_by_engine(self, mock_get, mock_from):
        x_registry = mock.Mock()
        x_registry.cluster_id = 'FAKE'
        x_registry.engine_id = 'FAKE_ENGINE'
        mock_get.return_value = x_registry

        x_obj = mock.Mock()
        mock_from.return_value = x_obj

        result = hro.HealthRegistry.get_by_engine(
            self.ctx, 'FAKE_ENGINE', 'FAKE')

        self.assertEqual(x_obj, result)
        mock_get.assert_called_once_with(
            self.ctx, {"cluster_id": "FAKE", "engine_id": "FAKE_ENGINE"})
        mock_from.assert_called_once_with(self.ctx, mock.ANY, x_registry)

    @mock.patch.object(hro.HealthRegistry, 'update')
    def test_disable(self, mock_update):
        hro.HealthRegistry.disable_registry(
            self.ctx, "FAKE_ID")

        mock_update.assert_called_once_with(
            self.ctx, "FAKE_ID", {"enabled": False})

    @mock.patch.object(hro.HealthRegistry, 'update')
    def test_enable(self, mock_update):
        hro.HealthRegistry.enable_registry(
            self.ctx, "FAKE_ID")

        mock_update.assert_called_once_with(
            self.ctx, "FAKE_ID", {"enabled": True})
