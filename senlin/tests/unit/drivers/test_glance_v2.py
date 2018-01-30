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

from senlin.drivers.os import glance_v2
from senlin.drivers import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(sdk, 'create_connection')
class TestGlanceV2(base.SenlinTestCase):

    def setUp(self):
        super(TestGlanceV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.fake_conn = mock.Mock()
        self.image = self.fake_conn.image

    def test_init(self, mock_create):
        mock_create.return_value = self.fake_conn

        gc = glance_v2.GlanceClient(self.conn_params)

        self.assertEqual(self.fake_conn, gc.conn)
        mock_create.assert_called_once_with(self.conn_params)

    def test_image_find(self, mock_create):
        mock_create.return_value = self.fake_conn
        gc = glance_v2.GlanceClient(self.conn_params)

        res = gc.image_find('foo')

        expected = self.image.find_image.return_value
        self.assertEqual(expected, res)
        self.image.find_image.assert_called_once_with('foo', True)

    def test_image_find_ignore_missing(self, mock_create):
        mock_create.return_value = self.fake_conn
        gc = glance_v2.GlanceClient(self.conn_params)

        res = gc.image_find('foo', ignore_missing=False)

        expected = self.image.find_image.return_value
        self.assertEqual(expected, res)
        self.image.find_image.assert_called_once_with('foo', False)

    def test_image_get(self, mock_create):
        mock_create.return_value = self.fake_conn
        gc = glance_v2.GlanceClient(self.conn_params)

        res = gc.image_get('foo')

        expected = self.image.get_image.return_value
        self.assertEqual(expected, res)
        self.image.get_image.assert_called_once_with('foo')

    def test_image_delete(self, mock_create):
        mock_create.return_value = self.fake_conn
        gc = glance_v2.GlanceClient(self.conn_params)
        gc.image_delete('foo')
        self.image.delete_image.assert_called_once_with('foo', False)
        self.image.delete_image.reset_mock()

        gc.image_delete('foo', True)
        self.image.delete_image.assert_called_once_with('foo', True)
        self.image.delete_image.reset_mock()

        gc.image_delete('foo', False)
        self.image.delete_image.assert_called_once_with('foo', False)
