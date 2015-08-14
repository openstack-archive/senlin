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
from senlin.api.openstack.v1 import webhooks
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.apiv1 import shared
from senlin.tests.unit.common import base


class WebhookDataTest(base.SenlinTestCase):
    def test_webhook_data(self):
        body = {
            'name': 'test_webhook',
            'obj_type': 'test_obj_type',
            'obj_id': 'test_obj_id',
            'action': 'test_action',
            'credential': {
                'user_id': 'test_user_id',
                'password': 'test_pass',
            },
            'params': {
                'test_param': 'test_value'
            },
        }
        data = webhooks.WebhookData(body)
        self.assertEqual('test_webhook', data.name())
        self.assertEqual('test_obj_type', data.obj_type())
        self.assertEqual('test_obj_id', data.obj_id())
        self.assertEqual('test_action', data.action())
        self.assertEqual({'user_id': 'test_user_id', 'password': 'test_pass'},
                         data.credential())
        self.assertEqual({'test_param': 'test_value'}, data.params())

    def test_required_fields_missing(self):
        body = {'fake_field': 'fake_value'}
        data = webhooks.WebhookData(body)
        self.assertRaises(exc.HTTPBadRequest, data.obj_type)
        self.assertRaises(exc.HTTPBadRequest, data.obj_id)
        self.assertRaises(exc.HTTPBadRequest, data.action)
        self.assertRaises(exc.HTTPBadRequest, data.credential)


