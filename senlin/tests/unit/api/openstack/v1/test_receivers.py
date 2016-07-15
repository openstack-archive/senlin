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
from senlin.common.i18n import _
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


class ReceiverDataTest(base.SenlinTestCase):
    def test_receiver_data(self):
        body = {
            'name': 'test_receiver',
            'type': 'webhook',
            'cluster_id': 'FAKE_CLUSTER',
            'action': 'test_action',
            'actor': {
                'user_id': 'test_user_id',
                'password': 'test_pass',
            },
            'params': {
                'test_param': 'test_value'
            },
        }
        data = receivers.ReceiverData(body)
        self.assertEqual(body['name'], data.name())
        self.assertEqual(body['type'], data.type_name())
        self.assertEqual(body['cluster_id'], data.cluster_id())
        self.assertEqual(body['action'], data.action())
        self.assertEqual(body['actor'], data.actor())
        self.assertEqual(body['params'], data.params())

    def test_required_fields_missing(self):
        body = {'fake_field': 'fake_value'}
        data = receivers.ReceiverData(body)
        self.assertRaises(exc.HTTPBadRequest, data.name)
        self.assertRaises(exc.HTTPBadRequest, data.type_name)
        self.assertRaises(exc.HTTPBadRequest, data.cluster_id)
        self.assertRaises(exc.HTTPBadRequest, data.action)


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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        default_args = {'limit': None, 'marker': None, 'sort': None,
                        'filters': None, 'project_safe': True}

        mock_call.assert_called_with(req.context,
                                     ('receiver_list', default_args))

        expected = {'receivers': engine_resp}
        self.assertEqual(expected, result)

    def test_receiver_index_whitelists_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 20,
            'marker': 'fake marker',
            'sort': 'fake sorting string',
        }
        req = self._get('/receivers', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(5, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort', engine_args)

    def test_receiver_index_whitelists_invalid_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/receivers', params=params)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_whitelist_filter_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'name': 'test',
            'type': 'webhook',
            'cluster_id': 'test-id',
            'action': 'fake-action',
        }
        req = self._get('/receivers', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(4, len(filters))
        self.assertIn('name', filters)
        self.assertIn('type', filters)
        self.assertIn('cluster_id', filters)
        self.assertIn('action', filters)

    def test_receiver_index_whitelist_filter_invalid_params(self,
                                                            mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/receivers', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_limit_non_int(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'receiver_list',
                                     return_value=[])

        params = {'limit': 'abc'}
        req = self._get('/receivers', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)
        self.assertIn("Invalid value 'abc' specified for 'limit'",
                      six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_receiver_index_global_project(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'receiver_list',
                                     return_value=[])

        params = {'global_project': True}
        req = self._get('/receivers', params=params)
        self.controller.index(req)
        mock_call.assert_called_once_with(mock.ANY,
                                          filters=mock.ANY,
                                          project_safe=False)

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
                'action': 'test_action',
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
            'action': 'test_action',
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(
            req.context,
            ('receiver_create', {
                'name': 'test_receiver',
                'type_name': 'webhook',
                'cluster_id': 'FAKE_ID',
                'action': 'test_action',
                'actor': {
                    'user_id': 'test_user_id',
                    'password': 'test_pass'
                },
                'params': {'test_param': 'test_value'},
            })
        )

        expected = {'receiver': engine_response}
        self.assertEqual(expected, resp)

    def test_receiver_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_receiver'}

        req = self._post('/receivers', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Malformed request data, missing 'receiver' key "
                         "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_receiver_create_with_bad_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        r_type = 'unsupported'
        body = {
            'receiver': {
                'name': 'test_receiver',
                'type': r_type,
                'cluster_id': 'FAKE_CLUSTER',
                'action': 'test_action',
            }
        }
        req = self._post('/receivers', jsonutils.dumps(body))

        msg = _('receiver obj_type (%s) is unsupported.') % r_type
        error = senlin_exc.BadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        expected_args = body['receiver']
        type_name = expected_args.pop('type')
        expected_args['type_name'] = type_name
        expected_args['actor'] = None
        expected_args['params'] = None
        mock_call.assert_called_once_with(req.context,
                                          ('receiver_create', expected_args))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('BadRequest', resp.json['error']['type'])

    def test_receiver_create_with_cluster_id_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        cluster_id = 'FAKE_ID'
        body = {
            'receiver': {
                'name': 'test_receiver',
                'type': 'webhook',
                'cluster_id': cluster_id,
                'action': 'test_action',
            }
        }
        req = self._post('/receivers', jsonutils.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cluster_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        expected_args = body['receiver']
        type_name = expected_args.pop('type')
        expected_args['type_name'] = type_name
        expected_args['actor'] = None
        expected_args['params'] = None
        mock_call.assert_called_once_with(req.context,
                                          ('receiver_create', expected_args))
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

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

        msg = _('Illegal action (%s) specified.') % action
        error = senlin_exc.BadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        expected = body['receiver']
        type_name = expected.pop('type')
        expected['type_name'] = type_name
        expected['actor'] = None
        expected['params'] = None
        mock_call.assert_called_once_with(req.context,
                                          ('receiver_create', expected))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('BadRequest', resp.json['error']['type'])

    def test_receiver_create_unapplicable_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        action = 'BAD'
        body = {
            'receiver': {
                'name': 'test_receiver',
                'type': 'webhook',
                'cluster_id': 'FAKE_CLUSTER',
                'action': action,
            }
        }
        req = self._post('/receivers', jsonutils.dumps(body))

        msg = 'Action BAD is not applicable clusters.'
        error = senlin_exc.BadRequest(msg=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        expected = body['receiver']
        type_name = expected.pop('type')
        expected['type_name'] = type_name
        expected['actor'] = None
        expected['params'] = None
        mock_call.assert_called_once_with(req.context,
                                          ('receiver_create', expected))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('BadRequest', resp.json['error']['type'])

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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.get(req, receiver_id=wid)

        mock_call.assert_called_once_with(
            req.context, ('receiver_get', {'identity': wid,
                                           'project_safe': True}))

        expected = {'receiver': engine_resp}
        self.assertEqual(expected, result)

    def test_receiver_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        wid = 'non-existent-receiver'
        req = self._get('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        error = senlin_exc.ReceiverNotFound(receiver=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, receiver_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ReceiverNotFound', resp.json['error']['type'])

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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, receiver_id=wid)

        mock_call.assert_called_with(
            req.context,
            ('receiver_delete', {'identity': wid}))

    def test_receiver_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        error = senlin_exc.ReceiverNotFound(receiver=wid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, receiver_id=wid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ReceiverNotFound', resp.json['error']['type'])

    def test_receiver_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        wid = 'aaaa-bbbb-cccc'
        req = self._delete('/receivers/%(receiver_id)s' % {'receiver_id': wid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, receiver_id=wid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
