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

from senlin.drivers.openstack import cinder_v2
from senlin.drivers.openstack import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(sdk, 'create_connection')
class TestCinderV2(base.SenlinTestCase):

    def setUp(self):
        super(TestCinderV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.fake_conn = mock.Mock()
        self.volume = self.fake_conn.block_store

    def test_init(self, mock_create):
        mock_create.return_value = self.fake_conn

        vo = cinder_v2.CinderClient(self.conn_params)

        self.assertEqual(self.fake_conn, vo.conn)
        mock_create.assert_called_once_with(self.conn_params)

    def test_volume_get(self, mock_create):
        mock_create.return_value = self.fake_conn
        vo = cinder_v2.CinderClient(self.conn_params)

        res = vo.volume_get('foo')

        expected = self.volume.get_volume.return_value
        self.assertEqual(expected, res)
        self.volume.get_volume.assert_called_once_with('foo')
