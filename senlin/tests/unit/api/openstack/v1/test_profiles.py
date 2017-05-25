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
from senlin.api.openstack.v1 import profiles
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class ProfileControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(ProfileControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = profiles.ProfileController(options=cfgopts)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_index_normal(self, mock_call, mock_parse,
                                  mock_enforce):
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
                u'created_time': u'2015-02-24T19:17:22Z',
                u'updated_time': None,
                u'metadata': {},
            }
        ]

        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.index(req)

        self.assertEqual(engine_resp, result['profiles'])
        mock_parse.assert_called_once_with(
            'ProfileListRequest', req, {'project_safe': True})
        mock_call.assert_called_once_with(req.context, 'profile_list', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_index_whitelists_params(self, mock_call, mock_parse,
                                             mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        marker_uuid = uuidutils.generate_uuid()
        params = {
            'name': 'foo',
            'type': 'fake_type',
            'limit': 20,
            'marker': marker_uuid,
            'sort': 'name:asc',
            'global_project': False
        }
        req = self._get('/profiles', params=params)

        mock_call.return_value = []
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.index(req)

        self.assertEqual([], result['profiles'])
        mock_parse.assert_called_once_with(
            'ProfileListRequest', req,
            {
                'sort': 'name:asc',
                'name': ['foo'],
                'limit': '20',
                'marker': marker_uuid,
                'type': ['fake_type'],
                'project_safe': True
            })
        mock_call.assert_called_once_with(req.context, 'profile_list', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_index_whitelist_bad_params(self, mock_call, mock_parse,
                                                mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/profiles', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertFalse(mock_parse.called)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_index_global_project_not_bool(self, mock_call,
                                                   mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'No'}
        req = self._get('/profiles', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'No' specified for 'global_project'",
                         six.text_type(ex))
        self.assertFalse(mock_parse.called)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_index_limit_non_int(self, mock_call, mock_parse,
                                         mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'limit': 'abc'}
        req = self._get('/profiles', params=params)

        mock_parse.side_effect = exc.HTTPBadRequest("bad limit")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("bad limit", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ProfileListRequest', req, mock.ANY)
        self.assertFalse(mock_call.called)

    def test_profile_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/profiles')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_create_success(self, mock_call, mock_parse,
                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'profile': {
                'name': 'test_profile',
                'spec': {
                    'type': 'test_profile_type',
                    'version': '1.0',
                    'properties': {
                        'param_1': 'value1',
                        'param_2': 2,
                    },
                },
                'metadata': {},
            }
        }

        engine_response = {
            'id': 'xxxx-yyyy-zzzz',
            'name': 'test_profile',
            'type': 'test_profile_type',
            'spec': {
                'type': 'test_profile_type',
                'version': '1.0',
                'properties': {
                    'param_1': 'value1',
                    'param_2': 2,
                }
            },
            'metadata': {},
        }

        req = self._post('/profiles', jsonutils.dumps(body))
        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = self.controller.create(req, body=body)

        self.assertEqual(engine_response, resp['profile'])
        mock_parse.assert_called_once_with(
            'ProfileCreateRequest', req, body, 'profile')
        mock_call.assert_called_once_with(
            req.context, 'profile_create', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_create_with_no_profile(self, mock_call, mock_parse,
                                            mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_profile'}

        req = self._post('/profiles', jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad body")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("bad body", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ProfileCreateRequest', mock.ANY, body, 'profile')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_create_with_profile_no_spec(self, mock_call,
                                                 mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'profile': {'name': 'test_profile'}}

        req = self._post('/profiles', jsonutils.dumps(body))
        mock_parse.side_effect = exc.HTTPBadRequest("miss spec")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("miss spec", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ProfileCreateRequest', mock.ANY, body, 'profile')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_create_with_bad_type(self, mock_call,
                                          mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        type_name = 'unknown_type'
        body = {
            'profile': {
                'name': 'test_profile',
                'spec': {
                    'type': type_name,
                    'version': '1.0',
                    'properties': {'param': 'value'},
                },
                'metadata': {},
            }
        }
        req = self._post('/profiles', jsonutils.dumps(body))

        obj = mock.Mock()
        mock_parse.return_value = obj
        error = senlin_exc.ResourceNotFound(type='profile_type', id=type_name)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])
        mock_parse.assert_called_once_with(
            'ProfileCreateRequest', mock.ANY, body, 'profile')
        mock_call.assert_called_once_with(
            req.context, 'profile_create', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_create_with_spec_validation_failed(self, mock_call,
                                                        mock_parse,
                                                        mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'profile': {
                'name': 'test_profile',
                'spec': {
                    'type': 'test_profile_type',
                    'version': '1.0',
                    'properties': {'param': 'value'},
                },
                'metadata': {},
            }
        }
        req = self._post('/profiles', jsonutils.dumps(body))
        obj = mock.Mock()
        mock_parse.return_value = obj

        msg = 'Spec validation error (param): value'
        error = senlin_exc.InvalidSpec(message=msg)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])
        mock_parse.assert_called_once_with(
            'ProfileCreateRequest', mock.ANY, body, 'profile')
        mock_call.assert_called_once_with(
            req.context, 'profile_create', obj)

    def test_profile_create_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', False)
        body = {
            'profile': {
                'name': 'test_profile',
                'spec': {
                    'type': 'test_profile_type',
                    'version': '1.0',
                    'properties': {'param': 'value'},
                }
            }
        }

        req = self._post('/profiles', jsonutils.dumps(body))
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_get_normal(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._get('/profiles/%(profile_id)s' % {'profile_id': pid})

        engine_resp = {
            u'id': u'aaaa-bbbb-cccc',
            u'name': u'profile-1',
            u'type': u'test_profile_type',
            u'spec': {
                u'param_1': u'value1',
                u'param_2': u'value2',
            },
            u'created_time': u'2015-02-24T19:17:22Z',
            u'updated_time': None,
            u'metadata': {},
        }

        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.get(req, profile_id=pid)

        self.assertEqual(engine_resp, result['profile'])
        mock_parse.assert_called_once_with(
            'ProfileGetRequest', req, {'identity': pid})
        mock_call.assert_called_once_with(
            req.context, 'profile_get', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_get_not_found(self, mock_call, mock_parse,
                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'non-existent-profile'
        req = self._get('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceNotFound(type='profile', id=pid)
        mock_call.side_effect = shared.to_remote_error(error)
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, profile_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

        mock_parse.assert_called_once_with(
            'ProfileGetRequest', mock.ANY, {'identity': pid})
        mock_call.assert_called_once_with(
            req.context, 'profile_get', obj)

    def test_profile_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        pid = 'non-existent-profile'
        req = self._get('/profiles/%(profile_id)s' % {'profile_id': pid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, profile_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_update_normal(self, mock_call, mock_parse,
                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {
                'name': 'profile-2',
                'metadata': {
                    'author': 'thomas j',
                }
            }
        }

        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        engine_resp = {
            u'id': pid,
            u'name': u'profile-2',
            u'type': u'test_profile_type',
            u'created_time': u'2015-02-25T16:20:13Z',
            u'updated_time': None,
            u'metadata': {u'author': u'thomas j'},
        }

        mock_call.return_value = engine_resp
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.update(req, profile_id=pid, body=body)

        self.assertEqual(engine_resp, result['profile'])
        mock_parse.assert_called_once_with(
            'ProfileUpdateRequest', req, mock.ANY)
        mock_call.assert_called_once_with(
            req.context, 'profile_update', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_update_no_body(self, mock_call, mock_parse,
                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad body")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, profile_id=pid, body=body)

        self.assertEqual("Malformed request data, missing 'profile' key "
                         "in request body.", six.text_type(ex))
        self.assertFalse(mock_parse.called)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_update_no_name(self, mock_call, mock_parse,
                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {'metadata': {'author': 'thomas j'}}
        }

        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        mock_call.return_value = {}
        obj = mock.Mock()
        mock_parse.return_value = obj

        result = self.controller.update(req, profile_id=pid, body=body)

        self.assertEqual({}, result['profile'])
        mock_parse.assert_called_once_with(
            'ProfileUpdateRequest', req, mock.ANY)
        mock_call.assert_called_once_with(
            req.context, 'profile_update', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_update_with_unexpected_field(self, mock_call,
                                                  mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {
                'name': 'new_profile',
                'metadata': {'author': 'john d'},
                'foo': 'bar'
            }
        }
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, profile_id=pid, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ProfileUpdateRequest', req, mock.ANY)
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_update_not_found(self, mock_call, mock_parse,
                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'non-existent-profile'
        body = {
            'profile': {
                'name': 'new_profile',
                'metadata': {'author': 'john d'},
            }
        }
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='profile', id=pid)
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, profile_id=pid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_profile_update_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {'name': 'test_profile', 'spec': {'param5': 'value5'}},
        }
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, profile_id=pid,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_delete_success(self, mock_call, mock_parse,
                                    mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        obj = mock.Mock()
        mock_parse.return_value = obj

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, profile_id=pid)

        mock_parse.assert_called_once_with(
            'ProfileDeleteRequest', req, {'identity': pid})
        mock_call.assert_called_once_with(req.context, 'profile_delete', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_delete_not_found(self, mock_call, mock_parse,
                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceNotFound(type='profile', id=pid)
        mock_call.side_effect = shared.to_remote_error(error)
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, profile_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

        mock_parse.assert_called_once_with(
            'ProfileDeleteRequest', mock.ANY, {'identity': pid})
        mock_call.assert_called_once_with(
            req.context, 'profile_delete', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_delete_resource_in_use(self, mock_call, mock_parse,
                                            mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceInUse(type='profile', id=pid,
                                         reason='still in use')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, profile_id=pid)

        self.assertEqual(409, resp.json['code'])
        self.assertEqual('ResourceInUse', resp.json['error']['type'])

    def test_profile_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, profile_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_validate_version_mismatch(self, mock_call, mock_parse,
                                               mock_enforce):
        body = {
            'profile': {}
        }
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.1')

        ex = self.assertRaises(senlin_exc.MethodVersionNotFound,
                               self.controller.validate,
                               req, body=body)

        self.assertFalse(mock_parse.called)
        self.assertFalse(mock_call.called)
        self.assertEqual("API version '1.1' is not supported on this "
                         "method.", six.text_type(ex))

    def test_profile_validate_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', False)

        body = {
            'profile': {
                'name': 'test_profile',
                'spec': {
                    'type': 'test_profile_type',
                    'version': '1.0',
                    'properties': {
                        'param_1': 'value1',
                        'param_2': 2,
                    },
                },
                'metadata': {},
            }
        }

        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.validate,
                                              req, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_validate_no_body(self, mock_call, mock_parse,
                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {'foo': 'bar'}
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("bad param", six.text_type(ex))

        mock_parse.assert_called_once_with(
            'ProfileValidateRequest', req, body, 'profile')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_validate_no_spec(self, mock_call, mock_parse,
                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'profile': {}
        }
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')

        mock_parse.side_effect = exc.HTTPBadRequest("miss spec")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("miss spec", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ProfileValidateRequest', req, body, 'profile')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_validate_unsupported_field(self, mock_call,
                                                mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'profile': {
                'spec': {'type': 'os.nova.server',
                         'version': '1.0'},
                'foo': 'bar'
            }
        }
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')
        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        mock_parse.assert_called_once_with(
            'ProfileValidateRequest', req, body, 'profile')
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_profile_validate_invalid_spec(self, mock_call,
                                           mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'profile': {
                'spec': {
                    'type': 'os.nova.server',
                    'version': '1.0'
                }
            }
        }

        req = self._post('/profiles/validate', jsonutils.dumps(body),
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
    def test_profile_validate_success(self, mock_call,
                                      mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        spec = {
            'spec': {
                'type': 'os.heat.stack',
                'version': '1.0'
            }
        }
        body = {
            'profile': spec
        }

        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')

        obj = mock.Mock()
        mock_parse.return_value = obj
        mock_call.return_value = spec

        result = self.controller.validate(req, body=body)

        self.assertEqual(spec, result['profile'])
        mock_parse.assert_called_once_with(
            'ProfileValidateRequest', req, body, 'profile')
        mock_call.assert_called_with(
            req.context, 'profile_validate', obj)
