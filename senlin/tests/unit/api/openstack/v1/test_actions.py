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

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import actions
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class ActionControllerTest(shared.ControllerTest, base.SenlinTestCase):
    '''Tests the API class which acts as the WSGI controller.'''

    def setUp(self):
        super(ActionControllerTest, self).setUp()

        # Create WSGI controller instance
        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = actions.ActionController(options=cfgopts)

    def test_action_index(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/actions')

        engine_resp = [
            {
                'action': 'NODE_CREATE',
                'cause': 'RPC_Request',
                'depended_by': [],
                'depends_on': [],
                'end_time': 1425555000.0,
                'id': '2366d400-c7e3-4961-09254-6d1c3f7ac167',
                'inputs': {},
                'interval': -1,
                'name': 'node_create_0df0931b',
                'outputs': {},
                'owner': None,
                'start_time': 1425550000.0,
                'status': 'SUCCEEDED',
                'status_reason': 'Action completed successfully.',
                'target': '0df0931b-e251-4f2e-8719-4effda3627ba',
                'timeout': 3600
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        default_args = {'limit': None, 'marker': None, 'sort': None,
                        'filters': None, 'project_safe': True}

        mock_call.assert_called_with(req.context,
                                     ('action_list', default_args))

        expected = {'actions': engine_resp}
        self.assertEqual(expected, result)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_action_index_whitelists_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 10,
            'marker': 'fake marker',
            'sort': 'fake sorting option',
            'global_project': True,
        }
        req = self._get('/actions', params=params)
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(5, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort', engine_args)
        self.assertIn('project_safe', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_action_index_whitelists_invalid_params(self, mock_call,
                                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!',
        }
        req = self._get('/actions', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_action_index_limit_not_int(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'limit': 'not-int'}
        req = self._get('/actions', params=params)

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'not-int' specified for 'limit'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_action_index_whitelist_filter_params(self, mock_call,
                                                  mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'name': 'fake name',
            'target': '1111-2222-3333',
            'action': 'CLUSTER_CREATE',
            'status': 'SUCCEEDED'
        }
        req = self._get('/actions', params=params)
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(4, len(filters))
        self.assertIn('name', filters)
        self.assertIn('action', filters)
        self.assertIn('target', filters)
        self.assertIn('status', filters)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_action_index_whitelist_filter_invalid_params(self, mock_call,
                                                          mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/actions', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    def test_action_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/actions')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_action_get_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        action_id = 'aaaa-bbbb-cccc'
        req = self._get('/actions/%(action_id)s' % {'action_id': action_id})

        engine_resp = {
            'action': 'NODE_CREATE',
            'cause': 'RPC_Request',
            'depended_by': [],
            'depends_on': [],
            'end_time': 1425555000.0,
            'id': '2366d400-c7e3-4961-09254-6d1c3f7ac167',
            'inputs': {},
            'interval': -1,
            'name': 'node_create_0df0931b',
            'outputs': {},
            'owner': None,
            'start_time': 1425550000.0,
            'status': 'SUCCEEDED',
            'status_reason': 'Action completed successfully.',
            'target': '0df0931b-e251-4f2e-8719-4effda3627ba',
            'timeout': 3600
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        response = self.controller.get(req, action_id=action_id)

        mock_call.assert_called_once_with(
            req.context, ('action_get', {'identity': action_id}))

        self.assertEqual({'action': engine_resp}, response)

    def test_action_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        action_id = 'non-existent-action'
        req = self._get('/actions/%(action_id)s' % {'action_id': action_id})

        error = senlin_exc.ActionNotFound(action=action_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, action_id=action_id)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ActionNotFound', resp.json['error']['type'])

    def test_action_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        action_id = 'non-existent-action'
        req = self._get('/actions/%(action_id)s' % {'action_id': action_id})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, action_id=action_id)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
