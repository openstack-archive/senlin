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

import json
import mock
import six
from webob import exc

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import profiles 
from senlin.common import exception as senlin_exc 
from senlin.common import policy
from senlin.tests.apiv1 import shared
from senlin.tests.common import base
from senlin.rpc import client as rpc_client


class ProfileDataTest(base.SenlinTestCase):
    def test_profile_data(self):
        body = {
            'name': 'test_profile',
            'spec': {
                'param1': 'value1',
                'param2': 'value2',
            },
            'type': 'test_profile_type',
            'permission': None,
            'tags': {}
            }
        data = profiles.ProfileData(body)
        self.assertEqual('test_profile', data.name())
        self.assertEqual({'param1': 'value1', 'param2': 'value2'}, data.spec())
        self.assertEqual('test_profile_type', data.type())
        self.assertIsNone(data.permission())
        self.assertEqual({}, data.tags())

    def test_required_fields_missing(self):
        body = {'not a profile name': 'wibble'}
        data = profiles.ProfileData(body)
        self.assertRaises(exc.HTTPBadRequest, data.name)
        self.assertRaises(exc.HTTPBadRequest, data.spec)
        self.assertRaises(exc.HTTPBadRequest, data.type)
        self.assertIsNone(data.permission())
        self.assertIsNone(data.tags())


@mock.patch.object(policy.Enforcer, 'enforce')
class ProfileControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(ProfileControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778 

        cfgopts = DummyConfig()
        self.controller = profiles.ProfileController(options=cfgopts)

    def test_profile_index_normal(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/profiles')

        engine_resp = [
            {
                u'id': u'aaaa-bbbb-cccc', 
                u'name': u'profile-1',
                u'type': u'test_profile_type',
                u'spec': {
                    u'param_1': u'value1',
                    u'param_2': u'value2',
                },
                u'permission': '',
                u'created_time': u'2015-02-24T19:17:22Z',
                u'updated_time': None,
                u'deleted_time': None,
                u'tags': {},
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        
        result = self.controller.index(req, tenant_id=self.tenant)

        default_args = {'limit': None, 'marker': None,
                        'sort_keys': None, 'sort_dir': None,
                        'filters': None, 'show_deleted': False}

        mock_call.assert_called_with(req.context, ('profile_list', default_args))

        expected = {'profiles': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_index_whitelists_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 20,
            'marker': 'fake marker',
            'sort_keys': 'fake sort keys',
            'sort_dir': 'fake sort dir',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/profiles', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.tenant)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(6, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort_keys', engine_args)
        self.assertIn('sort_dir', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('show_deleted', engine_args)
        self.assertNotIn('tenant_safe', engine_args)
        self.assertNotIn('balrog', engine_args)

    def test_profile_index_whitelist_filter_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'type': 'some_type',
            'name': 'fake name',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/profiles', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.tenant)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(2, len(filters))
        self.assertIn('name', filters)
        self.assertIn('type', filters)
        self.assertNotIn('balrog', filters)

    def test_profile_index_show_deleted_false(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'profile_list',
                                     return_value=[])

        params = {'show_deleted': 'False'}
        req = self._get('/profiles', params=params)
        self.controller.index(req, tenant_id=self.tenant)
        mock_call.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY,
                                          show_deleted=False)

    def test_profile_index_show_deleted_true(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'profile_list',
                                     return_value=[])

        params = {'show_deleted': 'True'}
        req = self._get('/profiles', params=params)
        self.controller.index(req, tenant_id=self.tenant)
        mock_call.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY,
                                          show_deleted=True)

    def test_profile_index_show_deleted_non_bool(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'profile_list',
                                     return_value=[])

        params = {'show_deleted': 'yes'}
        req = self._get('/profiles', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req,
                               tenant_id=self.tenant)
        self.assertIn("Invalid value 'yes' specified for 'show_deleted'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_index_limit_non_int(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'profile_list',
                                     return_value=[])

        params = {'limit': 'abc'}
        req = self._get('/profiles', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req,
                               tenant_id=self.tenant)
        self.assertIn("Invalid value 'abc' specified for 'limit'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/profiles')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.tenant)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_profile_create_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'profile': {
                'name': 'test_profile',
                'type': 'test_profile_type',
                'spec': {
                    'param_1': 'value1',
                    'param_2': 2,
                },
                'permission': None,
                'tags': {},
            }
        }

        engine_response = {
            'id': 'xxxx-yyyy-zzzz',
            'name': 'test_profile',
            'type': 'test_profile_type',
            'spec': {
                    'param_1': 'value1',
                    'param_2': 2,
             },
             'permission': None,
             'tags': {},
        }

        req = self._post('/profiles', json.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, tenant_id=self.tenant, body=body)

        mock_call.assert_called_with(
            req.context,
            ('profile_create', {
                'name': 'test_profile',
                'type': 'test_profile_type',
                'spec': {'param_1': 'value1', 'param_2': 2},
                'perm': None,
                'tags': {},
            })
        )

        expected = {'profile': engine_response}
        self.assertEqual(expected, resp)

    def test_profile_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_profile'}

        req = self._post('/profiles', json.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, tenant_id=self.tenant,
                               body=body)

        self.assertEqual("Malformed request data, missing 'profile' key "
                         "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_profile_create_with_bad_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'profile': {
                'name': 'test_profile',
                'type': 'unknown_type',
                'spec': {'param': 'value'},
                'permission': None,
                'tags': {},
            }
        }
        req = self._post('/profiles', json.dumps(body))

        msg = 'Unknown profile type: unknown_profile'
        error = senlin_exc.ProfileValidationFailed(message=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.tenant,
                                              body=body)

        mock_call.assert_called_once()
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('ProfileValidationFailed', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])
