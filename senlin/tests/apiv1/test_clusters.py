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
import webob
from webob import exc

from oslo_config import cfg

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import clusters
from senlin.common import exception as senlin_exc
from senlin.common import policy 
from senlin.tests.apiv1 import shared 
from senlin.tests.common import base
from senlin.rpc import client as rpc_client


class ClusterDataTest(base.SenlinTestCase):
    def test_cluster_name(self):
        body = {'name': 'test_cluster'}
        data = clusters.ClusterData(body)
        self.assertEqual('test_cluster', data.name())

    def test_cluster_name_missing(self):
        body = {'not the cluster name': 'wibble'}
        data = clusters.ClusterData(body)
        self.assertRaises(exc.HTTPBadRequest, data.name)
        self.assertRaises(exc.HTTPBadRequest, data.size)
        self.assertRaises(exc.HTTPBadRequest, data.profile)

    def test_cluster_size(self):
        body = {'size': 0}
        data = clusters.ClusterData(body)
        self.assertEqual(0, data.size())

    def test_cluster_timeout(self):
        body = {'timeout': 33}
        data = clusters.ClusterData(body)
        self.assertEqual(33, data.timeout())

        body = {}
        data = clusters.ClusterData(body)
        self.assertEqual(cfg.CONF.default_action_timeout, data.timeout())


