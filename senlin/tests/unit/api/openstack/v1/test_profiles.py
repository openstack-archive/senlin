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
from senlin.api.openstack.v1 import profiles
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
from senlin.common import policy
from senlin.objects.requests import profiles as vorp
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
                u'created_time': u'2015-02-24T19:17:22Z',
                u'updated_time': None,
                u'metadata': {},
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        result = self.controller.index(req)
        mock_call.assert_called_with(req.context, 'profile_list2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileListRequest)
        self.assertTrue(request.project_safe)
        self.assertFalse(request.obj_attr_is_set('name'))
        self.assertFalse(request.obj_attr_is_set('type'))
        self.assertFalse(request.obj_attr_is_set('limit'))
        self.assertFalse(request.obj_attr_is_set('marker'))
        self.assertFalse(request.obj_attr_is_set('sort'))

        expected = {'profiles': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_index_whitelists_params(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=[])

        self.controller.index(req)

        mock_call.assert_called_with(req.context, 'profile_list2', mock.ANY)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileListRequest)
        self.assertEqual(['foo'], request.name)
        self.assertEqual(['fake_type'], request.type)
        self.assertEqual(20, request.limit)
        self.assertEqual(marker_uuid, request.marker)
        self.assertEqual('name:asc', request.sort)
        self.assertTrue(request.project_safe)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_profile_index_whitelist_bad_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/profiles', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("Invalid parameter balrog", str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_profile_index_global_project_not_bool(self, mock_call,
                                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'No'}
        req = self._get('/profiles', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'No' specified for 'global_project'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_profile_index_limit_non_int(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)

        params = {'limit': 'abc'}
        req = self._get('/profiles', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("invalid literal for int() with base 10: 'abc'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/profiles')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_profile_create_success(self, mock_enforce):
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(req.context, 'profile_create2', mock.ANY)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileCreateRequest)

        expected = {'profile': engine_response}
        self.assertEqual(expected, resp)

    def test_profile_create_with_no_profile(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_profile'}

        req = self._post('/profiles', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Request body missing 'profile' key.",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_create_with_profile_no_spec(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'profile': {'name': 'test_profile'}}

        req = self._post('/profiles', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("'spec' is a required property",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_create_with_bad_type(self, mock_enforce):
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

        error = senlin_exc.ResourceNotFound(type='profile_type', id=type_name)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        mock_call.assert_called_once_with(req.context, 'profile_create2',
                                          mock.ANY)
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_profile_create_with_spec_validation_failed(self, mock_enforce):
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

        msg = 'Spec validation error (param): value'
        error = senlin_exc.InvalidSpec(message=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)
        mock_call.assert_called_once_with(req.context, 'profile_create2',
                                          mock.ANY)
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])

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

    def test_profile_get_normal(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        result = self.controller.get(req, profile_id=pid)

        mock_call.assert_called_with(req.context, 'profile_get2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileGetRequest)
        self.assertEqual(pid, request.identity)

        expected = {'profile': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'non-existent-profile'
        req = self._get('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceNotFound(type='profile', id=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, profile_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_profile_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        pid = 'non-existent-profile'
        req = self._get('/profiles/%(profile_id)s' % {'profile_id': pid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, profile_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_profile_update_normal(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)
        result = self.controller.update(req, profile_id=pid, body=body)
        mock_call.assert_called_with(req.context, 'profile_update2', mock.ANY)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileUpdateRequest)
        self.assertIsInstance(request.profile, vorp.ProfileUpdateRequestBody)
        self.assertEqual(pid, request.identity)
        self.assertEqual('profile-2', request.profile.name)
        self.assertEqual({'author': 'thomas j'}, request.profile.metadata)
        expected = {'profile': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_update_no_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, profile_id=pid, body=body)
        self.assertEqual("Malformed request data, missing 'profile' key in "
                         "request body.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_update_no_name(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {'metadata': {'author': 'thomas j'}}
        }

        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value={})
        result = self.controller.update(req, profile_id=pid, body=body)
        self.assertEqual({'profile': {}}, result)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileUpdateRequest)
        self.assertIsInstance(request.profile, vorp.ProfileUpdateRequestBody)
        self.assertEqual(pid, request.identity)
        self.assertEqual({'author': 'thomas j'}, request.profile.metadata)

    def test_profile_update_with_unexpected_field(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, profile_id=pid, body=body)
        msg = _("Additional properties are not allowed "
                "('foo' was unexpected)")
        self.assertEqual(msg, six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_update_not_found(self, mock_enforce):
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
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

    def test_profile_delete_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=None)

        self.assertRaises(exc.HTTPNoContent,
                          self.controller.delete, req, profile_id=pid)

        mock_call.assert_called_with(req.context, 'profile_delete2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertEqual(pid, request.identity)

    def test_profile_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceNotFound(type='profile', id=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, profile_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_profile_delete_resource_in_use(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceInUse(type='profile', id=pid,
                                         reason='still in use')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
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

    def test_profile_validate_version_mismatch(self, mock_enforce):
        body = {
            'profile': {}
        }
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

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

    def test_profile_validate_no_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {'foo': 'bar'}
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("Request body missing 'profile' key.",
                         six.text_type(ex))

    def test_profile_validate_no_spec(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'validate', True)
        body = {
            'profile': {}
        }
        req = self._post('/profiles/validate', jsonutils.dumps(body),
                         version='1.2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("'spec' is a required property", six.text_type(ex))

    def test_profile_validate_unsupported_field(self, mock_enforce):
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

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.validate,
                               req, body=body)
        self.assertEqual("Additional properties are not allowed "
                         "('foo' was unexpected)", six.text_type(ex))

    def test_profile_validate_invalide_spec(self, mock_enforce):
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.validate,
                                              req, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidSpec', resp.json['error']['type'])

    def test_profile_validate_success(self, mock_enforce):
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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=spec)
        result = self.controller.validate(req, body=body)
        mock_call.assert_called_with(req.context,
                                     'profile_validate2',
                                     mock.ANY)
        expected = {'profile': spec}
        self.assertEqual(expected, result)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorp.ProfileValidateRequest)
