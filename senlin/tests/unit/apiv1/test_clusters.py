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
from oslo_config import cfg
import six
import webob
from webob import exc

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import clusters
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.apiv1 import shared
from senlin.tests.unit.common import base


class ClusterDataTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterDataTest, self).setUp()
        self.body = {
            'name': 'test_cluster',
            'profile_id': 'some_profile',
            'parent': 'another_cluster',
            'metadata': {'tag_key': 'tag_value'},
            'desired_capacity': 5,
            'max_size': 10,
            'min_size': 0,
            'timeout': 60,
        }

    def test_cluster_name(self):
        data = clusters.ClusterData(self.body)
        self.assertEqual('test_cluster', data.name)
        self.assertEqual('some_profile', data.profile)
        self.assertEqual('another_cluster', data.parent)
        self.assertEqual({'tag_key': 'tag_value'}, data.metadata)
        self.assertEqual(5, data.desired_capacity)
        self.assertEqual(10, data.max_size)
        self.assertEqual(0, data.min_size)
        self.assertEqual(60, data.timeout)

    def test_timeout_use_default(self):
        body = {}
        data = clusters.ClusterData(body)
        self.assertEqual(cfg.CONF.default_action_timeout, data.timeout)

    def _test_data_type_errors(self, func_name):
        for key in ['desired_capacity', 'min_size', 'timeout']:
            for value in [' ', 'big', {}, '3.3', '-3']:
                body = {key: value}
                data = clusters.ClusterData(body)
                func = getattr(data, func_name)
                ex = self.assertRaises(senlin_exc.InvalidParameter, func)
                d = {'k': key, 'v': value}
                msg = "Invalid value '%(v)s' specified for '%(k)s'" % d
                self.assertEqual(msg, six.text_type(ex))

        # negative numbers are allowed for max_size
        key = 'max_size'
        for value in [' ', 'big', {}, '3.3']:
            body = {key: value}
            data = clusters.ClusterData(body)
            func = getattr(data, func_name)
            ex = self.assertRaises(senlin_exc.InvalidParameter, func)
            d = {'k': key, 'v': value}
            msg = "Invalid value '%(v)s' specified for '%(k)s'" % d
            self.assertEqual(msg, six.text_type(ex))

    def test_data_type_errors_for_create(self):
        self._test_data_type_errors('validate_for_create')

    def test_data_type_errors_for_update(self):
        self._test_data_type_errors('validate_for_update')

    def test_name_missing_for_create(self):
        body = self.body
        del body['name']
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_create)
        self.assertEqual('No cluster name specified.', six.text_type(ex))

    def test_desired_capacity_missing_for_create(self):
        body = self.body
        del body['desired_capacity']
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_create)
        self.assertEqual('No cluster desired capacity provided.',
                         six.text_type(ex))

    def test_profile_missing_for_create(self):
        body = self.body
        del body['profile_id']
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_create)
        self.assertIn('No cluster profile provided.', six.text_type(ex))

    def test_min_size_vs_desired_capacity_for_create(self):
        body = {
            'name': 'FOO',
            'desired_capacity': 3,
            'profile_id': 'xx-yy',
            'min_size': 1,
        }
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_create())

        body['min_size'] = 3
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_create())

        body['min_size'] = 4
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_create)
        self.assertIn('Cluster min_size, if specified, must be less than or '
                      'equal to its desired capacity.', six.text_type(ex))

    def test_max_size_vs_desired_capacity_for_create(self):
        body = {
            'name': 'FOO',
            'desired_capacity': 3,
            'profile_id': 'xx-yy',
        }

        body['max_size'] = 3
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_create())

        # -1 means unconstrained
        body['max_size'] = -1
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_create())

        body['max_size'] = 2
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_create)
        self.assertEqual('Cluster max_size, if specified, must be greater '
                         'than or equal to its desired capacity. Setting '
                         'max_size to -1 means no upper limit on cluster '
                         'size.',
                         six.text_type(ex))

    def test_simple_keys_for_update(self):
        body = {}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'min_size': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'max_size': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'desired_capacity': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

    def test_min_size_vs_desired_capacity_for_update(self):
        body = {'min_size': 0, 'desired_capacity': 1}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'min_size': 0, 'desired_capacity': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'min_size': 3, 'desired_capacity': 2}
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_update)
        self.assertEqual('Cluster min_size, if specified, must be less than '
                         'or equal to its desired capacity.',
                         six.text_type(ex))

    def test_max_size_vs_desired_capacity_for_update(self):
        body = {'max_size': 1, 'desired_capacity': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'max_size': 0, 'desired_capacity': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        # -1 means no upper limit
        body = {'max_size': -1, 'desired_capacity': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'max_size': 0, 'desired_capacity': 1}
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_update)
        self.assertEqual('Cluster max_size, if specified, must be greater '
                         'than or equal to its desired capacity. Setting '
                         'max_size to -1 means no upper limit on cluster '
                         'size.', six.text_type(ex))

    def test_min_size_vs_max_size_for_update(self):
        body = {'min_size': 0, 'max_size': 0}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        # -1 means no upper limit
        body = {'min_size': 1000, 'max_size': -1}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.validate_for_update())

        body = {'min_size': 6, 'max_size': 5}
        data = clusters.ClusterData(body)
        ex = self.assertRaises(exc.HTTPBadRequest, data.validate_for_update)
        self.assertEqual('Cluster max_size, if specified, must be greater '
                         'than or equal to its min_size. Setting max_size to '
                         '-1 means no upper limit on cluster size.',
                         six.text_type(ex))


