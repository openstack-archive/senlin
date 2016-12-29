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
import six

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import build_info
from senlin.common import policy
from senlin.objects.requests import build_info as vorb
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class BuildInfoControllerTest(shared.ControllerTest, base.SenlinTestCase):

    def setUp(self):
        super(BuildInfoControllerTest, self).setUp()
        self.controller = build_info.BuildInfoController({})

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_default_build_revision(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'build_info', True)
        req = self._get('/build_info')

        mock_call.return_value = '12.34'

        result = self.controller.build_info(req)
        response = result['build_info']
        self.assertIn('api', response)
        self.assertIn('engine', response)
        self.assertIn('revision', response['api'])
        self.assertEqual('1.0', response['api']['revision'])
        self.assertIn('revision', response['engine'])
        self.assertEqual('12.34', response['engine']['revision'])

        mock_call.assert_called_once_with(req.context,
                                          'get_revision', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorb.GetRevisionRequest)

    @mock.patch.object(build_info.cfg, 'CONF')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_response_api_build_revision_from_config_file(
            self, mock_call, mock_conf, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'build_info', True)
        req = self._get('/build_info')
        mock_call.return_value = 'engine_revision'
        mock_conf.revision = {'senlin_api_revision': 'test'}

        result = self.controller.build_info(req)
        response = result['build_info']
        self.assertEqual('test', response['api']['revision'])
        mock_call.assert_called_once_with(req.context,
                                          'get_revision', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorb.GetRevisionRequest)

    def test_build_info_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'build_info', False)
        req = self._get('/build_info')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.build_info,
                                              req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
