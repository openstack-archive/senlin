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
from senlin.api.openstack.v1 import profiles
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


class ProfileDataTest(base.SenlinTestCase):
    def test_profile_data(self):
        body = {
            'name': 'test_profile',
            'spec': {
                'type': 'test_profile_type',
                'version': '1.0',
                'properties': {
                    'param1': 'value1',
                    'param2': 'value2',
                    'context': {
                        'region': 'region1',
                    },
                }
            },
            'metadata': {}
        }
        data = profiles.ProfileData(body)
        self.assertEqual('test_profile', data.name())
        self.assertEqual(body['spec'], data.spec())
        self.assertEqual({}, data.metadata())

    def test_required_fields_missing(self):
        body = {'not a profile name': 'wibble'}
        data = profiles.ProfileData(body)
        self.assertRaises(exc.HTTPBadRequest, data.name)
        self.assertRaises(exc.HTTPBadRequest, data.spec)
        self.assertIsNone(data.metadata())


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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        default_args = {'limit': None, 'marker': None, 'filters': None,
                        'sort': None, 'project_safe': True}

        mock_call.assert_called_with(req.context,
                                     ('profile_list', default_args))

        expected = {'profiles': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_index_whitelists_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 20,
            'marker': 'fake marker',
            'sort': 'fake sorting string',
            'global_project': False
        }
        req = self._get('/profiles', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(5, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('project_safe', engine_args)

    def test_profile_index_whitelist_bad_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/profiles', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_index_whitelist_filter_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'type': 'some_type',
            'name': 'fake name',
            'metadata': 'fake_data',
        }
        req = self._get('/profiles', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(3, len(filters))
        self.assertIn('name', filters)
        self.assertIn('type', filters)
        self.assertIn('metadata', filters)

    def test_profile_index_whitelist_filter_bad_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'fake_value'
        }
        req = self._get('/profiles', params=params)

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)
        self.assertEqual("Invalid parameter balrog", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_profile_index_limit_non_int(self, mock_enforce):
        mock_call = self.patchobject(rpc_client.EngineClient, 'profile_list',
                                     return_value=[])

        params = {'limit': 'abc'}
        req = self._get('/profiles', params=params)
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)
        self.assertIn("Invalid value 'abc' specified for 'limit'",
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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(
            req.context,
            ('profile_create', {
                'name': 'test_profile',
                'spec': {
                    'type': 'test_profile_type',
                    'version': '1.0',
                    'properties': {
                        'param_1': 'value1',
                        'param_2': 2
                    },
                },
                'metadata': {},
            })
        )

        expected = {'profile': engine_response}
        self.assertEqual(expected, resp)

    def test_profile_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'name': 'test_profile'}

        req = self._post('/profiles', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Malformed request data, missing 'profile' key "
                         "in request body.", six.text_type(ex))

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

        error = senlin_exc.ProfileTypeNotFound(profile_type=type_name)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        mock_call.assert_called_once_with(req.context,
                                          ('profile_create', body['profile']))
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileTypeNotFound', resp.json['error']['type'])

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
        error = senlin_exc.SpecValidationFailed(message=msg)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)
        mock_call.assert_called_once_with(req.context,
                                          ('profile_create', body['profile']))
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SpecValidationFailed', resp.json['error']['type'])

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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.get(req, profile_id=pid)

        mock_call.assert_called_with(req.context,
                                     ('profile_get', {'identity': pid}))

        expected = {'profile': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        pid = 'non-existent-profile'
        req = self._get('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ProfileNotFound(profile=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, profile_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

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
                'spec': {
                    'param_2': 'value3',
                },
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
            u'spec': {
                u'param_1': u'value1',
                u'param_2': u'value3',
            },
            u'created_time': u'2015-02-25T16:20:13Z',
            u'updated_time': None,
            u'metadata': {u'author': u'thomas j'},
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        result = self.controller.update(req, profile_id=pid, body=body)

        args = copy.deepcopy(body['profile'])
        args['profile_id'] = pid
        del args['spec']
        mock_call.assert_called_with(req.context, ('profile_update', args))

        expected = {'profile': engine_resp}
        self.assertEqual(expected, result)

    def test_profile_update_no_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {'foo': 'bar'}
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, profile_id=pid, body=body)
        self.assertEqual("Malformed request data, missing 'profile' key in "
                         "request body.", six.text_type(ex))

    def test_profile_update_no_name(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {'spec': {'param_2': 'value3'},
                        'metadata': {'author': 'thomas j'}}
        }

        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        self.patchobject(rpc_client.EngineClient, 'call', return_value={})
        result = self.controller.update(req, profile_id=pid, body=body)
        self.assertEqual({'profile': {}}, result)

    def test_profile_update_no_spec(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        pid = 'aaaa-bbbb-cccc'
        body = {
            'profile': {
                'name': 'new_profile',
                'metadata': {'author': 'john d'},
            }
        }
        req = self._put('/profiles/%(profile_id)s' % {'profile_id': pid},
                        jsonutils.dumps(body))

        engine_response = {
            u'id': 'dddd-eeee-ffff',
            u'name': u'new_profile',
            u'type': u'test_profile_type',
            u'spec': {
                u'param_1': u'value1',
                u'param_2': u'value3',
            },
            u'created_time': u'2015-02-25T16:20:13Z',
            u'updated_time': u'2015-02-25T16:50:22Z',
            u'metadata': {u'author': u'john d'},
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)
        result = self.controller.update(req, profile_id=pid, body=body)

        args = copy.deepcopy(body['profile'])
        args['profile_id'] = pid
        mock_call.assert_called_with(req.context, ('profile_update', args))

        expected = {'profile': engine_response}
        self.assertEqual(expected, result)

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

        error = senlin_exc.ProfileNotFound(profile=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, profile_id=pid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=None)

        self.controller.delete(req, profile_id=pid)

        mock_call.assert_called_with(
            req.context, ('profile_delete', {'identity': pid}))

    def test_profile_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ProfileNotFound(profile=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, profile_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

    def test_profile_delete_resource_in_use(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        pid = 'aaaa-bbbb-cccc'
        req = self._delete('/profiles/%(profile_id)s' % {'profile_id': pid})

        error = senlin_exc.ResourceInUse(resource_type='profile',
                                         resource_id=pid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
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
