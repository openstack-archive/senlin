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
from webob import exc

from senlin.api.common import util
from senlin.api.middleware import fault
from senlin.api.openstack.v1 import policy_types
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class PolicyTypeControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(PolicyTypeControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = policy_types.PolicyTypeController(options=cfgopts)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_list(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/policy_types')

        engine_response = [
            {'name': 'senlin.policy.p1', 'version': '1.0', 'attr': 'v1'},
            {'name': 'senlin.policy.p2', 'version': '1.0', 'attr': 'v2'}
        ]

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        response = self.controller.index(req)

        self.assertEqual(
            [
                {'name': 'senlin.policy.p1-1.0'},
                {'name': 'senlin.policy.p2-1.0'},
            ],
            response['policy_types']
        )
        mock_parse.assert_called_once_with(
            'PolicyTypeListRequest', req, {})
        mock_call.assert_called_once_with(
            req.context, 'policy_type_list', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_list_old_version(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/policy_types', version='1.3')

        engine_response = [
            {'name': 'senlin.policy.p1', 'version': '1.0'},
            {'name': 'senlin.policy.p2', 'version': '1.1'}
        ]

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        response = self.controller.index(req)

        self.assertEqual(
            [
                {'name': 'senlin.policy.p1-1.0'},
                {'name': 'senlin.policy.p2-1.1'}
            ],
            response['policy_types']
        )
        mock_parse.assert_called_once_with(
            'PolicyTypeListRequest', req, {})
        mock_call.assert_called_once_with(
            req.context, 'policy_type_list', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_list_new_version(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/policy_types', version='1.5')

        engine_response = [
            {'name': 'senlin.policy.p1', 'version': '1.0', 'a1': 'v1'},
            {'name': 'senlin.policy.p2', 'version': '1.1', 'a2': 'v2'}
        ]

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        response = self.controller.index(req)

        self.assertEqual(engine_response, response['policy_types'])
        mock_parse.assert_called_once_with(
            'PolicyTypeListRequest', req, {})
        mock_call.assert_called_once_with(
            req.context, 'policy_type_list', mock.ANY)

    def test_list_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/policy_types')
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_get_old_version(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 'SimplePolicy'
        req = self._get('/policy_types/%(type)s' % {'type': type_name},
                        version='1.3')

        engine_response = {
            'name': type_name,
            'schema': {
                'Foo': {'type': 'String', 'required': False},
                'Bar': {'type': 'Integer', 'required': False},
            },
        }

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        response = self.controller.get(req, type_name=type_name)

        self.assertEqual(engine_response, response['policy_type'])
        mock_parse.assert_called_once_with(
            'PolicyTypeGetRequest', req, {'type_name': type_name})
        mock_call.assert_called_once_with(
            req.context, 'policy_type_get', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_get_new_version(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 'SimplePolicy'
        req = self._get('/policy_types/%(type)s' % {'type': type_name},
                        version='1.5')

        engine_response = {
            'name': type_name,
            'schema': {
                'Foo': {'type': 'String', 'required': False},
                'Bar': {'type': 'Integer', 'required': False},
            },
            'support_status': 'faked_status'
        }

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        response = self.controller.get(req, type_name=type_name)

        self.assertEqual(engine_response, response['policy_type'])
        mock_parse.assert_called_once_with(
            'PolicyTypeGetRequest', req, {'type_name': type_name})
        mock_call.assert_called_once_with(
            req.context, 'policy_type_get', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_type_get(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 'SimplePolicy'
        req = self._get('/policy_types/%(type)s' % {'type': type_name})

        engine_response = {
            'name': type_name,
            'schema': {
                'Foo': {'type': 'String', 'required': False},
                'Bar': {'type': 'Integer', 'required': False},
            },
        }

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        response = self.controller.get(req, type_name=type_name)

        self.assertEqual(engine_response, response['policy_type'])
        mock_parse.assert_called_once_with(
            'PolicyTypeGetRequest', req, {'type_name': type_name})
        mock_call.assert_called_once_with(
            req.context, 'policy_type_get', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_type_get_not_found(self, mock_call, mock_parse,
                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 'BogusPolicyType'
        req = self._get('/policy_types/%(type)s' % {'type': type_name})

        error = senlin_exc.ResourceNotFound(type='policy_type', id=type_name)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, type_name=type_name)
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_type_get_bad_param(self, mock_call, mock_parse,
                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        type_name = 11
        req = self._get('/policy_types/%(type)s' % {'type': type_name})

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.get,
                               req, type_name=type_name)
        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'PolicyTypeGetRequest', req, {'type_name': type_name})
        self.assertEqual(0, mock_call.call_count)

    def test_policy_type_schema_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        type_name = 'FakePolicyType'
        req = self._get('/policy_types/%(type)s' % {'type': type_name})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, type_name=type_name)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
