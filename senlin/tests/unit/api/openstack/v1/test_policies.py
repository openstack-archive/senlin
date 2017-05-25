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

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from senlin.api.common import util
from senlin.api.middleware import fault
from senlin.api.openstack.v1 import policies
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.objects.requests import policies as vorp
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class PolicyControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(PolicyControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = policies.PolicyController(options=cfgopts)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_index_normal(self, mock_call, mock_parse,
                                 mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/policies')

        engine_resp = [
            {
                u'id': u'aaaa-bbbb-cccc',
                u'name': u'policy-1',
                u'type': u'test_policy_type',
                u'spec': {
                    u'param_1': u'value1',
                    u'param_2': u'value2',
                },
                u'created_time': u'2015-02-24T19:17:22Z',
                u'updated_time': None,
            }
        ]

        mock_call.return_value = engine_resp
        obj = vorp.PolicyListRequest()
        mock_parse.return_value = obj

        result = self.controller.index(req)

        expected = {u'policies': engine_resp}
        self.assertEqual(expected, result)

        mock_parse.assert_called_once_with('PolicyListRequest', req,
                                           {'project_safe': True})
        mock_call.assert_called_once_with(req.context, 'policy_list',
                                          mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_index_whitelists_params(self, mock_call, mock_parse,
                                            mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        fake_id = uuidutils.generate_uuid()
        params = {
            'name': 'FAKE',
            'type': 'TYPE',
            'limit': 20,
            'marker': fake_id,
            'sort': 'name:asc',
            'global_project': True,
        }
        req = self._get('/policies', params=params)
        obj = vorp.PolicyListRequest()
        mock_parse.return_value = obj

        engine_resp = [{'foo': 'bar'}]
        mock_call.return_value = engine_resp

        result = self.controller.index(req)

        expected = {u'policies': engine_resp}
        self.assertEqual(expected, result)

        mock_parse.assert_called_once_with(
            'PolicyListRequest', req,
            {
                'name': ['FAKE'],
                'type': ['TYPE'],
                'limit': '20',
                'marker': fake_id,
                'sort': 'name:asc',
                'project_safe': False,
            })
        mock_call.assert_called_once_with(req.context, 'policy_list',
                                          mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_index_whitelist_bad_params(self, mock_call, mock_parse,
                                               mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/policies', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)
        self.assertEqual(0, mock_parse.call_count)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_index_invalid_param(self, mock_call,
                                        mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': '10',
        }
        req = self._get('/policies', params=params)
        err = "Invalid value 'No' specified for 'global_project'"
        mock_parse.side_effect = exc.HTTPBadRequest(err)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual(err, six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)
        mock_parse.assert_called_once_with(
            'PolicyListRequest', req, {'limit': '10',
                                       'project_safe': True})

    def test_policy_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/policies')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_create_success(self, mock_call, mock_parse,
                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'policy': {
                'name': 'test_policy',
                'spec': {
                    'type': 'policy_type',
                    'version': '1.0',
                    'properties': {
                        'param_1': 'value1',
                        'param_2': 2,
                    }
                },
            }
        }

        engine_response = {
            'id': 'xxxx-yyyy-zzzz',
            'name': 'test_policy',
            'type': 'test_policy_type-1.0',
            'spec': {
                'type': 'policy_type',
                'version': '1.0',
                'properties': {
                    'param_1': 'value1',
                    'param_2': 2,
                },
            },
        }

        req = self._post('/policies', jsonutils.dumps(body))
        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = self.controller.create(req, body=body)
        self.assertEqual(engine_response, resp['policy'])
        mock_parse.assert_called_once_with(
            'PolicyCreateRequest', req, body, 'policy')
        mock_call.assert_called_with(req.context, 'policy_create',
                                     mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_create_no_policy(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'not_policy': 'test_policy'}

        req = self._post('/policies', jsonutils.dumps(body))
        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_create_bad_policy(self, mock_call, mock_parse,
                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'policy': {'name': 'fake_name'}}

        req = self._post('/policies', jsonutils.dumps(body))
        mock_parse.side_effect = exc.HTTPBadRequest("bad spec")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("bad spec", six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_create_with_spec_validation_failed(self, mock_call,
                                                       mock_parse,
                                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'policy': {
                'name': 'test_policy',
                'spec': {
                    'type': 'policy_type',
                    'version': '1.0',
                    'properties': {'param': 'value'}
                },
            }
        }
        req = self._post('/policies', jsonutils.dumps(body))
        obj = mock.Mock()
        mock_parse.return_value = obj
        err = senlin_exc.InvalidSpec(message="bad spec")
        mock_call.side_effect = shared.to_remote_error(err)
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])
        mock_parse.assert_called_once_with(
            'PolicyCreateRequest', mock.ANY, body, 'policy')
        mock_call.assert_called_once_with(req.context, 'policy_create',
                                          obj.policy)

    def test_policy_create_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', False)
        body = {
            'policy': {
                'name': 'test_policy',
                'spec': {
                    'type': 'policy_type',
                    'version': '1.0',
                    'properties': {'param': 'value'},
                }
            }
        }

        req = self._post('/policies', jsonutils.dumps(body))
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_get_normal(self, mock_call, mock_parse,
                               mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'pid'
        req = self._get('/policies/%s' % pid)

        engine_resp = {'foo': 'bar'}
        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.get(req, policy_id=pid)

        self.assertEqual(engine_resp, result['policy'])
        mock_parse.assert_called_once_with(
            'PolicyGetRequest', req, {'identity': pid})
        mock_call.assert_called_with(req.context, 'policy_get',
                                     mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_get_not_found(self, mock_call, mock_parse,
                                  mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'non-existent-policy'
        req = self._get('/policies/%s' % pid)

        error = senlin_exc.ResourceNotFound(type='policy', id=pid)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, policy_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])
        mock_parse.assert_called_once_with(
            "PolicyGetRequest", mock.ANY, {'identity': pid})

    def test_policy_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        pid = 'non-existent-policy'
        req = self._get('/policies/%s' % pid)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, policy_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_update_normal(self, mock_call, mock_parse,
                                  mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'policy': {
                'name': 'policy-2',
            }
        }

        req = self._put('/policies/%(policy_id)s' % {'policy_id': pid},
                        jsonutils.dumps(body))

        engine_resp = {
            u'id': pid,
            u'name': u'policy-2',
            u'type': u'test_policy_type',
            u'spec': {
                u'param_1': u'value1',
                u'param_2': u'value3',
            },
            u'created_time': u'2015-02-25T16:20:13Z',
            u'updated_time': None,
        }

        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.requests = obj

        obj
        result = self.controller.update(req, policy_id=pid, body=body)

        expected = {'policy': engine_resp}
        self.assertEqual(expected, result)

        mock_parse.assert_called_once_with(
            'PolicyUpdateRequest', req, {'identity': pid,
                                         'policy': mock.ANY})
        mock_call.assert_called_with(req.context, 'policy_update',
                                     mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_update_with_no_name(self, mock_call, mock_parse,
                                        mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'policy': {}}

        req = self._put('/policies/%(pid)s' % {'pid': pid},
                        jsonutils.dumps(body))
        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'PolicyUpdateRequest', req, {'identity': pid,
                                         'policy': mock.ANY})
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_update_with_bad_body(self, mock_call, mock_parse,
                                         mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._patch('/policies/%(pid)s' % {'pid': pid},
                          jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("Malformed request data, missing 'policy' key in "
                         "request body.", six.text_type(ex))
        self.assertFalse(mock_call.called)
        self.assertFalse(mock_parse.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_update_with_unsupported_field(self, mock_call, mock_parse,
                                                  mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'policy': {
                'name': 'new_name_policy',
                'bogus': 'foo'
            }
        }

        req = self._put('/policies/%(pid)s' % {'pid': pid},
                        jsonutils.dumps(body))
        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'PolicyUpdateRequest', req, {'identity': pid,
                                         'policy': mock.ANY})
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_update_not_found(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'non-existent-policy'
        body = {
            'policy': {
                'name': 'new_policy',
            }
        }
        req = self._patch('/policies/%(policy_id)s' % {'policy_id': pid},
                          jsonutils.dumps(body))

        obj = mock.Mock()
        mock_parse.return_value = obj
        error = senlin_exc.ResourceNotFound(type='policy', id=pid)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, policy_id=pid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_policy_update_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'policy': {'name': 'test_policy'},
        }
        req = self._put('/policies/%(policy_id)s' % {'policy_id': pid},
                        jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, policy_id=pid, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_delete_success(self, mock_call, mock_parse,
                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'FAKE_ID'
        req = self._delete('/policies/%s' % pid)

        obj = mock.Mock()
        mock_parse.return_value = obj
        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, policy_id=pid)

        mock_parse.assert_called_once_with(
            'PolicyDeleteRequest', req, {'identity': pid})
        mock_call.assert_called_with(
            req.context, 'policy_delete', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_delete_not_found(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'FAKE_ID'
        req = self._delete('/policies/%s' % pid)

        error = senlin_exc.ResourceNotFound(type='policy', id=pid)
        mock_call.side_effect = shared.to_remote_error(error)
        obj = mock.Mock()
        mock_parse.return_value = obj
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, policy_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_policy_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        pid = 'FAKE_ID'
        req = self._delete('/policies/%s' % pid)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, policy_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_validate_version_mismatch(self, mock_call, mock_enforce):
        body = {
            'policy': {}
        }
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.1')

        ex = self.assertRaises(senlin_exc.MethodVersionNotFound,
                               self.controller.validate,
                               req, body=body)

        mock_call.assert_not_called()
        self.assertEqual("API version '1.1' is not supported on this "
                         "method.", six.text_type(ex))

    def test_profile_validate_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', False)

        body = {
            'profile': {
                'name': 'test_policy',
                'spec': {
                    'type': 'test_policy_type',
                    'version': '1.0',
                    'properties': {
                        'param_1': 'value1',
                        'param_2': 2,
                    },
                },
                'metadata': {},
            }
        }

        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.validate,
                                              req, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_validate_no_body(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {'foo': 'bar'}
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')
        mock_parse.side_effect = exc.HTTPBadRequest("miss policy")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("miss policy", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'PolicyValidateRequest', req, body, 'policy')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_validate_no_spec(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'policy': {}
        }
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')

        mock_parse.side_effect = exc.HTTPBadRequest("miss policy")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("miss policy", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'PolicyValidateRequest', req, body, 'policy')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_validate_invalid_spec(self, mock_call, mock_parse,
                                          mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'policy': {
                'spec': {
                    'type': 'senlin.policy.deletion',
                    'version': '1.0'
                }
            }
        }

        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')

        msg = 'Spec validation error'
        error = senlin_exc.InvalidSpec(message=msg)
        mock_call.side_effect = shared.to_remote_error(error)
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.validate,
                                              req, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_policy_validate_success(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        spec = {
            'spec': {
                'properties': {'foo': 'bar'},
                'type': 'senlin.policy.deletion',
                'version': '1.0'
            }
        }
        body = {
            'policy': spec
        }

        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')
        obj = mock.Mock()
        mock_parse.return_value = obj
        mock_call.return_value = spec

        result = self.controller.validate(req, body=body)
        self.assertEqual(body, result)

        mock_parse.assert_called_once_with(
            'PolicyValidateRequest', req, body, 'policy')
        mock_call.assert_called_with(
            req.context, 'policy_validate', mock.ANY)
