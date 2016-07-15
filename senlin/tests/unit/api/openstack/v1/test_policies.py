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

import copy
import mock
import six
from webob import exc

from oslo_serialization import jsonutils

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import policies
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
from senlin.common import policy
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

    def test_policy_index_normal(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        default_args = {'limit': None, 'marker': None, 'sort': None,
                        'filters': None, 'project_safe': True}

        mock_call.assert_called_with(req.context,
                                     ('policy_list', default_args))

        expected = {'policies': engine_resp}
        self.assertEqual(expected, result)

    def test_policy_index_whitelists_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'name': 'FAKE',
            'type': 'TYPE',
            'limit': 20,
            'marker': 'fake marker',
            'sort': 'fake sorting string',
            'global_project': True,
        }
        req = self._get('/policies', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, w = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(5, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('project_safe', engine_args)

    def test_policy_index_whitelist_bad_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/policies', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_index_whitelist_filter_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'type': 'some_type',
            'name': 'fake name',
        }
        req = self._get('/policies', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, w = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(2, len(filters))
        self.assertIn('name', filters)
        self.assertIn('type', filters)

    def test_policy_index_whitelist_filter_bad_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/policies', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_index_limit_non_int(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'policy_list',
                                     return_value=[])

        params = {'limit': 'abc'}
        req = self._get('/policies', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)
        self.assertIn("Invalid value 'abc' specified for 'limit'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(
            req.context,
            ('policy_create', {
                'name': 'test_policy',
                'spec': {
                    'type': 'policy_type',
                    'version': '1.0',
                    'properties': {'param_1': 'value1', 'param_2': 2}
                },
            })
        )

        expected = {'policy': engine_response}
        self.assertEqual(expected, resp)

    def test_policy_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_policy'}

        req = self._post('/policies', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Malformed request data, missing 'policy' key "
                         "in request body.", six.text_type(ex))

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
        error = senlin_exc.SpecValidationFailed(message=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        expected_args = body['policy']
        mock_call.assert_called_once_with(req.context,
                                          ('policy_create', expected_args))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SpecValidationFailed', resp.json['error']['type'])

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
        pid = 'aaaa-bbbb-cccc'
        req = self._get('/policies/%(policy_id)s' % {'policy_id': pid})

        engine_resp = {
            u'id': u'aaaa-bbbb-cccc',
            u'name': u'policy-1',
            u'type': u'test_policy_type-1.0',
            u'spec': {
                u'type': u'test_policy_type',
                u'version': u'1.0',
                u'properties': {
                    u'param_1': u'value1',
                    u'param_2': u'value2',
                }
            },
            u'created_time': u'2015-02-24T19:17:22Z',
            u'updated_time': None,
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.get(req, policy_id=pid)

        mock_call.assert_called_with(req.context,
                                     ('policy_get', {'identity': pid}))

        expected = {'policy': engine_resp}
        self.assertEqual(expected, result)

    def test_policy_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'non-existent-policy'
        req = self._get('/policies/%(policy_id)s' % {'policy_id': pid})

        error = senlin_exc.PolicyNotFound(policy=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, policy_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_policy_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        pid = 'non-existent-policy'
        req = self._get('/policies/%(policy_id)s' % {'policy_id': pid})

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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        result = self.controller.update(req, policy_id=pid, body=body)

        args = copy.deepcopy(body['policy'])
        args['identity'] = pid
        mock_call.assert_called_with(req.context, ('policy_update', args))

        expected = {'policy': engine_resp}
        self.assertEqual(expected, result)

    def test_policy_update_with_no_name(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'policy': {}}

        req = self._put('/policies/%(pid)s' % {'pid': pid},
                        jsonutils.dumps(body))

        engine_resp = mock.Mock()
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("Policy name not specified.",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_update_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._patch('/policies/%(pid)s' % {'pid': pid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        self.assertEqual("Malformed request data, missing 'policy' key in "
                         "request body.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_policy_update_with_spec(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'policy': {'spec': {'param_2': 'value3'}}
        }

        req = self._patch('/policies/%(policy_id)s' % {'policy_id': pid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, policy_id=pid, body=body)

        msg = _("Updating the spec of a policy is not supported because "
                "it may cause state conflicts in engine.")

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

        error = senlin_exc.PolicyNotFound(policy=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, policy_id=pid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

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
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/policies/%(policy_id)s' % {'policy_id': pid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, policy_id=pid)

        mock_call.assert_called_with(
            req.context, ('policy_delete', {'identity': pid}))

    def test_policy_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/policies/%(policy_id)s' % {'policy_id': pid})

        error = senlin_exc.PolicyNotFound(policy=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, policy_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_policy_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/policies/%(policy_id)s' % {'policy_id': pid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, policy_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
