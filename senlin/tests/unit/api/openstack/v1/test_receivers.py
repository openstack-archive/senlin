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

from senlin.api.common import util
from senlin.api.middleware import fault
from senlin.api.openstack.v1 import receivers
from senlin.common import exception as senlin_exc
from senlin.common import policy
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

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_normal(self, mock_call, mock_parse, mock_enforce):
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

        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.index(req)

        self.assertEqual(engine_resp, result['receivers'])
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req, mock.ANY)
        mock_call.assert_called_with(req.context, 'receiver_list', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_whitelists_params(self, mock_call,
                                              mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        marker = 'cac6d9c1-cb4e-4884-ba2a-3cbc72d84aaf'
        params = {
            'limit': 20,
            'marker': marker,
            'sort': 'name:desc',
            'name': 'receiver01',
            'type': 'webhook',
            'cluster_id': '123abc',
            'action': 'CLUSTER_RESIZE',
            'user': 'user123'
        }
        req = self._get('/receivers', params=params)

        mock_call.return_value = []
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.index(req)

        self.assertEqual([], result['receivers'])
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req,
            {
                'sort': 'name:desc',
                'name': ['receiver01'],
                'action': ['CLUSTER_RESIZE'],
                'limit': '20',
                'marker': marker,
                'cluster_id': ['123abc'],
                'type': ['webhook'],
                'project_safe': True,
                'user': ['user123']
            })
        mock_call.assert_called_with(req.context, 'receiver_list', mock.ANY)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_whitelists_invalid_params(self, mock_call,
                                                      mock_parse,
                                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/receivers', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertFalse(mock_parse.called)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_invalid_type(self, mock_call,
                                         mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'type': 'bogus'}
        req = self._get('/receivers', params=params)

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req,
            {
                'type': ['bogus'],
                'project_safe': True
            })
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_invalid_action(self, mock_call,
                                           mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'action': 'bogus'}
        req = self._get('/receivers', params=params)

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req,
            {
                'action': ['bogus'],
                'project_safe': True
            })
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_limit_non_int(self, mock_call,
                                          mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'limit': 'abc'}
        req = self._get('/receivers', params=params)

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req,
            {
                'limit': 'abc',
                'project_safe': True
            })
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_invalid_sort(self, mock_call,
                                         mock_parse, mock_enforce):

        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'sort': 'bogus:foo'}
        req = self._get('/receivers', params=params)

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req,
            {
                'sort': 'bogus:foo',
                'project_safe': True
            })
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_index_global_project(self, mock_call,
                                           mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'global_project': True}
        req = self._get('/receivers', params=params)

        mock_call.return_value = []
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.index(req)

        self.assertEqual([], result['receivers'])
        mock_parse.assert_called_once_with(
            'ReceiverListRequest', req, {'project_safe': False})
        mock_call.assert_called_once_with(
            req.context, 'receiver_list', obj)

    def test_receiver_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/receivers')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index, req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_create_success(self, mock_call,
                                     mock_parse, mock_enforce):
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
        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = self.controller.create(req, body=body)

        self.assertEqual(engine_response, resp['receiver'])
        mock_parse.assert_called_once_with(
            'ReceiverCreateRequest', req, body, 'receiver')
        mock_call.assert_called_with(
            req.context, 'receiver_create', obj.receiver)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_create_with_bad_body(self, mock_call, mock_parse,
                                           mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_receiver'}

        req = self._post('/receivers', jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverCreateRequest', req, body, 'receiver')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_create_missing_required_field(self, mock_call,
                                                    mock_parse,
                                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'receiver': {
                'name': 'test_receiver',
                'cluster_id': 'FAKE_CLUSTER',
                'action': 'CLUSTER_RESIZE',
            }
        }

        req = self._post('/receivers', jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("miss type")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("miss type", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverCreateRequest', req, body, 'receiver')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_create_with_bad_type(self, mock_call,
                                           mock_parse, mock_enforce):
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

        mock_parse.side_effect = exc.HTTPBadRequest("bad type")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("bad type", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverCreateRequest', req, body, 'receiver')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_create_illegal_action(self, mock_call,
                                            mock_parse, mock_enforce):
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

        mock_parse.side_effect = exc.HTTPBadRequest("bad action")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("bad action", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverCreateRequest', req, body, 'receiver')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_get_normal(self, mock_call, mock_parse, mock_enforce):
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

        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.get(req, receiver_id=wid)

        self.assertEqual(engine_resp, result['receiver'])
        mock_parse.assert_called_once_with(
            'ReceiverGetRequest', req, {'identity': wid})
        mock_call.assert_called_with(req.context, 'receiver_get', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_get_not_found(self, mock_call, mock_parse,
                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        wid = 'non-existent-receiver'
        req = self._get('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        error = senlin_exc.ResourceNotFound(type='receiver', id=wid)
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

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_update_normal(self, mock_call, mock_parse,
                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        wid = 'aaaa-bbbb-cccc'
        body = {
            'receiver': {
                'name': 'receiver-2',
                'params': {
                    'count': 10,
                }
            }
        }

        req = self._put('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                        jsonutils.dumps(body))

        engine_response = {
            u'id': wid,
            u'name': u'receiver-2',
            u'created_time': u'2015-02-25T16:20:13Z',
            u'updated_time': None,
            u'params': {u'count': 10},
        }

        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.update(req, receiver_id=wid, body=body)

        self.assertEqual(engine_response, result['receiver'])
        mock_parse.assert_called_once_with(
            'ReceiverUpdateRequest', req, mock.ANY)
        mock_call.assert_called_once_with(
            req.context, 'receiver_update', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_update_no_body(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        wid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._put('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                        jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad body")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, receiver_id=wid, body=body)

        self.assertEqual("Malformed request data, missing 'receiver' key "
                         "in request body.", six.text_type(ex))
        self.assertFalse(mock_parse.called)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_update_no_name(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        wid = 'aaaa-bbbb-cccc'
        body = {
            'receiver': {'params': {'count': 10}}
        }

        req = self._put('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                        jsonutils.dumps(body))
        mock_call.return_value = {}
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.update(req, receiver_id=wid, body=body)

        self.assertEqual({}, result['receiver'])
        mock_parse.assert_called_once_with(
            'ReceiverUpdateRequest', req, mock.ANY)
        mock_call.assert_called_once_with(
            req.context, 'receiver_update', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_update_with_unexpected_field(self, mock_call,
                                                   mock_parse,
                                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        wid = 'aaaa-bbbb-cccc'
        body = {
            'receiver': {
                'name': 'receiver-2',
                'params': {'count': 10},
            }
        }
        req = self._put('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                        jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, receiver_id=wid, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverUpdateRequest', req, mock.ANY)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_update_not_found(self, mock_call, mock_parse,
                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        wid = 'non-existent-receiver'
        body = {
            'receiver': {
                'name': 'receiver-2',
                'params': {'count': 10},
            }
        }
        req = self._put('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                        jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='webhook', id=wid)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, receiver_id=wid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_receiver_update_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        wid = 'aaaa-bbbb-cccc'
        body = {
            'receiver': {'name': 'receiver-2', 'spec': {'param5': 'value5'}},
        }
        req = self._put('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                        jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, profile_id=wid,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_delete_success(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        obj = mock.Mock()
        mock_parse.return_value = obj

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, receiver_id=wid)
        mock_parse.assert_called_once_with(
            'ReceiverDeleteRequest', req, {'identity': wid})
        mock_call.assert_called_once_with(
            req.context, 'receiver_delete', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_delete_err_malformed_receiver_id(self, mock_call,
                                                       mock_parse,
                                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = {'k1': 'v1'}
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        mock_parse.side_effect = exc.HTTPBadRequest("bad identity")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.delete, req,
                               receiver_id=wid)
        self.assertEqual("bad identity", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverDeleteRequest', req, {'identity': wid})
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_delete_not_found(self, mock_call, mock_parse,
                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        error = senlin_exc.ResourceNotFound(type='receiver', id=wid)
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

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_notify_success(self, mock_call, mock_parse,
                                     mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'notify')
        wid = 'aaaa-bbbb-cccc'
        req = self._post('/receivers/%(receiver_id)s/notify' % {
            'receiver_id': wid}, None)

        obj = mock.Mock()
        mock_parse.return_value = obj

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.notify, req, receiver_id=wid)
        mock_parse.assert_called_once_with(
            'ReceiverNotifyRequest', req, {'identity': wid})
        mock_call.assert_called_with(req.context, 'receiver_notify', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_notify_err_malformed_receiver_id(self, mock_call,
                                                       mock_parse,
                                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'notify', True)
        wid = {'k1': 'v1'}
        req = self._post('/receivers/%(receiver_id)s' % {'receiver_id': wid},
                         None)

        mock_parse.side_effect = exc.HTTPBadRequest("bad identity")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.notify, req,
                               receiver_id=wid)
        self.assertEqual("bad identity", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ReceiverNotifyRequest', req, {'identity': wid})
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_receiver_notify_not_found(self, mock_call, mock_parse,
                                       mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'notify', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._post('/receivers/%(receiver_id)s/notify' % {
            'receiver_id': wid}, None)

        error = senlin_exc.ResourceNotFound(type='receiver', id=wid)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.notify,
                                              req, receiver_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])