@mock.patch.object(policy, 'enforce')
class ClusterControllerTest(shared.ControllerTest, base.SenlinTestCase):
    '''Test case for the cluster controoler.'''

    def setUp(self):
        super(ClusterControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = clusters.ClusterController(options=cfgopts)

    def test_default(self, mock_enforce):
        self.assertRaises(exc.HTTPNotFound, self.controller.default, None)

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
            u'min_size': 0,
            u'max_size': 0,
            u'desired_capacity': 0,
            u'timeout': 60,
            u'status': u'ACTIVE',
            u'status_reason': u'Cluster successfully created.',
            u'metadata': {},
            u'data': {},
            u'nodes': [],
            u'policies': [],
            u'profile_name': u'test_profile',
        }]

        mock_call.return_value = engine_resp

        result = self.controller.index(req, tenant_id=req.context.project)
        expected = {u'clusters': engine_resp}
        self.assertEqual(expected, result)

        default_args = {'limit': None, 'sort_keys': None, 'marker': None,
                        'sort_dir': None, 'filters': None,
                        'project_safe': True, 'show_deleted': False,
                        'show_nested': False}
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

        self.controller.index(req, tenant_id=self.project)

        rpc_call_args, w = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertEqual(8, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('sort_keys', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort_dir', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('project_safe', engine_args)
        self.assertNotIn('balrog', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelist_filter_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'status': 'fake status',
            'name': 'fake name',
            'user': 'fake username',
            'project': 'fake project',
            'owner': 'no such key',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/clusters', params=params)
        mock_call.return_value = []

        self.controller.index(req, tenant_id=self.project)

        rpc_call_args, w = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(4, len(filters))
        self.assertIn('status', filters)
        self.assertIn('name', filters)
        self.assertIn('project', filters)
        self.assertIn('user', filters)
        self.assertNotIn('owner', filters)
        self.assertNotIn('balrog', filters)

    def test_index_show_deleted_false(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_deleted': 'False'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.project)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                        filters=mock.ANY,
                                                        project_safe=True,
                                                        show_deleted=False)

    def test_index_show_deleted_true(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_deleted': 'True'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.project)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                        filters=mock.ANY,
                                                        project_safe=True,
                                                        show_deleted=True)

    def test_index_show_nested_false(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_nested': 'False'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.project)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                        filters=mock.ANY,
                                                        project_safe=True,
                                                        show_nested=False)

    def test_index_show_nested_true(self, mock_enforce):
        rpc_client = self.controller.rpc_client
        rpc_client.cluster_list = mock.Mock(return_value=[])

        params = {'show_nested': 'True'}
        req = self._get('/clusters', params=params)
        self.controller.index(req, tenant_id=self.project)
        rpc_client.cluster_list.assert_called_once_with(mock.ANY,
                                                        filters=mock.ANY,
                                                        project_safe=True,
                                                        show_nested=True)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_remote_attribute_error(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/clusters')

        mock_call.side_effect = shared.to_remote_error(AttributeError())

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.project)

        self.assertEqual(500, resp.json['code'])
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
                                              req, tenant_id=self.project)

        self.assertEqual(500, resp.json['code'])
        self.assertEqual('Exception', resp.json['error']['type'])
        mock_call.assert_called_once_with(
            req.context, ('cluster_list', mock.ANY))

    def test_index_error_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)

        req = self._get('/clusters')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, tenant_id=self.project)

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
                'parent': None,
                'metadata': {},
                'timeout': None,
            }
        }

        req = self._post('/clusters', json.dumps(body))

        engine_response = {
            'name': 'test_cluster',
            'desired_capacity': 0,
            'profile_id': 'xxxx-yyyy',
            'min_size': 0,
            'max_size': 0,
            'parent': None,
            'metadata': {},
            'timeout': 60,
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, tenant_id=self.project, body=body)

        mock_call.assert_called_with(
            req.context,
            ('cluster_create', {
                'name': 'test_cluster',
                'desired_capacity': 0,
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'parent': None,
                'metadata': {},
                'timeout': None
            })
        )

        expected = {'cluster': engine_response}
        self.assertEqual(expected, resp)

    def test_create_maleformed_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'name': 'test_cluster',
            'profile_id': 'xxxx-yyyy',
            'min_size': 0,
            'max_size': 0,
            'desired_capacity': 0,
            'parent': None,
            'metadata': {},
            'timeout': None,
        }

        req = self._post('/clusters', json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, tenant_id=self.project, body=body)

        self.assertIn("Malformed request data, missing 'cluster' key "
                      "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_create_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', False)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'desired_capacity': 0,
                'parent': None,
                'metadata': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', json.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_create_err_engine(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'desired_capacity': -1,
                'parent': None,
                'metadata': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', json.dumps(body))

        error = senlin_exc.InvalidParameter(name='desired_capacity', value=-1)
        self.patchobject(rpc_client.EngineClient, 'call', side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, tenant_id=self.project,
                                              body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])

    def test_create_err_cluster_bad_reqest(self, mock_enforce):
        cfg.CONF.set_override('debug', True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'desired_capacity': 0,
                'parent': None,
                'metadata': {},
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
            u'min_size': 0,
            u'max_size': 0,
            u'desired_capacity': 0,
            u'timeout': 60,
            u'status': u'ACTIVE',
            u'status_reason': u'Cluster successfully created.',
            u'metadata': {},
            u'data': {},
            u'nodes': [],
            u'policies': [],
            u'profile_name': u'test_profile',
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        response = self.controller.get(req, tenant_id=self.project,
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
                                              req, tenant_id=self.project,
                                              cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._get('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, tenant_id=self.project,
                                              cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_delete(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = {'action': 'action_id'}

        self.assertRaises(webob.exc.HTTPNoContent,
                          self.controller.delete,
                          req, tenant_id=self.project,
                          cluster_id=cid)
        mock_call.assert_called_with(req.context,
                                     ('cluster_delete', {'identity': cid}))

    def test_cluster_delete_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_delete_engine_error(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        self.patchobject(rpc_client.EngineClient, 'cluster_delete',
                         return_value=None)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              cluster_id=cid)
        self.assertEqual(500, resp.status_int)
        self.assertIn('Failed deleting cluster', six.text_type(resp))

    def test_cluster_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, tenant_id=self.project,
                                              cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_update(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'cluster': {
                'desired_capacity': 0,
                'profile_id': 'xxxx-yyyy-zzzz',
                'min_size': 0,
                'max_size': 0,
            }
        }

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        self.assertRaises(exc.HTTPAccepted,
                          self.controller.update,
                          req, tenant_id=self.project,
                          cluster_id=cid,
                          body=body)

        args = {
            'name': None,
            'parent': None,
            'metadata': None,
            'profile_id': 'xxxx-yyyy-zzzz',
            'timeout': cfg.CONF.default_action_timeout,
            'identity': cid,
        }
        mock_call.assert_called_once_with(req.context,
                                          ('cluster_update', args))

    def test_cluster_update_missing_cluster_key(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'profile_id': 'xxxx-yyyy-zzzz'}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'cluster_update')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)

        self.assertIn("Malformed request data, missing 'cluster' key "
                      "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_cluster_update_timeout_non_int(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'timeout': '10min'}}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'cluster_update')
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.update,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)

        self.assertEqual(_("Invalid value '10min' specified for 'timeout'"),
                         six.text_type(ex))

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
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_update_unsupported_status(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.FeatureNotSupported(feature='Wrong status')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(409, resp.json['code'])
        self.assertEqual('FeatureNotSupported', resp.json['error']['type'])

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
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

    def test_cluster_update_profile_type_mismatch(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'profile-of-diff-type'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.ProfileTypeNotMatch(message='not matching')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('ProfileTypeNotMatch', resp.json['error']['type'])

    def test_update_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_action_add_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'add_nodes': {
                'nodes': ['xxxx-yyyy-zzzz', ],
            }
        }

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_add_nodes', {
                'identity': cid, 'nodes': ['xxxx-yyyy-zzzz'],
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_add_nodes_none(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'somearg': 'somevalue'}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)

        self.assertEqual('No node to add', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_add_nodes_empty(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'nodes': []}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)

        self.assertEqual('No node to add', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_add_nodes_bad_requests(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'nodes': ['bad-node-1']}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        error = senlin_exc.SenlinBadRequest(msg='Nodes not found: bad-node-1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SenlinBadRequest', resp.json['error']['type'])
        self.assertIn('Nodes not found: bad-node-1',
                      resp.json['error']['message'])

    def test_cluster_action_del_nodes(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'del_nodes': {
                'nodes': ['xxxx-yyyy-zzzz', ],
            }
        }

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_del_nodes', {
                'identity': cid, 'nodes': ['xxxx-yyyy-zzzz'],
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_del_nodes_none(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'somearg': 'somevalue'}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)

        self.assertEqual('No node to delete', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_del_nodes_empty(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': []}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)

        self.assertEqual('No node to delete', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_del_nodes_bad_requests(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': ['bad-node-1']}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        error = senlin_exc.SenlinBadRequest(msg='Nodes not found: bad-node-1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('SenlinBadRequest', resp.json['error']['type'])
        self.assertIn('Nodes not found: bad-node-1',
                      resp.json['error']['message'])

    def _test_cluster_action_resize_with_types(self, adj_type, mock_enforce):
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
        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_resize', {
                'identity': cid,
                'adj_type': adj_type,
                'number': 1,
                'min_size': 0,
                'max_size': 10,
                'min_step': 1,
                'strict': True
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_resize_with_exact_capacity(self, mock_enforce):
        self._test_cluster_action_resize_with_types('EXACT_CAPACITY',
                                                    mock_enforce)

    def test_cluster_action_resize_with_change_capacity(self, mock_enforce):
        self._test_cluster_action_resize_with_types('CHANGE_IN_CAPACITY',
                                                    mock_enforce)

    def test_cluster_action_resize_with_change_percentage(self, mock_enforce):
        self._test_cluster_action_resize_with_types('CHANGE_IN_PERCENTAGE',
                                                    mock_enforce)

    def test_cluster_action_resize_with_bad_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': 'NOT_QUITE_SURE',
                'number': 1
            }
        }
        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        error = senlin_exc.InvalidParameter(name='adjustment_type',
                                            value='NOT_QUITE_SURE')

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)
        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])
        self.assertIn("Invalid value 'NOT_QUITE_SURE' specified for "
                      "'adjustment_type'", resp.json['error']['message'])

    def test_cluster_action_resize_missing_number(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': 'EXACT_CAPACITY',
            }
        }
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual('Missing number value for resize operation.',
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_missing_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'number': 2}}
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual('Missing adjustment_type value for resize operation.',
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def _test_cluster_resize_param_not_int(self, param, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {
            'resize': {
                'adjustment_type': 'CHANGE_IN_CAPACITY',
                'number': 1,
            }
        }
        body['resize'][param] = 'BOGUS'
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual("Invalid value 'BOGUS' specified for '%s'" %
                         param, six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_number_not_int(self, mock_enforce):
        self._test_cluster_resize_param_not_int('number', mock_enforce)

    def test_cluster_action_resize_min_size_not_int(self, mock_enforce):
        self._test_cluster_resize_param_not_int('min_size', mock_enforce)

    def test_cluster_action_resize_max_size_not_int(self, mock_enforce):
        self._test_cluster_resize_param_not_int('max_size', mock_enforce)

    def test_cluster_action_resize_min_step_not_int(self, mock_enforce):
        self._test_cluster_resize_param_not_int('min_step', mock_enforce)

    def test_cluster_action_resize_min_size_non_neg(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'min_size': -1}}
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual("Invalid value '-1' specified for 'min_size'",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_max_size_neg_ok(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'max_size': -1}}
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid, body=body)
        mock_call.assert_called_once_with(
            req.context,
            ('cluster_resize', {
                'identity': cid,
                'adj_type': None,
                'number': None,
                'min_size': None,
                'max_size': -1,
                'min_step': None,
                'strict': None
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_resize_max_size_too_small(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'min_size': 2, 'max_size': 1}}
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual("The specified min_size (2) is greater than "
                         "the specified max_size (1).", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_min_with_max_neg(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'min_size': 2, 'max_size': -1}}
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_resize', {
                'identity': cid,
                'adj_type': None,
                'number': None,
                'min_size': 2,
                'max_size': -1,
                'min_step': None,
                'strict': None
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_resize_strict_non_bool(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'strict': 'yes'}}
        req = self._put('/clusters/%s/action' % cid, json.dumps(body))

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual("Invalid value 'yes' specified for 'strict'",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_scale_out(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'scale_out': {'count': 1}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
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

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_scale_in', {
                'identity': cid, 'count': 1,
            })
        )
        self.assertEqual(eng_resp, resp)

    def _cluster_action_scale_non_int(self, action, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {action: {'count': 'abc'}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        error = senlin_exc.InvalidParameter(name='count', value='abc')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])
        self.assertIn("Invalid value 'abc' specified for 'count'",
                      resp.json['error']['message'])

    def test_cluster_action_scale_out_non_int(self, mock_enforce):
        self._cluster_action_scale_non_int('scale_out', mock_enforce)

    def test_cluster_action_scale_in_non_int(self, mock_enforce):
        self._cluster_action_scale_non_int('scale_in', mock_enforce)

    def test_cluster_action_attach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'policy_id': 'xxxx-yyyy'}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_attach', {
                'identity': cid, 'policy': 'xxxx-yyyy',
                'level': None, 'enabled': True, 'cooldown': None,
                'priority': 50,
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_attach_policy_with_fields(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {
            'policy_id': 'xxxx-yyyy',
            'priority': 40,
            'cooldown': 20,
            'level': 30,
            'enabled': False,
        }}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_attach', {
                'identity': cid, 'policy': 'xxxx-yyyy',
                'level': 30, 'enabled': False, 'cooldown': 20,
                'priority': 40,
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_attach_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'policy_id': 'not-a-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.PolicyNotFound(policy='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_cluster_action_detach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'xxxx-yyyy'}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_detach', {
                'identity': cid, 'policy': 'xxxx-yyyy',
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_detach_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'not-a-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.PolicyNotFound(policy='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_cluster_action_update_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {
            'policy_id': 'xxxx-yyyy',
            'priority': 99,
        }}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, tenant_id=self.project,
                                      cluster_id=cid,
                                      body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_update', {
                'identity': cid, 'policy': 'xxxx-yyyy',
                'priority': 99, 'level': None, 'enabled': None,
                'cooldown': None,
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_update_policy_non_int(self, mock_enforce):
        # NOTE: There are other cases of invalid parameter inputs, but
        # we only take one of them as the example for testing. The rest
        # of them should be tested at the engine side because this test
        # case cares only about whether the API layer can respond to such
        # 'error's correctly.
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {
            'policy_id': 'xxxx-yyyy',
            'priority': 'abc',
        }}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, json.dumps(body))

        error = senlin_exc.InvalidParameter(name='priority', value='abc')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])
        self.assertIn("Invalid value 'abc' specified for 'priority'",
                      resp.json['error']['message'])

    def test_cluster_action_update_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {'policy_id': 'not-a-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.PolicyNotFound(policy='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_cluster_action_cluster_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'non-existent-cluster'
        body = {'add_nodes': {'nodes': ['xxxx-yyyy-zzzz']}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_action_missing_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual('No action specified', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_multiple_actions(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'action_1': {}, 'action_2': {}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual('Multiple actions specified', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_unsupported_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'fly': None}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, tenant_id=self.project,
                               cluster_id=cid,
                               body=body)
        self.assertEqual("Unrecognized action 'fly' specified",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', False)
        cid = 'aaaa-bbbb-cccc'
        body = {'someaction': {'param': 'value'}}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        json.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, tenant_id=self.project,
                                              cluster_id=cid,
                                              body=body)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
