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
from oslo_utils import uuidutils
import six
from webob import exc

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import clusters
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
from senlin.common import policy
from senlin.objects.requests import clusters as vorc
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class ClusterControllerTest(shared.ControllerTest, base.SenlinTestCase):
    '''Test case for the cluster controoler.'''

    def setUp(self):
        super(ClusterControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = clusters.ClusterController(options=cfgopts)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_index(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/clusters')

        engine_resp = [{'foo': 'bar'}]
        mock_call.return_value = engine_resp

        result = self.controller.index(req)

        expected = {u'clusters': engine_resp}
        self.assertEqual(expected, result)

        mock_call.assert_called_once_with(req.context, 'cluster_list2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterListRequest)
        self.assertTrue(request.project_safe)
        self.assertFalse(request.obj_attr_is_set('name'))
        self.assertFalse(request.obj_attr_is_set('status'))
        self.assertFalse(request.obj_attr_is_set('limit'))
        self.assertFalse(request.obj_attr_is_set('marker'))
        self.assertFalse(request.obj_attr_is_set('sort'))

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_index_with_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        fake_id = uuidutils.generate_uuid()
        params = {
            'name': 'name1',
            'status': 'ACTIVE',
            'limit': '3',
            'marker': fake_id,
            'sort': 'name:asc',
            'global_project': 'True',
        }
        req = self._get('/clusters', params=params)

        engine_resp = [{'foo': 'bar'}]
        mock_call.return_value = engine_resp

        result = self.controller.index(req)

        expected = {u'clusters': engine_resp}
        self.assertEqual(expected, result)

        mock_call.assert_called_once_with(req.context, 'cluster_list2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterListRequest)
        self.assertFalse(request.project_safe)
        self.assertEqual(['name1'], request.name)
        self.assertEqual(['ACTIVE'], request.status)
        self.assertEqual(3, request.limit)
        self.assertEqual(fake_id, request.marker)
        self.assertEqual('name:asc', request.sort)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_index_with_bad_param_name(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'foo': 'bar'}
        req = self._get('/clusters', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual("Invalid parameter 'foo'", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_index_with_bad_param_value(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'limit': -1}
        req = self._get('/clusters', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual("Value must be >= 0 for field 'limit'.",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_index_with_bad_schema(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'status': 'fake'}
        req = self._get('/clusters', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual("Field value fake is invalid",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_index_error_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)

        req = self._get('/clusters')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_create(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'desired_capacity': 0,
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'metadata': {},
                'timeout': None,
            }
        }

        req = self._post('/clusters', jsonutils.dumps(body))
        engine_response = {
            'id': 'FAKE_ID',
            'name': 'test_cluster',
            'desired_capacity': 0,
            'profile_id': 'xxxx-yyyy',
            'min_size': 0,
            'max_size': 0,
            'metadata': {},
            'timeout': 60,
            'action': 'fake_action'
        }
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_create2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterCreateRequestBody)
        self.assertEqual(0, request.desired_capacity)
        self.assertEqual(0, request.max_size)
        self.assertEqual(0, request.min_size)
        self.assertEqual({}, request.metadata)
        self.assertEqual('test_cluster', request.name)
        self.assertEqual('xxxx-yyyy', request.profile_id)
        self.assertIsNone(request.timeout)

        self.assertEqual(engine_response, resp['cluster'])
        self.assertEqual('/actions/fake_action', resp['location'])

    def test_create_only_required(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
            }
        }

        req = self._post('/clusters', jsonutils.dumps(body))
        engine_response = {
            'id': 'FAKE_ID',
            'name': 'test_cluster',
            'desired_capacity': 0,
            'profile_id': 'xxxx-yyyy',
            'min_size': 0,
            'max_size': 0,
            'metadata': {},
            'timeout': 60,
            'action': 'fake_action'
        }
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(req.context, 'cluster_create2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterCreateRequestBody)
        self.assertEqual('test_cluster', request.name)
        self.assertEqual('xxxx-yyyy', request.profile_id)
        for attr in ('desired_capacity', 'min_size', 'max_size', 'metadata',
                     'timeout'):
            self.assertFalse(request.obj_attr_is_set(attr))

        self.assertEqual(engine_response, resp['cluster'])
        self.assertEqual('/actions/fake_action', resp['location'])

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_create_missing_cluster_key(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'what_the_hell': {
                'name': 'test/cluster',
                'profile_id': 'xxxx-yyyy',
            }
        }
        req = self._post('/clusters', jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("Request body missing 'cluster' key.",
                         six.text_type(ex))

        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_create_bad_name(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'cluster': {
                'name': 'test/cluster',
                'profile_id': 'xxxx-yyyy',
            }
        }
        req = self._post('/clusters', jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

        self.assertEqual("The value for the 'name' (test/cluster) contains "
                         "illegal characters.", six.text_type(ex))

        self.assertEqual(0, mock_call.call_count)

    def test_create_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', False)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
            }
        }
        req = self._post('/clusters', jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_get(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        cid = 'cid'
        req = self._get('/clusters/%s' % cid)
        engine_resp = {'foo': 'bar'}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        response = self.controller.get(req, cluster_id=cid)

        mock_call.assert_called_once_with(req.context, 'cluster_get2',
                                          mock.ANY)

        expected = {'cluster': engine_resp}
        self.assertEqual(expected, response)
        request = mock_call.call_args[0][2]
        self.assertEqual('cid', request.identity)

    def test_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        cid = 'non-existent-cluster'
        req = self._get('/clusters/%s' % cid)

        error = senlin_exc.ResourceNotFound(type='cluster', id=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        cid = 'cid'
        req = self._get('/clusters/%s' % cid)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_delete(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%s' % cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value={'action': 'FAKE_ID'})

        res = self.controller.delete(req, cluster_id=cid)

        result = {'location': '/actions/FAKE_ID'}
        self.assertEqual(result, res)
        mock_call.assert_called_with(req.context, 'cluster_delete2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterDeleteRequest)
        self.assertEqual(cid, request.identity)

    def test_cluster_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%s' % cid)
        error = senlin_exc.ResourceNotFound(type='cluster', id=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_cluster_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%s' % cid)
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_update(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'cluster': {
                'profile_id': 'xxxx-yyyy-zzzz',
            }
        }
        engine_resp = {
            'id': cid,
            'action': 'fake_action',
        }
        req = self._patch('/clusters/%s' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        res = self.controller.update(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_update2',
                                          mock.ANY)
        self.assertEqual(engine_resp, res['cluster'])
        self.assertEqual('/actions/fake_action', res['location'])
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterUpdateRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual('xxxx-yyyy-zzzz', request.profile_id)
        self.assertFalse(request.obj_attr_is_set('name'))
        self.assertFalse(request.obj_attr_is_set('metadata'))
        self.assertFalse(request.obj_attr_is_set('timeout'))

    def test_update_missing_cluster_key(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'profile_id': 'xxxx-yyyy-zzzz'}
        req = self._patch('/clusters/%s' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, cluster_id=cid, body=body)

        self.assertIn("Malformed request data, missing 'cluster' key "
                      "in request body.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_update_bad_name(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'name': 'foo bar'}}
        req = self._patch('/clusters/%s' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, cluster_id=cid, body=body)

        self.assertEqual(_("The value for the 'name' (foo bar) contains "
                           "illegal characters."),
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_update_timeout_non_int(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'timeout': '10min'}}
        req = self._patch('/clusters/%s' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, cluster_id=cid, body=body)

        self.assertEqual(_("invalid literal for int() with base 10: '10min'"),
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_update_bad_metadata(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'metadata': 'what?'}}

        req = self._patch('/clusters/%s' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, cluster_id=cid, body=body)

        self.assertEqual(_("The server could not comply with the request "
                           "since it is either malformed or otherwise "
                           "incorrect."),
                         six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_update_engine_error(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'non-existent-cluster'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}
        req = self._patch('/clusters/%s' % cid, jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='cluster', id=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_update_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}

        req = self._patch('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                          jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def _test_action_resize_w_type(self, adj_type, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': adj_type,
                'number': 1,
                'min_size': 0,
                'max_size': 10,
                'min_step': 1,
                'strict': True
            }
        }
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_resize2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterResizeRequest)
        self.assertEqual(adj_type, request.adjustment_type)
        self.assertEqual(1, request.number)
        self.assertEqual(0, request.min_size)
        self.assertEqual(10, request.max_size)
        self.assertEqual(1, request.min_step)
        self.assertTrue(request.strict)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_action_resize_with_exact_capacity(self, mock_enforce):
        self._test_action_resize_w_type('EXACT_CAPACITY', mock_enforce)

    def test_action_resize_with_change_capacity(self, mock_enforce):
        self._test_action_resize_w_type('CHANGE_IN_CAPACITY', mock_enforce)

    def test_action_resize_with_change_percentage(self, mock_enforce):
        self._test_action_resize_w_type('CHANGE_IN_PERCENTAGE', mock_enforce)

    def test_action_resize_with_bad_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': 'NOT_QUITE_SURE',
                'number': 1
            }
        }
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertIn("Value 'NOT_QUITE_SURE' is not acceptable for field "
                      "'adjustment_type'.", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_resize_missing_number(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': 'EXACT_CAPACITY',
            }
        }
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('Missing number value for size adjustment.',
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_resize_missing_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'number': 2}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Missing adjustment_type value for size adjustment.",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def _test_resize_param_not_int(self, param, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': 'CHANGE_IN_CAPACITY',
                'number': 1,
            }
        }
        body['resize'][param] = 'BOGUS'
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual(0, mock_call.call_count)

        return six.text_type(ex)

    def test_action_resize_number_not_int(self, mock_enforce):
        r = self._test_resize_param_not_int('number', mock_enforce)
        self.assertIn('could not convert string to float', r)

    def test_action_resize_min_size_not_int(self, mock_enforce):
        r = self._test_resize_param_not_int('min_size', mock_enforce)
        self.assertEqual("The value for min_size must be an integer: 'BOGUS'.",
                         r)

    def test_action_resize_max_size_not_int(self, mock_enforce):
        r = self._test_resize_param_not_int('max_size', mock_enforce)
        self.assertEqual("The value for max_size must be an integer: 'BOGUS'.",
                         r)

    def test_action_resize_min_step_not_int(self, mock_enforce):
        r = self._test_resize_param_not_int('min_step', mock_enforce)
        self.assertEqual("invalid literal for int() with base 10: 'BOGUS'", r)

    def test_action_resize_max_size_too_small(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'min_size': 2, 'max_size': 1}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("The specified min_size (2) is greater than "
                         "the specified max_size (1).", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_resize_strict_non_bool(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'strict': 'FOO'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertIn("Unrecognized value 'FOO'", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_scale_out(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'scale_out': {'count': 1}}
        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_scale_out2',
                                          mock.ANY)
        self.assertEqual(eng_resp, resp)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterScaleOutRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual(1, request.count)

    def test_action_scale_in(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'scale_in': {'count': 1}}
        eng_resp = {'action': {'id': 'action-id', 'target': cid}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_scale_in2',
                                          mock.ANY)
        self.assertEqual(eng_resp, resp)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterScaleInRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual(1, request.count)

    def _action_scale_non_int(self, action, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {action: {'count': 'abc'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertIn("invalid literal", six.text_type(ex))

    def test_action_scale_out_non_int(self, mock_enforce):
        self._action_scale_non_int('scale_out', mock_enforce)

    def test_action_scale_in_non_int(self, mock_enforce):
        self._action_scale_non_int('scale_in', mock_enforce)

    def test_action_attach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'policy_id': 'xxxx-yyyy'}}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context,
                                          'cluster_policy_attach2', mock.ANY)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterAttachPolicyRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual('xxxx-yyyy', request.policy_id)
        self.assertFalse(request.obj_attr_is_set('enabled'))

    def test_action_attach_policy_disabled(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {
            'policy_id': 'xxxx-yyyy',
            'enabled': False,
        }}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context,
                                          'cluster_policy_attach2', mock.ANY)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterAttachPolicyRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual('xxxx-yyyy', request.policy_id)
        self.assertFalse(request.enabled)

    def test_action_attach_policy_missing_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("'policy_id' is a required property",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_attach_policy_additional_properties(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'foo': 'bar', 'policy_id': 'fake'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Additional properties are not allowed ('foo' was "
                         "unexpected)", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_attach_policy_enabled_not_boolean(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {
            'policy_id': 'not-a-policy',
            'enabled': 'who knows'
        }}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertIn("Unrecognized value 'who knows'", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_detach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'xxxx-yyyy'}}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context,
                                          'cluster_policy_detach2', mock.ANY)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterDetachPolicyRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual('xxxx-yyyy', request.policy_id)

    def test_action_detach_policy_missing_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("'policy_id' is a required property",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_detach_policy_additional_properties(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'fake', 'foo': 'bar'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Additional properties are not allowed ('foo' was "
                         "unexpected)", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_update_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {
            'policy_id': 'xxxx-yyyy',
            'enabled': True,
        }}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context,
                                          'cluster_policy_update2', mock.ANY)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterUpdatePolicyRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual('xxxx-yyyy', request.policy_id)
        self.assertTrue(request.enabled)

    def test_action_update_policy_missing_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("'policy_id' is a required property",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_update_policy_additional_properties(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {'foo': 'bar', 'policy_id': 'fake'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Additional properties are not allowed ('foo' was "
                         "unexpected)", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_update_policy_enabled_not_boolean(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {
            'policy_id': 'xxxx-yyyy',
            'enabled': 'good',
        }}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertIn("Unrecognized value 'good'", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_action_update_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {'policy_id': 'not-a-policy'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='policy', id='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_cluster_action_missing_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual('No action specified', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_multiple_actions(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'action_1': {}, 'action_2': {}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual('Multiple actions specified', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_unsupported_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'fly': None}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual("Unrecognized action 'fly' specified",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', False)
        cid = 'aaaa-bbbb-cccc'
        body = {'someaction': {'param': 'value'}}

        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_collect(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'collect', True)
        cid = 'aaaa-bbbb-cccc'
        path = 'foo.bar'
        req = self._get('/clusters/%(cid)s/attrs/%(path)s' %
                        {'cid': cid, 'path': path}, version='1.2')
        engine_response = {
            'cluster_attributes': [{'key': 'value'}],
        }
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_response)

        resp = self.controller.collect(req, cluster_id=cid, path=path)

        self.assertEqual(engine_response, resp)
        mock_call.assert_called_once_with(req.context, 'cluster_collect2',
                                          mock.ANY)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterCollectRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual(path, request.path)

    def test_cluster_collect_version_mismatch(self, mock_enforce):
        # NOTE: we skip the mock_enforce setup below because api version check
        #       comes before the policy enforcement and the check fails in
        #       this test case.
        # self._mock_enforce_setup(mock_enforce, 'collect', True)
        cid = 'aaaa-bbbb-cccc'
        path = 'foo.bar'
        req = self._get('/clusters/%(cid)s/attrs/%(path)s' %
                        {'cid': cid, 'path': path}, version='1.1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(senlin_exc.MethodVersionNotFound,
                               self.controller.collect,
                               req, cluster_id=cid, path=path)

        self.assertEqual(0, mock_call.call_count)
        self.assertEqual('API version 1.1 is not supported on this method.',
                         six.text_type(ex))

    def test_cluster_collect_path_not_provided(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'collect', True)
        cid = 'aaaa-bbbb-cccc'
        path = '    '
        req = self._get('/clusters/%(cid)s/attrs/%(path)s' %
                        {'cid': cid, 'path': path}, version='1.2')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.collect,
                               req, cluster_id=cid, path=path)

        self.assertEqual(0, mock_call.call_count)
        self.assertEqual('Required path attribute is missing.',
                         six.text_type(ex))

    def test_cluster_collect_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'collect', False)
        cid = 'aaaa-bbbb-cccc'
        path = 'foo.bar'
        req = self._get('/clusters/%(cid)s/attrs/%(path)s' %
                        {'cid': cid, 'path': path}, version='1.2')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.collect,
                                              req, cluster_id=cid, path=path)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
        self.assertEqual(0, mock_call.call_count)

    def test_action_add_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'FAKE_ID'
        body = {'add_nodes': {'nodes': ['NODE1']}}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_add_nodes2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterAddNodesRequest)
        self.assertEqual('FAKE_ID', request.identity)
        self.assertEqual(['NODE1'], request.nodes)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_action_add_nodes_none(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'somearg': 'somevalue'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_action_add_nodes_empty(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'nodes': []}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_action_add_nodes_bad_requests(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'nodes': ['bad-node-1']}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='Node', id='bad-node-1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])
        self.assertIn('The Node (bad-node-1) could not be found.',
                      resp.json['error']['message'])

    def test_action_del_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': ['NODE1', ]}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        eng_resp = {'action': 'action-id'}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_del_nodes2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterDelNodesRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual(['NODE1'], request.nodes)
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_action_del_nodes_none(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'somearg': 'somevalue'}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_action_del_nodes_empty(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': []}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_action_del_nodes_bad_request(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': ['bad-node-1']}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        error = senlin_exc.BadRequest(msg='Nodes not found: bad-node-1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('BadRequest', resp.json['error']['type'])
        self.assertIn('Nodes not found: bad-node-1',
                      resp.json['error']['message'])

    def test_action_check(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'check': {}}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_check2',
                                          mock.ANY)
        self.assertEqual(eng_resp, resp)
        request = mock_call.call_args[0][2]
        self.assertEqual(cid, request.identity)
        self.assertEqual({}, request.params)

    def test_action_check_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'unknown-cluster'
        body = {'check': {}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='cluster', id=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_action_recover(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'recover': {}}
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(req.context, 'cluster_recover2',
                                          mock.ANY)
        self.assertEqual(eng_resp, resp)
        request = mock_call.call_args[0][2]
        self.assertEqual(cid, request.identity)
        self.assertEqual({}, request.params)

    def test_action_recover_with_ops(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'recover': {
                'operation': 'REBUILD'
            }
        }
        eng_resp = {'action': 'action-id'}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        self.assertEqual(eng_resp, resp)
        mock_call.assert_called_once_with(req.context, 'cluster_recover2',
                                          mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertEqual(cid, request.identity)
        self.assertEqual({'operation': 'REBUILD'}, request.params)

    def test_action_recover_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'unknown-cluster'
        body = {'recover': {}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body))

        error = senlin_exc.ResourceNotFound(type='cluster', id=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_action_replace_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'replace_nodes': {
                'nodes': {
                    'dddd-eeee-ffff': 'gggg-hhhh-iiii'
                }
            }
        }
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body),
                         version='1.3')
        eng_resp = {'action': 'action-id'}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        result = {
            'action': 'action-id',
            'location': '/actions/action-id'
        }
        self.assertEqual(result, resp)
        mock_call.assert_called_once_with(req.context,
                                          'cluster_replace_nodes2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vorc.ClusterReplaceNodesRequest)
        self.assertEqual(cid, request.identity)
        self.assertEqual({'dddd-eeee-ffff': 'gggg-hhhh-iiii'}, request.nodes)

    def test_action_replace_nodes_not_map(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'CID'
        body = {'replace_nodes': {'nodes': ['node1']}}
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body),
                         version='1.3')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('The data provided is not a map.', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_action_replace_nodes_duplicate(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'CID'
        body = {
            'replace_nodes': {
                'nodes': {
                    'origin1': 'replace_node',
                    'origin2': 'replace_node'
                }
            }
        }
        req = self._post('/clusters/%s/actions' % cid, jsonutils.dumps(body),
                         version='1.3')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('Map contains duplicated values', six.text_type(ex))
        self.assertFalse(mock_call.called)
