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

from oslo_config import cfg
from oslo_serialization import jsonutils

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import nodes
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


class NodeDataTest(base.SenlinTestCase):
    def test_node_name(self):
        body = {'name': 'test_node'}
        data = nodes.NodeData(body)
        self.assertEqual('test_node', data.name())

    def test_required_fields_missing(self):
        body = {'not a node name': 'wibble'}
        data = nodes.NodeData(body)
        self.assertRaises(exc.HTTPBadRequest, data.name)
        self.assertRaises(exc.HTTPBadRequest, data.profile_id)
        self.assertIsNone(data.cluster_id())
        self.assertIsNone(data.role())
        self.assertIsNone(data.metadata())

    def test_with_cluster_id(self):
        body = {'cluster_id': 'cluster-1', 'name': 'test_node'}
        data = nodes.NodeData(body)
        self.assertEqual('test_node', data.name())
        self.assertEqual('cluster-1', data.cluster_id())

    def test_with_profile_id(self):
        body = {'profile_id': 'my-stack', 'name': 'test_node'}
        data = nodes.NodeData(body)
        self.assertEqual('test_node', data.name())
        self.assertEqual('my-stack', data.profile_id())


@mock.patch.object(policy, 'enforce')
class NodeControllerTest(shared.ControllerTest, base.SenlinTestCase):

    def setUp(self):
        super(NodeControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = nodes.NodeController(options=cfgopts)

    def test_node_index(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/nodes')

        engine_resp = [
            {
                u'id': u'aaaa-bbbb-cccc',
                u'name': u'node-1',
                u'cluster_id': None,
                u'physical_id': None,
                u'profile_id': u'pppp-rrrr-oooo-ffff',
                u'profile_name': u'my_stack_profile',
                u'index': 1,
                u'role': None,
                u'init_time': u'2015-01-23T13:06:00Z',
                u'created_time': u'2015-01-23T13:07:22Z',
                u'updated_time': None,
                u'status': u'ACTIVE',
                u'status_reason': u'Node successfully created',
                u'data': {},
                u'metadata': {},
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        default_args = {'cluster_id': None, 'limit': None, 'marker': None,
                        'sort': None, 'filters': None, 'project_safe': True}

        mock_call.assert_called_with(req.context, ('node_list', default_args))

        expected = {'nodes': engine_resp}
        self.assertEqual(expected, result)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_whitelists_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'name': 'node111',
            'status': 'active',
            'cluster_id': 'id or name of a cluster',
            'limit': 10,
            'marker': 'fake marker',
            'sort': 'fake sorting string',
            'global_project': False,
        }
        req = self._get('/nodes', params=params)
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(6, len(engine_args))
        self.assertIn('cluster_id', engine_args)
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('project_safe', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_whitelists_invalid_params(self, mock_call,
                                                  mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/nodes', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_global_project_true(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'True'}
        req = self._get('/nodes', params=params)

        self.controller.index(req)

        call_args, w = mock_call.call_args
        call_args = call_args[1][1]
        self.assertIn('project_safe', call_args)
        self.assertFalse(call_args['project_safe'])

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_global_project_false(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'False'}
        req = self._get('/nodes', params=params)

        self.controller.index(req)

        call_args, w = mock_call.call_args
        call_args = call_args[1][1]
        self.assertIn('project_safe', call_args)
        self.assertTrue(call_args['project_safe'])

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_global_project_not_bool(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'No'}
        req = self._get('/nodes', params=params)

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'No' specified for 'global_project'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_limit_not_int(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'limit': 'not-int'}
        req = self._get('/nodes', params=params)

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'not-int' specified for 'limit'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_whitelist_filter_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'status': 'fake status',
            'name': 'fake name',
        }
        req = self._get('/nodes', params=params)
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(2, len(filters))
        self.assertIn('status', filters)
        self.assertIn('name', filters)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_whitelist_filter_invalid_params(self, mock_call,
                                                        mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/nodes', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    def test_node_index_cluster_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        cluster_id = 'non-existent'
        req = self._get('/nodes', {'cluster_id': cluster_id})

        error = senlin_exc.ClusterNotFound(cluster=cluster_id)
        self.patchobject(rpc_client.EngineClient, 'call',
                         side_effect=shared.to_remote_error(error))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index, req)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_node_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/nodes')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index, req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_node_create_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'node': {
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'cluster_id': None,
                'role': None,
                'metadata': {},
            }
        }

        engine_response = {
            'id': 'test_node_id',
            'name': 'test_node',
            'profile_id': 'xxxx-yyyy',
            'cluster_id': None,
            'role': None,
            'metadata': {},
            'action': 'fake_action'
        }

        req = self._post('/nodes', jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(
            req.context,
            ('node_create', {
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'cluster_id': None,
                'role': None,
                'metadata': {},
            })
        )

        expected = {
            'node': engine_response,
            'location': '/actions/fake_action'
        }
        self.assertEqual(expected, resp)

    def test_node_create_with_bad_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {'foo': 'bar'}
        req = self._post('/nodes', jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)
        self.assertEqual("Malformed request data, missing 'node' key in "
                         "request body.", six.text_type(ex))

    def test_node_create_with_bad_profile(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'node': {
                'name': 'test_node',
                'profile_id': 'bad-profile',
                'cluster_id': None,
                'role': None,
                'metadata': {},
            }
        }
        req = self._post('/nodes', jsonutils.dumps(body))

        error = senlin_exc.ProfileNotFound(profile='bad-profile')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)
        mock_call.assert_called_once_with(req.context,
                                          ('node_create', body['node']))
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

    def test_node_create_with_bad_cluster(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'node': {
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy-zzzz',
                'cluster_id': 'non-existent-cluster',
                'role': None,
                'metadata': {},
            }
        }
        req = self._post('/nodes', jsonutils.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster='non-existent-cluster')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        mock_call.assert_called_once_with(req.context,
                                          ('node_create', body['node']))
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_node_get_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        node_id = 'aaaa-bbbb-cccc'
        req = self._get('/nodes/%(node_id)s' % {'node_id': node_id})

        engine_resp = {
            u'id': 'aaaa-bbbb-cccc',
            u'name': 'node-1',
            u'cluster_id': None,
            u'physical_id': None,
            u'profile_id': 'pppp-rrrr-oooo-ffff',
            u'profile_name': u'my_stack_profile',
            u'index': 1,
            u'role': None,
            u'init_time': u'2015-01-23T13:06:00Z',
            u'created_time': u'2015-01-23T13:07:22Z',
            u'updated_time': None,
            u'status': u'ACTIVE',
            u'status_reason': u'Node successfully created',
            u'data': {},
            u'metadata': {},
            u'details': {}
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        response = self.controller.get(req, node_id=node_id)

        mock_call.assert_called_once_with(
            req.context, ('node_get', {'identity': node_id,
                                       'show_details': False}))

        expected = {'node': engine_resp}
        self.assertEqual(expected, response)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_get_show_details_not_bool(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        node_id = 'aaaa-bbbb-cccc'
        params = {'show_details': 'Okay'}
        req = self._get('/nodes/%(node_id)s' % {'node_id': node_id},
                        params=params)

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.get,
                               req, node_id=node_id)

        self.assertEqual("Invalid value 'Okay' specified for 'show_details'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_node_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        node_id = 'non-existent-node'
        req = self._get('/nodes/%(node_id)s' % {'node_id': node_id})

        error = senlin_exc.NodeNotFound(node=node_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, node_id=node_id)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('NodeNotFound', resp.json['error']['type'])

    def test_node_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        node_id = 'non-existent-node'
        req = self._get('/nodes/%(node_id)s' % {'node_id': node_id})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, node_id=node_id)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_node_update_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        nid = 'aaaa-bbbb-cccc'
        body = {
            'node': {
                'id': nid,
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'role': None,
                'metadata': {},
            }
        }
        aid = 'xxxx-yyyy-zzzz'

        engine_response = body['node'].copy()
        engine_response['action'] = aid

        req = self._patch('/nodes/%(node_id)s' % {'node_id': nid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        res = self.controller.update(req, node_id=nid, body=body)

        mock_call.assert_called_with(
            req.context,
            ('node_update', {
                'identity': nid,
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'role': None,
                'metadata': {},
            })
        )
        result = {
            'node': body['node'],
            'location': '/actions/%s' % aid,
        }
        self.assertEqual(result, res)

    def test_node_update_malformed_request(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        nid = 'aaaa-bbbb-cccc'
        body = {'name': 'new name'}

        req = self._patch('/nodes/%(node_id)s' % {'node_id': nid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update, req,
                               node_id=nid, body=body)
        self.assertEqual("Malformed request data, missing 'node' key "
                         "in request body.", six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_node_update_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        nid = 'non-exist-node'
        body = {
            'node': {
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'role': None,
                'metadata': {},
            }
        }

        req = self._patch('/nodes/%(node_id)s' % {'node_id': nid},
                          jsonutils.dumps(body))

        error = senlin_exc.NodeNotFound(node=nid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=shared.to_remote_error(error))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, node_id=nid, body=body)

        mock_call.assert_called_with(
            req.context,
            ('node_update', {
                'identity': nid,
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'role': None,
                'metadata': {},
            })
        )

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('NodeNotFound', resp.json['error']['type'])

    def test_node_update_invalid_profile(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        nid = 'aaaa-bbbb-cccc'
        body = {
            'node': {
                'name': 'test_node',
                'profile_id': 'profile-not-exist',
                'role': None,
                'metadata': {},
            }
        }

        req = self._patch('/nodes/%(node_id)s' % {'node_id': nid},
                          jsonutils.dumps(body))

        error = senlin_exc.ProfileNotFound(profile=nid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=shared.to_remote_error(error))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, node_id=nid, body=body)
        mock_call.assert_called_with(
            req.context,
            ('node_update', {
                'identity': nid,
                'name': 'test_node',
                'profile_id': 'profile-not-exist',
                'role': None,
                'metadata': {},
            })
        )
        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

    def test_node_update_cluster_id_specified(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        nid = 'aaaa-bbbb-cccc'
        body = {'node': {'cluster_id': 'xxxx-yyyy-zzzz'}}

        req = self._patch('/nodes/%(node_id)s' % {'node_id': nid},
                          jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, node_id=nid, body=body)
        self.assertEqual('Updating cluster_id is not allowed, please invoke '
                         'cluster add/remove node actions if needed.',
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_node_update_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        node_id = 'test-node-1'
        body = {
            'node': {
                'name': 'test_node',
                'profile_id': 'xxxx-yyyy',
                'role': None,
                'metadata': {},
            }
        }
        req = self._patch('/nodes/%(node_id)s' % {'node_id': node_id},
                          jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, node_id=node_id, body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_node_delete_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        nid = 'aaaa-bbbb-cccc'
        req = self._delete('/node/%(node_id)s' % {'node_id': nid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = {'action': 'FAKE_ID'}

        res = self.controller.delete(req, node_id=nid)
        result = {'location': '/actions/FAKE_ID'}
        self.assertEqual(res, result)
        mock_call.assert_called_with(
            req.context, ('node_delete', {'identity': nid}))

    def test_node_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        nid = 'aaaa-bbbb-cccc'
        req = self._delete('/nodes/%(node_id)s' % {'node_id': nid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, node_id=nid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_node_action_check_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        node_id = 'test-node-1'
        body = {'check': {}}
        req = self._post('/nodes/%(node_id)s/actions' % {'node_id': node_id},
                         jsonutils.dumps(body))

        engine_response = {'action': 'action-id'}

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        response = self.controller.action(req, node_id=node_id, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('node_check', {'identity': node_id, 'params': {}}))

        location = {'location': '/actions/action-id'}
        engine_response.update(location)
        self.assertEqual(engine_response, response)

    def test_node_action_check_node_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        node_id = 'unknown-node'
        body = {'check': {}}
        req = self._post('/nodes/%(node_id)s/actions' % {'node_id': node_id},
                         jsonutils.dumps(body))

        error = senlin_exc.NodeNotFound(node=node_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, node_id=node_id, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('NodeNotFound', resp.json['error']['type'])

    def test_node_action_recover_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        node_id = 'xxxx-yyyy'
        body = {'recover': {}}
        req = self._post('/nodes/%(node_id)s/actions' % {'node_id': node_id},
                         jsonutils.dumps(body))

        engine_response = {'action': 'action-id'}

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        response = self.controller.action(req, node_id=node_id, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('node_recover', {'identity': node_id, 'params': {}}))

        location = {'location': '/actions/action-id'}
        engine_response.update(location)
        self.assertEqual(engine_response, response)

    def test_node_action_missing_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cfg.CONF.set_override('debug', True, enforce_type=True)
        node_id = 'xxxx-yyyy'
        body = {}
        req = self._post('/nodes/%(node_id)s/actions' % {'node_id': node_id},
                         jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action, req,
                               node_id=node_id, body=body)

        self.assertFalse(mock_call.called)
        self.assertEqual(400, ex.code)
        self.assertIn('No action specified.', six.text_type(ex))

    def test_node_action_multiple_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cfg.CONF.set_override('debug', True, enforce_type=True)
        node_id = 'xxxx-yyyy'
        body = {'eat': {}, 'sleep': {}}
        req = self._post('/nodes/%(node_id)s/actions' % {'node_id': node_id},
                         jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, node_id=node_id, body=body)

        self.assertFalse(mock_call.called)
        self.assertEqual(400, ex.code)
        self.assertIn('Multiple actions specified.', six.text_type(ex))

    def test_node_action_unknown_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cfg.CONF.set_override('debug', True, enforce_type=True)
        node_id = 'xxxx-yyyy'
        body = {'eat': None}
        req = self._post('/nodes/%(node_id)s/action' % {'node_id': node_id},
                         jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, node_id=node_id, body=body)

        self.assertFalse(mock_call.called)
        self.assertEqual(400, ex.code)
        self.assertIn('Unrecognized action "eat" specified',
                      six.text_type(ex))

    def test_node_action_recover_node_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        node_id = 'xxxx-yyyy'
        body = {'recover': {}}
        req = self._post('/nodes/%(node_id)s/actions' % {'node_id': node_id},
                         jsonutils.dumps(body))

        error = senlin_exc.NodeNotFound(node=node_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, node_id=node_id, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('NodeNotFound', resp.json['error']['type'])

        mock_call.assert_called_once_with(
            req.context,
            ('node_recover', {'identity': node_id, 'params': {}}))

    def test_node_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        nid = 'aaaa-bbbb-cccc'
        req = self._delete('/nodes/%(node_id)s' % {'node_id': nid})

        error = senlin_exc.NodeNotFound(node=nid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, node_id=nid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('NodeNotFound', resp.json['error']['type'])
