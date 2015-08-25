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
from oslo_serialization import jsonutils
import six
from webob import exc

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import triggers
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.apiv1 import shared
from senlin.tests.unit.common import base


class TriggerDataTest(base.SenlinTestCase):

    def test_initialize(self):
        body = {
            'name': 'test_trigger',
            'spec': {
                'type': 'test_alarm_type',
                'version': '1.0',
                'param1': 'value1',
            },
            'description': 'a test alarm',
            'state': 'ok',
            'severity': 'low',
            'enabled': True,
        }
        data = triggers.TriggerData(body)
        self.assertEqual('test_trigger', data.name)
        self.assertEqual({'type': 'test_alarm_type',
                          'version': '1.0',
                          'param1': 'value1'},
                         data.spec)
        self.assertEqual('a test alarm', data.desc)
        self.assertEqual('ok', data.state)
        self.assertEqual(True, data.enabled)
        self.assertEqual('low', data.severity)

    def test_required_fields_missing(self):
        body = {'no_name': 'boom', 'spec': {}}
        data = triggers.TriggerData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate)
        self.assertEqual('No trigger name specified.', six.text_type(ex))

        body = {'name': 'biang', 'no_spec': {}}
        data = triggers.TriggerData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate)
        self.assertEqual('No trigger spec provided.', six.text_type(ex))

    def test_enabled_not_boolean(self):
        body = {'name': 'boom', 'spec': {}, 'enabled': 'yes'}
        data = triggers.TriggerData(body)
        ex = self.assertRaises(senlin_exc.InvalidParameter, data.validate)
        self.assertEqual("Invalid value 'yes' specified for 'enabled'",
                         six.text_type(ex))


