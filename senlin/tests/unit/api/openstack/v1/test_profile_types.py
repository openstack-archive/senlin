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
from senlin.api.openstack.v1 import profile_types
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class ProfileTypeControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(ProfileTypeControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = profile_types.ProfileTypeController(options=cfgopts)

    def test_profile_type_list(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/profile_types')

        engine_response = [{'name': 'os.heat.stack'},
                           {'name': 'os.nova.server'}]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        response = self.controller.index(req)
        self.assertEqual({'profile_types': engine_response}, response)

        mock_call.assert_called_once_with(req.context,
                                          ('profile_type_list', {}))

    def test_profile_type_list_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/profile_types')
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_profile_type_get(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 'SimpleProfile'
        req = self._get('/profile_types/%(type)s' % {'type': type_name})

        engine_response = {
            'name': type_name,
            'schema': {
                'Foo': {'type': 'String', 'required': False},
                'Bar': {'type': 'Integer', 'required': False},
            },
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        response = self.controller.get(req, type_name=type_name)

        mock_call.assert_called_once_with(
            req.context,
            ('profile_type_get', {'type_name': type_name}))

        self.assertEqual(engine_response, response['profile_type'])

    def test_profile_type_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 'BogusProfileType'
        req = self._get('/profile_types/%(type)s' % {'type': type_name})

        error = senlin_exc.ProfileTypeNotFound(profile_type=type_name)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, type_name=type_name)

        mock_call.assert_called_once_with(
            req.context,
            ('profile_type_get', {'type_name': type_name}))

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileTypeNotFound', resp.json['error']['type'])

    def test_profile_type_get_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        type_name = 'BogusProfileType'
        req = self._get('/profile_types/%(type)s' % {'type': type_name})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, type_name=type_name)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