@mock.patch.object(policy.Enforcer, 'enforce')
class ClusterControllerTest(shared.ControllerTest, base.SenlinTestCase):
    '''Test case for the cluster controoler.'''

    def setUp(self):
        super(ClusterControllerTest, self).setUp()
        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = clusters.ClusterController(options=cfgopts)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/clusters')

        engine_resp = [{
            u'id': u'xxxx-yyyy-zzzz',
            u'name': u'test_cluster',
            u'profile_id': u'aaaa-bbbb-cccc',
            u'user': u'admin',
            u'project': u'123456abcd3555',
            u'domain': u'default',
            u'parent': None,
            u'init_time': u'2015-01-09T09:13:11Z',
            u'created_time': u'2015-01-09T09:16:45Z',
            u'updated_time': None,
            u'deleted_time': None,
            u'size': 0,
            u'timeout': 60,
            u'status': u'ACTIVE',
            u'status_reason': u'Cluster successfully created.',
            u'tags': {},
            u'data': {},
            u'nodes': [],
            u'policies': [],
            u'profile_name': u'test_profile',
        }]

        mock_call.return_value = engine_resp

        result = self.controller.index(req, tenant_id=req.context.tenant_id)
        expected = {u'clusters': engine_resp}
        self.assertEqual(expected, result)

        default_args = {'limit': None, 'sort_keys': None, 'marker': None,
                        'sort_dir': None, 'filters': None, 'tenant_safe': True,
                        'show_deleted': False, 'show_nested': False}
        mock_call.assert_called_once_with(
            req.context, ('cluster_list', default_args))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelists_pagination_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'limit': 'fake limit',
            'sort_keys': 'fake sort keys',
            'marker': 'fake marker',
            'sort_dir': 'fake sort dir',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/clusters', params=params)
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.tenant)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertEqual(8, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('sort_keys', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort_dir', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('tenant_safe', engine_args)
        self.assertNotIn('balrog', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelist_filter_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'status': 'fake status',
            'name': 'fake name',
            'user': 'fake username',
            'project': 'fake tenant',
            'owner': 'no such key',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/clusters', params=params)
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.tenant)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(4, len(filters))
        self.assertIn('status', filters)
        self.assertIn('name', filters)
        self.assertIn('project', filters)
        self.assertIn('user', filters)
        self.assertNotIn('tenant', filters)
        self.assertNotIn('owner', filters)
        self.assertNotIn('balrog', filters)

    def test_index_show_deleted_false(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_deleted': 'False'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.tenant)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                       filters=mock.ANY,
                                                       tenant_safe=True,
                                                       show_deleted=False)

    def test_index_show_deleted_true(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_deleted': 'True'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.tenant)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                       filters=mock.ANY,
                                                       tenant_safe=True,
                                                       show_deleted=True)

    def test_index_show_nested_false(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_nested': 'False'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.tenant)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                       filters=mock.ANY,
                                                       tenant_safe=True,
                                                       show_nested=False)

    def test_index_show_nested_true(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_nested': 'True'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.tenant)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                       filters=mock.ANY,
                                                       tenant_safe=True,
                                                       show_nested=True)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_remote_attribute_error(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/clusters')

        mock_call.side_effect = shared.to_remote_error(AttributeError())

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.tenant)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('AttributeError', resp.json['error']['type'])
        mock_call.assert_called_once_with(
            req.context, ('cluster_list', mock.ANY))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_remote_internal_error(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/clusters')

        mock_call.side_effect = shared.to_remote_error(Exception())

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.tenant)

        self.assertEqual(500, resp.json['code'])
        self.assertEqual('Exception', resp.json['error']['type'])
        mock_call.assert_called_once_with(
            req.context, ('cluster_list', mock.ANY))

    def test_index_error_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)

        req = self._get('/clusters')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.tenant)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_create(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'size': 0,
                'parent': None,
                'tags': {},
                'timeout': None,
            }
        }

        req = self._post('/clusters', json.dumps(body))

        engine_response = {
            'name': 'test_cluster',
            'profile_id': 'xxxx-yyyy',
            'size': 0,
            'parent': None,
            'tags': {},
            'timeout': 60,
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, tenant_id=self.tenant, body=body)
        
        mock_call.assert_called_with(
            req.context,
            ('cluster_create', {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'size': 0,
                'parent': None,
                'tags': {},
                'timeout': None}
            )
        )

        expected = {'cluster': engine_response}
        self.assertEqual(expected, resp)

    def test_create_maleformed_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'name': 'test_cluster',
            'profile_id': 'xxxx-yyyy',
            'size': 0,
            'parent': None,
            'tags': {},
            'timeout': None,
        }

        req = self._post('/clusters', json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, tenant_id=self.tenant, body=body)

        self.assertIn("Malformed request data, missing 'cluster' key "
                      "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_create_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', False)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'size': 0,
                'parent': None,
                'tags': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', json.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.tenant,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_create_err_engine(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'size': -1,
                'parent': None,
                'tags': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', json.dumps(body))

        error = senlin_exc.InvalidParameter(name='size', value=-1)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.tenant,
                                              body=body)

        mock_call.assert_called_once()
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])

    def test_create_err_cluster_bad_reqest(self, mock_enforce):
        cfg.CONF.set_override('debug', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'size': 0,
                'parent': None,
                'tags': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', json.dumps(body))

        error = senlin_exc.HTTPExceptionDisguise(webob.exc.HTTPBadRequest())
        self.controller.create = mock.MagicMock(side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create, req,
                                              body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('HTTPBadRequest', resp.json['error']['type'])
        self.assertIsNotNone(resp.json['error']['traceback'])

    def test_cluster_get(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._get('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        engine_resp = {
            u'id': u'aaaa-bbbb-cccc',
            u'name': u'test_cluster',
            u'profile_id': u'AAAA-BBBB-CCCCCCCC',
            u'user': u'admin',
            u'project': u'123456abcd3555',
            u'domain': u'default',
            u'parent': None,
            u'init_time': u'2015-01-09T09:13:11Z',
            u'created_time': u'2015-01-09T09:16:45Z',
            u'updated_time': None,
            u'deleted_time': None,
            u'size': 0,
            u'timeout': 60,
            u'status': u'ACTIVE',
            u'status_reason': u'Cluster successfully created.',
            u'tags': {},
            u'data': {},
            u'nodes': [],
            u'policies': [],
            u'profile_name': u'test_profile',
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        response = self.controller.get(req, tenant_id=self.tenant,
                                       cluster_id=cid)

        mock_call.assert_called_once_with(
            req.context, ('cluster_get', {'identity': cid}))

        expected = {'cluster': engine_resp}
        self.assertEqual(expected, response)

    def test_cluster_get_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        cid = 'non-existent-cluster'
        req = self._get('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._get('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_delete(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = None

        self.assertRaises(webob.exc.HTTPNoContent,
                          self.controller.delete,
                          req, tenant_id=self.tenant,
                          cluster_id=cid)
        mock_call.assert_called_with(req.context,
                                     ('cluster_delete', {'identity': cid}))

    def test_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid}) 
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid)

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

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = cid

        self.assertRaises(exc.HTTPAccepted,
                          self.controller.update,
                          req, tenant_id=self.tenant,
                          cluster_id=cid,
                          body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_update', {
                'identity': cid, 'profile_id': 'xxxx-yyyy-zzzz',
            })
        )

    def test_update_with_maleformed_request(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'profile_id': 'xxxx-yyyy-zzzz'}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'cluster_update')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, tenant_id=self.tenant,
                               cluster_id=cid,
                               body=body)

        self.assertIn("Malformed request data, missing 'cluster' key "
                      "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_cluster_update_cluster_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'non-existent-cluster'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_update_profile_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'not-a-profile'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.ProfileNotFound(profile='not-a-profile')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

    def test_update_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, tenant_id=self.tenant,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_action_add_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'add_nodes': {
                'nodes': [ 'xxxx-yyyy-zzzz', ],
            }
        }

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.tenant,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_add_nodes', {
                'identity': cid, 'nodes': ['xxxx-yyyy-zzzz'],
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_del_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'del_nodes': {
                'nodes': [ 'xxxx-yyyy-zzzz', ],
            }
        }

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.tenant,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_del_nodes', {
                'identity': cid, 'nodes': ['xxxx-yyyy-zzzz'],
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_scale_out(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'scale_out': {'count': 1}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.tenant,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_scale_out', {
                'identity': cid, 'count': 1,
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_scale_in(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'scale_in': {'count': 1}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.tenant,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_scale_in', {
                'identity': cid, 'count': 1,
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_attach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'policy_id': 'xxxx-yyyy'}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.tenant,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_attach', {
                'identity': cid, 'policy': 'xxxx-yyyy',
                'level': 50, 'enabled': True, 'cooldown': 0,
                'priority': 50,
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_detach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'xxxx-yyyy'}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.tenant,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_detach', {
                'identity': cid, 'policy': 'xxxx-yyyy',
            })
        )
        self.assertEqual(eng_resp, resp)
