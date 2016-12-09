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

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import policies
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
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

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_policy_index_normal(self, mock_call, mock_enforce):
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

        result = self.controller.index(req)

        expected = {u'policies': engine_resp}
        self.assertEqual(expected, result)

        mock_call.assert_called_with(req.context, 'policy_list2',
                                     mock.ANY)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.PolicyListRequest)
        self.assertTrue(request.project_safe)
        self.assertFalse(request.obj_attr_is_set('name'))
        self.assertFalse(request.obj_attr_is_set('type'))
        self.assertFalse(request.obj_attr_is_set('limit'))
        self.assertFalse(request.obj_attr_is_set('marker'))
        self.assertFalse(request.obj_attr_is_set('sort'))

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_policy_index_whitelists_params(self, mock_call, mock_enforce):
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

        engine_resp = [{'foo': 'bar'}]
        mock_call.return_value = engine_resp

        result = self.controller.index(req)

        expected = {u'policies': engine_resp}
        self.assertEqual(expected, result)

        mock_call.assert_called_once_with(req.context, 'policy_list2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.PolicyListRequest)
        self.assertFalse(request.project_safe)
        self.assertEqual(['FAKE'], request.name)
        self.assertEqual(['TYPE'], request.type)
        self.assertEqual(20, request.limit)
        self.assertEqual(fake_id, request.marker)
        self.assertEqual('name:asc', request.sort)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_policy_index_whitelist_bad_params(self, mock_call, mock_enforce):
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

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_policy_index_gloable_project_invalid(self, mock_call,
                                                  mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'global_project': 'No',
        }
        req = self._get('/policies', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual("Invalid value 'No' specified for 'global_project'",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_policy_index_limit_non_int(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'limit': 'abc'}
        req = self._get('/policies', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertIn("invalid literal for int() with base 10: 'abc'",
                      six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_policy_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/policies')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_policy_create_success(self, mock_enforce):
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(req.context, 'policy_create2',
                                     mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.PolicyCreateRequestBody)
        expected = {'policy': engine_response}
        self.assertEqual(expected, resp)
        # request = mock_call.call_args[0][2]
        # self.assertEqual('test_policy', request.name)

    def test_policy_create_no_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'not_policy': 'test_policy'}

        req = self._post('/policies', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Request body missing 'policy' key.",
                         six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_policy_create_bad_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'policy': {'name': 'fake_name'}}

        req = self._post('/policies', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("'spec' is a required property",
                         six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_policy_create_with_spec_validation_failed(self, mock_enforce):
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

        msg = 'Spec validation error (param): value'
        error = senlin_exc.InvalidSpec(message=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.PolicyCreateRequestBody)
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])

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
                                              self.controller.create, req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_policy_get_normal(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'pid'
        req = self._get('/policies/%s' % pid)

        engine_resp = {'foo': 'bar'}

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        result = self.controller.get(req, policy_id=pid)

        mock_call.assert_called_with(req.context, 'policy_get2',
                                     mock.ANY)

        expected = {'policy': engine_resp}
        self.assertEqual(expected, result)
        request = mock_call.call_args[0][2]
        self.assertEqual('pid', request.identity)

    def test_policy_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'non-existent-policy'
        req = self._get('/policies/%s' % pid)

        error = senlin_exc.ResourceNotFound(type='policy', id=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, policy_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_policy_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        pid = 'non-existent-policy'
        req = self._get('/policies/%s' % pid)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, policy_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_policy_update_normal(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)
        result = self.controller.update(req, policy_id=pid, body=body)
        mock_call.assert_called_with(req.context, 'policy_update2',
                                     mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.PolicyUpdateRequest)
        self.assertIsInstance(request.policy, vorp.PolicyUpdateRequestBody)
        self.assertEqual(pid, request.identity)
        self.assertEqual('policy-2', request.policy.name)
        expected = {'policy': engine_resp}
        self.assertEqual(expected, result)

    def test_policy_update_with_no_name(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'policy': {}}

        req = self._put('/policies/%(pid)s' % {'pid': pid},
                        jsonutils.dumps(body))

        engine_resp = mock.Mock()
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("'name' is a required property",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_update_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._patch('/policies/%(pid)s' % {'pid': pid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("Malformed request data, missing 'policy' key in "
                         "request body.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_update_with_unsupported_field(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'policy': {
                'name': 'new_name_policy',
                'bogus': 'foo'
            }
        }

        req = self._patch('/policies/%(policy_id)s' % {'policy_id': pid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        msg = _("Additional properties are not allowed"
                " ('bogus' was unexpected)")

        self.assertEqual(msg, six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_update_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'non-existent-policy'
        body = {
            'policy': {
                'name': 'new_policy',
            }
        }
        req = self._patch('/policies/%(policy_id)s' % {'policy_id': pid},
                          jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='policy', id=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
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
            'policy': {'name': 'test_policy', 'spec': {'param5': 'value5'}},
        }
        req = self._put('/policies/%(policy_id)s' % {'policy_id': pid},
                        jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, policy_id=pid, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_policy_delete_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'FAKE_ID'
        req = self._delete('/policies/%s' % pid)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, policy_id=pid)

        mock_call.assert_called_with(
            req.context, 'policy_delete2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertEqual('FAKE_ID', request.identity)

    def test_policy_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'FAKE_ID'
        req = self._delete('/policies/%s' % pid)

        error = senlin_exc.ResourceNotFound(type='policy', id=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

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

    def test_policy_validate_version_mismatch(self, mock_enforce):
        body = {
            'policy': {}
        }
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(senlin_exc.MethodVersionNotFound,
                               self.controller.validate,
                               req, body=body)

        mock_call.assert_not_called()
        self.assertEqual('API version 1.1 is not supported on this method.',
                         six.text_type(ex))

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

    def test_policy_validate_no_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {'foo': 'bar'}
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("Request body missing 'policy' key.",
                         six.text_type(ex))

    def test_policy_validate_no_spec(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'policy': {}
        }
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("'spec' is a required property", six.text_type(ex))

    def test_policy_validate_unsupported_field(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'policy': {
                'spec': {'type': 'senlin.policy.deletion',
                         'version': '1.0'},
                'foo': 'bar'
            }
        }
        req = self._post('/policies/validate', jsonutils.dumps(body),
                         version='1.2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("Additional properties are not allowed "
                         "('foo' was unexpected)", six.text_type(ex))

    def test_policy_validate_invalide_spec(self, mock_enforce):
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.validate,
                                              req, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])

    def test_policy_validate_success(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=spec)
        result = self.controller.validate(req, body=body)
        mock_call.assert_called_with(req.context,
                                     'policy_validate2', mock.ANY)
        expected = {'policy': spec}
        self.assertEqual(expected, result)
