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


class TestCinderV2(base.SenlinTestCase):

    def setUp(self):
        super(TestCinderV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.mock_conn = mock.Mock()
        self.mock_create = self.patchobject(sdk, 'create_connection',
                                            return_value=self.mock_conn)
        self.volume = self.mock_conn.block_store
        self.vo = cinder_v2.CinderClient(self.conn_params)

    def test_init(self):
        self.mock_create.assert_called_once_with(self.conn_params)
        self.assertEqual(self.mock_conn, self.vo.conn)

    def test_volume_get(self):
        self.vo.volume_get('foo')
        self.volume.get_volume.assert_called_once_with('foo')