@mock.patch.object(policy, 'enforce')
class TriggerControllerTest(shared.ControllerTest, base.SenlinTestCase):

    def setUp(self):
        super(TriggerControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = triggers.TriggerController(options=cfgopts)

    def test_default_handler(self, mock_enforce):
        req = self._get('/triggers')
        self.assertRaises(exc.HTTPNotFound, self.controller.default, req)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_normal(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/triggers')

        engine_resp = [
            {
                'id': 'FAKE_ID',
                'name': 'fake-name',
                'description': 'fake desc',
                'enabled': True,
                'spec': {
                    'type': 'alarm',
                    'version': '1.0',
                    'rule': {'p1': 'v1', 'p2': 'v2'},
                },
                'state': 'ok',
                'created_time': '2015-06-24T11:22:33Z',
                'updated_time': None,
                'deleted_time': None,
                'severity': 'low',
            }
        ]

        mock_call.return_value = engine_resp
        result = self.controller.index(req, tenant_id=self.project)

        args = {'limit': None, 'marker': None, 'sort_keys': None,
                'sort_dir': None, 'filters': None, 'show_deleted': False,
                'project_safe': True}

        mock_call.assert_called_with(req.context, ('trigger_list', args))

        self.assertEqual({'triggers': engine_resp}, result)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelists_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 20,
            'marker': 'MARKER',
            'sort_keys': 'KEYS',
            'sort_dir': 'asc',
            'show_deleted': False,
            'filters': None,
            'global_project': True,
            'balrog': 'Illegal!'
        }
        req = self._get('/triggers', params=params)
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
        self.assertNotIn('balrog', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelist_filter_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'name': 'fake name',
            'type': 'some_type',
            'state': 'some_state',
            'enabled': True,
            'severity': 'high',
            'balrog': 'invalid!'
        }
        req = self._get('/triggers', params=params)

        mock_call.return_value = []
        self.controller.index(req, tenant_id=self.project)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(5, len(filters))
        self.assertIn('name', filters)
        self.assertIn('type', filters)
        self.assertIn('state', filters)
        self.assertIn('severity', filters)
        self.assertIn('enabled', filters)
        self.assertNotIn('balrog', filters)

    @mock.patch.object(rpc_client.EngineClient, 'trigger_list')
    def test_index_show_deleted_false(self, mock_list, mock_enforce):
        mock_list.return_value = []

        params = {'show_deleted': 'False'}
        req = self._get('/triggers', params=params)
        self.controller.index(req, tenant_id=self.project)
        mock_list.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY, show_deleted=False)

    @mock.patch.object(rpc_client.EngineClient, 'trigger_list')
    def test_index_show_deleted_true(self, mock_list, mock_enforce):
        mock_list.return_value = []
        params = {'show_deleted': 'True'}
        req = self._get('/triggers', params=params)
        self.controller.index(req, tenant_id=self.project)
        mock_list.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY, show_deleted=True)

    @mock.patch.object(rpc_client.EngineClient, 'trigger_list')
    def test_index_show_deleted_not_bool(self, mock_list, mock_enforce):
        mock_list.return_value = []
        params = {'show_deleted': 'yes'}
        req = self._get('/triggers', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req,
                               tenant_id=self.project)
        self.assertIn("Invalid value 'yes' specified for 'show_deleted'",
                      six.text_type(ex))
        self.assertFalse(mock_list.called)

    @mock.patch.object(rpc_client.EngineClient, 'trigger_list')
    def test_index_limit_non_int(self, mock_list, mock_enforce):
        mock_list.return_value = []
        params = {'limit': 'abc'}
        req = self._get('/triggers', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req,
                               tenant_id=self.project)
        self.assertIn("Invalid value 'abc' specified for 'limit'",
                      six.text_type(ex))
        self.assertFalse(mock_list.called)

    def test_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/triggers')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.project)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_create_success(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'trigger': {
                'name': 'test_trigger',
                'spec': {
                    'type': 'alarm_type',
                    'param_1': 'value1',
                    'param_2': 2,
                },
                'enabled': True,
                'severity': 'low',
            }
        }

        engine_response = {
            'id': 'xxxx-yyyy-zzzz',
            'name': 'test_trigger',
            'spec': {
                'type': 'alarm_type',
                'param_1': 'value1',
                'param_2': 2,
            },
            'enabled': True,
            'description': None,
            'severity': 'low',
            'state': 'ok',
        }

        req = self._post('/triggers', jsonutils.dumps(body))
        mock_call.return_value = engine_response

        resp = self.controller.create(req, tenant_id=self.project, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('trigger_create', {
                'name': 'test_trigger',
                'spec': {
                    'type': 'alarm_type',
                    'param_1': 'value1',
                    'param_2': 2
                },
                'description': None,
                'enabled': True,
                'severity': 'low',
                'state': None,
            })
        )

        expected = {'trigger': engine_response}
        self.assertEqual(expected, resp)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_create_with_bad_body(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_trigger'}

        req = self._post('/triggers', jsonutils.dumps(body))
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, tenant_id=self.project, body=body)

        self.assertEqual("Malformed request data, missing 'trigger' key "
                         "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_create_with_bad_type(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        type_name = 'unknown_type'
        body = {
            'trigger': {
                'name': 'test_trigger',
                'spec': {
                    'type': type_name,
                    'param': 'value'
                },
                'enabled': True,
            }
        }
        req = self._post('/triggers', jsonutils.dumps(body))

        error = senlin_exc.TriggerTypeNotFound(trigger_type=type_name)
        mock_call.side_effect = error

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('trigger_create',
             {'name': 'test_trigger',
              'spec': {'type': type_name, 'param': 'value'},
              'enabled': True,
              'state': None,
              'severity': None,
              'description': None}))

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('TriggerTypeNotFound', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_create_with_spec_validation_failed(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'trigger': {
                'name': 'test_trigger',
                'spec': {'type': 'alarm_type', 'param': 'value'},
                'enabled': True,
            }
        }
        req = self._post('/triggers', jsonutils.dumps(body))

        msg = 'Spec validation error (param): value'
        error = senlin_exc.SpecValidationFailed(message=msg)
        mock_call.side_effect = error

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('trigger_create',
             {'name': 'test_trigger', 'description': None,
              'spec': {'type': 'alarm_type', 'param': 'value'},
              'enabled': True, 'state': None, 'severity': None}))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SpecValidationFailed', resp.json['error']['type'])
        self.assertIsNone(resp.json['error']['traceback'])

    def test_create_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', False)
        body = {
            'trigger': {
                'name': 'test_trigger',
                'spec': {'type': 'alarm_type', 'param': 'value'},
            }
        }

        req = self._post('/triggers', jsonutils.dumps(body))
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_get_normal(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        trigger_id = 'FAKE_ID'
        req = self._get('/triggers/FAKE_ID')

        engine_resp = {
            'id': trigger_id,
            'name': 'test_trigger',
            'spec': {
                'type': 'alarm_type',
                'param_1': 'value1',
                'param_2': 2,
            },
            'enabled': True,
            'description': None,
            'severity': 'low',
            'state': 'ok',
        }

        mock_call.return_value = engine_resp

        result = self.controller.get(req, tenant_id=self.project,
                                     trigger_id=trigger_id)

        mock_call.assert_called_with(
            req.context, ('trigger_get', {'identity': trigger_id}))

        expected = {'trigger': engine_resp}
        self.assertEqual(expected, result)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_get_not_found(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        trigger_id = 'non-existent-trigger'
        req = self._get('/triggers/%(tid)s' % {'tid': trigger_id})

        error = senlin_exc.TriggerNotFound(trigger=trigger_id)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.project,
                                              trigger_id=trigger_id)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('TriggerNotFound', resp.json['error']['type'])

    def test_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        trigger_id = 'non-existent-trigger'
        req = self._get('/triggers/%(tid)s' % {'tid': trigger_id})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.project,
                                              trigger_id=trigger_id)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_delete_success(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        tid = 'FAKE_ID'
        req = self._delete('/triggers/FAKE_ID')

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete,
                          req, tenant_id=self.project, trigger_id=tid)

        mock_call.assert_called_with(
            req.context, ('trigger_delete', {'identity': tid,
                                             'force': False}))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_delete_not_found(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        tid = 'FAKE_ID'
        req = self._delete('/triggers/FAKE_ID')

        error = senlin_exc.TriggerNotFound(trigger=tid)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              trigger_id=tid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('TriggerNotFound', resp.json['error']['type'])

    def test_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        trigger_id = 'FAKE_ID'
        req = self._delete('/triggers/FAKE_ID')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              trigger_id=trigger_id)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