@mock.patch.object(policy, 'enforce')
class WebhookControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(WebhookControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = webhooks.WebhookController(options=cfgopts)

    def test_default(self, mock_enforce):
        self.assertRaises(exc.HTTPNotFound, self.controller.default, None)

    def test_webhook_index_normal(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/webhooks')

        engine_resp = [
            {
                u'id': u'aaaa-bbbb-cccc',
                u'name': u'test-webhook',
                u'user': u'admin',
                u'project': u'123456abcd3555',
                u'domain': u'default',
                u'obj_id': u'test-id',
                u'obj_type': u'test-type',
                u'action': u'test-action',
                u'credential': {
                    u'user_id': u'test-user-id',
                    u'password': u'test-pass',
                },
                u'created_time': u'2015-02-24T19:17:22Z',
                u'deleted_time': None,
                u'params': {},
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req, tenant_id=self.project)

        default_args = {'limit': None, 'marker': None,
                        'sort_keys': None, 'sort_dir': None,
                        'filters': None, 'project_safe': True,
                        'show_deleted': False}

        mock_call.assert_called_with(req.context,
                                     ('webhook_list', default_args))

        expected = {'webhooks': engine_resp}
        self.assertEqual(expected, result)

    def test_webhook_index_whitelists_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 20,
            'marker': 'fake marker',
            'sort_keys': 'fake sort keys',
            'sort_dir': 'fake sort dir',
            'show_deleted': False,
            'project_safe': True,
            'filters': None,
            'balrog': 'you shall not pass!'
        }
        req = self._get('/webhooks', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.project)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(7, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort_keys', engine_args)
        self.assertIn('sort_dir', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('show_deleted', engine_args)
        self.assertIn('project_safe', engine_args)
        self.assertNotIn('tenant_safe', engine_args)
        self.assertNotIn('balrog', engine_args)

    def test_webhook_index_whitelist_filter_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'obj_type': 'test-type',
            'obj_id': 'test-id',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/webhooks', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.project)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(2, len(filters))
        self.assertIn('obj_id', filters)
        self.assertIn('obj_type', filters)
        self.assertNotIn('balrog', filters)

    def test_webhook_index_show_deleted_false(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'webhook_list',
                                     return_value=[])

        params = {'show_deleted': 'False'}
        req = self._get('/webhooks', params=params)
        self.controller.index(req, tenant_id=self.project)
        mock_call.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY,
                                          show_deleted=False)

    def test_webhook_index_show_deleted_true(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'webhook_list',
                                     return_value=[])

        params = {'show_deleted': 'True'}
        req = self._get('/webhooks', params=params)
        self.controller.index(req, tenant_id=self.project)
        mock_call.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY,
                                          show_deleted=True)

    def test_webhook_index_show_deleted_non_bool(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'webhook_list',
                                     return_value=[])

        params = {'show_deleted': 'yes'}
        req = self._get('/webhooks', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req,
                               tenant_id=self.project)
        self.assertIn("Invalid value 'yes' specified for 'show_deleted'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_webhook_index_limit_non_int(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'webhook_list',
                                     return_value=[])

        params = {'limit': 'abc'}
        req = self._get('/webhooks', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req,
                               tenant_id=self.project)
        self.assertIn("Invalid value 'abc' specified for 'limit'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_webhook_index_global_project(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'webhook_list',
                                     return_value=[])

        params = {'global_project': True}
        req = self._get('/webhooks', params=params)
        self.controller.index(req, tenant_id=self.project)
        mock_call.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY,
                                          project_safe=False)

    def test_webhook_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/webhooks')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.project)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_webhook_create_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'webhook': {
                'name': 'test_webhook',
                'obj_type': 'test_obj_type',
                'obj_id': 'test_obj_id',
                'action': 'test_action',
                'credential': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass',
                },
                'params': {
                    'test_param': 'test_value'
                },
            }
        }

        engine_response = {
            'id': 'xxxx-yyyy-zzzz',
            'name': 'test_webhook',
            'obj_type': 'test_obj_type',
            'obj_id': 'test_obj_id',
            'action': 'test_action',
            'credential': {
                'user_id': 'test_user_id',
                'password': 'test_pass',
            },
            'params': {
                'test_param': 'test_value'
            },
            'url': 'test_url'
        }

        req = self._post('/webhooks', json.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, tenant_id=self.project, body=body)

        mock_call.assert_called_with(
            req.context,
            ('webhook_create', {
                'name': 'test_webhook',
                'obj_type': 'test_obj_type',
                'obj_id': 'test_obj_id',
                'action': 'test_action',
                'credential': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass'
                },
                'params': {'test_param': 'test_value'},
            })
        )

        expected = {'webhook': engine_response}
        self.assertEqual(expected, resp)

    def test_webhook_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_webhook'}

        req = self._post('/webhooks', json.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, tenant_id=self.project,
                               body=body)

        self.assertEqual("Malformed request data, missing 'webhook' key "
                         "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_webhook_create_with_bad_obj_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        obj_type = 'unknown_obj_type'
        body = {
            'webhook': {
                'name': 'test_webhook',
                'obj_type': obj_type,
                'obj_id': 'test_obj_id',
                'action': 'test_action',
                'credential': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass',
                },
                'params': {
                    'test_param': 'test_value'
                },
            }
        }
        req = self._post('/webhooks', json.dumps(body))

        msg = _('webhook obj_type %s is unsupported') % obj_type
        error = senlin_exc.SenlinBadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        expected_args = body['webhook']
        mock_call.assert_called_once_with(req.context,
                                          ('webhook_create', expected_args))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SenlinBadRequest', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    def test_webhook_create_with_obj_id_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        obj_id = 'false_obj_id'
        body = {
            'webhook': {
                'name': 'test_webhook',
                'obj_type': 'cluster',
                'obj_id': obj_id,
                'action': 'test_action',
                'credential': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass',
                },
                'params': {
                    'test_param': 'test_value'
                },
            }
        }
        req = self._post('/webhooks', json.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=obj_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        expected_args = body['webhook']
        mock_call.assert_called_once_with(req.context,
                                          ('webhook_create', expected_args))
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    def test_webhook_create_illegal_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        action = 'illegal_action'
        body = {
            'webhook': {
                'name': 'test_webhook',
                'obj_type': 'test_obj_type',
                'obj_id': 'test_obj_id',
                'action': action,
                'credential': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass',
                },
                'params': {
                    'test_param': 'test_value'
                },
            }
        }
        req = self._post('/webhooks', json.dumps(body))

        msg = _('illegal action name %s') % action
        error = senlin_exc.SenlinBadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        expected_args = body['webhook']
        mock_call.assert_called_once_with(req.context,
                                          ('webhook_create', expected_args))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SenlinBadRequest', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    def test_webhook_create_unapplicable_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        obj_type = 'test_obj_type'
        action = 'unapplicable_action'
        body = {
            'webhook': {
                'name': 'test_webhook',
                'obj_type': obj_type,
                'obj_id': 'test_obj_id',
                'action': action,
                'credential': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass',
                },
                'params': {
                    'test_param': 'test_value'
                },
            }
        }
        req = self._post('/webhooks', json.dumps(body))

        msg = _('Action %(action)s is not applicable to '
                'object %(obj_type)s') % {'action': action,
                                          'obj_type': obj_type}
        error = senlin_exc.SenlinBadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        expected_args = body['webhook']
        mock_call.assert_called_once_with(req.context,
                                          ('webhook_create', expected_args))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SenlinBadRequest', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    def test_webhook_create_credential_missing(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'webhook': {
                'name': 'test_webhook',
                'obj_type': 'test_obj_type',
                'obj_id': 'test_obj_id',
                'action': 'test_action',
                'credential': None,
                'params': {
                    'test_param': 'test_value'
                },
            }
        }
        req = self._post('/webhooks', json.dumps(body))

        msg = _('The credential parameter is missing')
        error = senlin_exc.SenlinBadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        expected_args = body['webhook']
        mock_call.assert_called_once_with(req.context,
                                          ('webhook_create', expected_args))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SenlinBadRequest', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    def test_webhook_get_normal(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._get('/webhooks/%(webhook_id)s' % {'webhook_id': wid})

        engine_resp = {
            u'id': u'aaaa-bbbb-cccc',
            u'name': u'test-webhook',
            u'user': u'admin',
            u'project': u'123456abcd3555',
            u'domain': u'default',
            u'obj_id': u'test-id',
            u'obj_type': u'test-type',
            u'action': u'test-action',
            u'credential': {
                u'user_id': u'test-user-id',
                u'password': u'test-pass',
            },
            u'created_time': u'2015-02-24T19:17:22Z',
            u'deleted_time': None,
            u'params': {},
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.get(req, tenant_id=self.project,
                                     webhook_id=wid)

        mock_call.assert_called_with(req.context,
                                     ('webhook_get', {'identity': wid}))

        expected = {'webhook': engine_resp}
        self.assertEqual(expected, result)

    def test_webhook_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        wid = 'non-existent-webhook'
        req = self._get('/webhooks/%(webhook_id)s' % {'webhook_id': wid})

        error = senlin_exc.WebhookNotFound(webhook=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.project,
                                              webhook_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('WebhookNotFound', resp.json['error']['type'])

    def test_webhook_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        wid = 'non-existent-webhook'
        req = self._get('/webhooks/%(webhook_id)s' % {'webhook_id': wid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.project,
                                              webhook_id=wid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_webhook_trigger(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = None
        webhook_id = 'test_webhook_id'
        action_id = 'test_action_id'

        engine_response = {
            'action': action_id,
        }

        req = self._post('/webhooks/test_webhook_id/trigger',
                         json.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.trigger(req, tenant_id=self.project,
                                       webhook_id=webhook_id,
                                       body=None)

        mock_call.assert_called_with(
            req.context,
            ('webhook_trigger', {
                'params': None,
                'identity': webhook_id,
            })
        )

        expected = engine_response
        self.assertEqual(expected, resp)

    def test_webhook_trigger_with_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = {'params': {'key': 'value'}}
        webhook_id = 'test_webhook_id'

        engine_response = {'action': 'FAKE_ACTION'}

        req = self._post('/webhooks/test_webhook_id/trigger',
                         json.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.trigger(req, tenant_id=self.project,
                                       webhook_id=webhook_id,
                                       body=body)

        mock_call.assert_called_with(req.context,
                                     ('webhook_trigger',
                                      {'params': {'key': 'value'},
                                       'identity': webhook_id}))

        expected = engine_response
        self.assertEqual(expected, resp)

    def test_webhook_delete_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/webhooks/%(webhook_id)s' % {'webhook_id': wid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent, self.controller.delete,
                          req, tenant_id=self.project, webhook_id=wid)

        mock_call.assert_called_with(
            req.context,
            ('webhook_delete', {'identity': wid}))

    def test_webhook_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/webhooks/%(webhook_id)s' % {'webhook_id': wid})

        error = senlin_exc.WebhookNotFound(webhook=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              webhook_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('WebhookNotFound', resp.json['error']['type'])

    def test_webhook_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/webhooks/%(webhook_id)s' % {'webhook_id': wid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              webhook_id=wid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
