#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
import iso8601
import mock

from senlin.api.openstack.v1 import services
from senlin.common import policy
from senlin.objects import service as service_obj
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


fake_services_list = [
    mock.Mock(binary='senlin-engine',
              host='host1',
              id=1,
              disabled=False,
              topic='senlin-engine',
              updated_at=datetime.datetime(2012, 10, 29, 13, 42, 11,
                                           tzinfo=iso8601.UTC),
              created_at=datetime.datetime(2014, 10, 29, 13, 42, 11,
                                           tzinfo=iso8601.UTC),
              disabled_reason='')
]


@mock.patch.object(policy, 'enforce')
class ServicesControllerTest(shared.ControllerTest, base.SenlinTestCase):

    def setUp(self):
        super(ServicesControllerTest, self).setUp()

        # Create WSGI controller instance
        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = services.ServiceController(options=cfgopts)

    def tearDown(self):
        super(ServicesControllerTest, self).tearDown()

    @mock.patch.object(service_obj.Service, 'get_all')
    def test_service_index(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/services')
        req.context.is_admin = True

        mock_call.return_value = fake_services_list
        res_dict = self.controller.index(req)

        response = {'services': [{'topic': 'senlin-engine',
                                  'binary': 'senlin-engine', 'id': 1,
                                  'host': 'host1', 'status': 'enabled',
                                  'state': 'down', 'disabled_reason': '',
                                  'updated_at': datetime.datetime(
                                      2012, 10, 29, 13, 42, 11)}]}
        self.assertEqual(res_dict, response)
