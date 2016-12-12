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

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import receivers
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.objects.requests import receivers as vorr
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class ReceiverControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(ReceiverControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = receivers.ReceiverController(options=cfgopts)

    def test_receiver_index_normal(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/receivers')

        engine_resp = [
            {
                u'id': u'aaaa-bbbb-cccc',
                u'name': u'test-receiver',
                u'type': u'webhook',
                u'user': u'admin',
                u'project': u'123456abcd3555',
                u'domain': u'default',
                u'cluster_id': u'FAKE_CLUSTER',
                u'action': u'test-action',
                u'actor': {
                    u'user_id': u'test-user-id',
                    u'password': u'test-pass',
                },
                u'created_time': u'2015-02-24T19:17:22Z',
                u'params': {},
                'channel': {
                    'alarm_url': 'http://somewhere/on/earth',
                },
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        mock_call.assert_called_with(req.context, 'receiver_list2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorr.ReceiverListRequest)
        self.assertTrue(request.project_safe)

        expected = {'receivers': engine_resp}
        self.assertEqual(expected, result)

    def test_receiver_index_whitelists_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        marker = 'cac6d9c1-cb4e-4884-ba2a-3cbc72d84aaf'
        params = {
            'limit': 20,
            'marker': marker,
            'sort': 'name:desc',
            'name': 'receiver01',
            'type': 'webhook',
            'cluster_id': '123abc',
            'action': 'CLUSTER_RESIZE'
        }
        req = self._get('/receivers', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.return_value = []

        self.controller.index(req)
        mock_call.assert_called_with(req.context, 'receiver_list2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorr.ReceiverListRequest)
        self.assertTrue(request.project_safe)
        self.assertEqual(20, request.limit)
        self.assertEqual(marker, request.marker)
        self.assertEqual('name:desc', request.sort)
        self.assertEqual(['receiver01'], request.name)
        self.assertEqual(['webhook'], request.type)
        self.assertEqual(['123abc'], request.cluster_id)
        self.assertEqual(['CLUSTER_RESIZE'], request.action)

    def test_receiver_index_whitelists_invalid_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/receivers', params=params)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_invalid_type(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=[])

        params = {'type': 'bogus'}
        req = self._get('/receivers', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertIn("Field value bogus is invalid",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_invalid_action(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=[])

        params = {'action': 'bogus'}
        req = self._get('/receivers', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertIn("Field value bogus is invalid",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_limit_non_int(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=[])

        params = {'limit': 'abc'}
        req = self._get('/receivers', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertIn("invalid literal for int() with base 10: 'abc'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_invalid_sort(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=[])

        params = {'sort': 'bogus:foo'}
        req = self._get('/receivers', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertIn("unsupported sort dir 'foo' for 'sort'.",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_global_project(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=[])

        params = {'global_project': True}
        req = self._get('/receivers', params=params)
        self.controller.index(req)
        mock_call.assert_called_once_with(req.context,
                                          'receiver_list2',
                                          mock.ANY)

    def test_receiver_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/receivers')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index, req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_receiver_create_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'receiver': {
                'name': 'test_receiver',
                'type': 'webhook',
                'cluster_id': 'FAKE_ID',
                'action': 'CLUSTER_RESIZE',
                'actor': {
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
            'name': 'test_receiver',
            'type': 'webhook',
            'cluster_id': 'FAKE_ID',
            'action': 'CLUSTER_RESIZE',
            'actor': {
                'user_id': 'test_user_id',
                'password': 'test_pass',
            },
            'params': {
                'test_param': 'test_value'
            },
            'channel': {
                'alarm_url': 'http://somewhere/on/earth',
            },
        }

        req = self._post('/receivers', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(req.context, 'receiver_create2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorr.ReceiverCreateRequestBody)
        self.assertEqual('test_receiver', request.name)
        self.assertEqual('webhook', request.type)
        self.assertEqual('FAKE_ID', request.cluster_id)
        self.assertEqual('CLUSTER_RESIZE', request.action)
        self.assertEqual({'user_id': 'test_user_id',
                          'password': 'test_pass'}, request.actor)
        self.assertEqual({'test_param': 'test_value'}, request.params)

        expected = {'receiver': engine_response}
        self.assertEqual(expected, resp)

    def test_receiver_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_receiver'}

        req = self._post('/receivers', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Request body missing 'receiver' key.",
                         six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_receiver_create_missing_required_field(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'receiver': {
                'name': 'test_receiver',
                'cluster_id': 'FAKE_CLUSTER',
                'action': 'CLUSTER_RESIZE',
            }
        }

        req = self._post('/receivers', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("'type' is a required property", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_create_with_bad_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        r_type = 'unsupported'
        body = {
            'receiver': {
                'name': 'test_receiver',
                'type': r_type,
                'cluster_id': 'FAKE_CLUSTER',
                'action': 'CLUSTER_RESIZE',
            }
        }

        req = self._post('/receivers', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Value 'unsupported' is not acceptable for field "
                         "'type'.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_create_illegal_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        action = 'illegal_action'
        body = {
            'receiver': {
                'name': 'test_receiver',
                'type': 'webhook',
                'cluster_id': 'FAKE_CLUSTER',
                'action': action,
            }
        }
        req = self._post('/receivers', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Value 'illegal_action' is not acceptable for field "
                         "'action'.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_get_normal(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._get('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        engine_resp = {
            u'id': u'aaaa-bbbb-cccc',
            u'name': u'test-receiver',
            u'type': u'webhook',
            u'user': u'admin',
            u'project': u'123456abcd3555',
            u'domain': u'default',
            u'cluster_id': u'FAKE_CLUSTER',
            u'action': u'test-action',
            u'actor': {
                u'user_id': u'test-user-id',
                u'password': u'test-pass',
            },
            u'created_time': u'2015-02-24T19:17:22Z',
            u'params': {},
            u'channel': {
                u'alarm_url': u'http://somewhere/on/earth',
            }
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        result = self.controller.get(req, receiver_id=wid)
        mock_call.assert_called_with(req.context, 'receiver_get2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorr.ReceiverGetRequest)
        self.assertEqual(wid, request.identity)

        expected = {'receiver': engine_resp}
        self.assertEqual(expected, result)

    def test_receiver_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        wid = 'non-existent-receiver'
        req = self._get('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        error = senlin_exc.ResourceNotFound(type='receiver', id=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, receiver_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_receiver_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        wid = 'non-existent-receiver'
        req = self._get('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, receiver_id=wid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_receiver_delete_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, receiver_id=wid)
        mock_call.assert_called_with(req.context, 'receiver_delete2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorr.ReceiverDeleteRequest)
        self.assertEqual(wid, request.identity)

    def test_receiver_delete_err_malformed_receiver_id(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = {'k1': 'v1'}
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.delete, req,
                               receiver_id=wid)
        self.assertEqual("A string is required in field identity, "
                         "not a dict", six.text_type(ex))

    def test_receiver_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        error = senlin_exc.ResourceNotFound(type='receiver', id=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, receiver_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_receiver_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, receiver_id=wid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_receiver_notify_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'notify')
        wid = 'aaaa-bbbb-cccc'
        req = self._post('/receivers/%(receiver_id)s/notify' % {
            'receiver_id': wid}, None)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.notify, req, receiver_id=wid)

        mock_call.assert_called_with(req.context, 'receiver_notify2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorr.ReceiverNotifyRequest)
        self.assertEqual(wid, request.identity)

    def test_receiver_notify_err_malformed_receiver_id(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'notify', True)
        wid = {'k1': 'v1'}
        req = self._post('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                         None)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.notify, req,
                               receiver_id=wid)
        self.assertEqual("A string is required in field identity, "
                         "not a dict", six.text_type(ex))

    def test_receiver_notify_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'notify')
        wid = 'aaaa-bbbb-cccc'
        req = self._post('/receivers/%(receiver_id)s/notify' % {
            'receiver_id': wid}, None)

        error = senlin_exc.ResourceNotFound(type='receiver', id=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.notify,
                                              req, receiver_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])
