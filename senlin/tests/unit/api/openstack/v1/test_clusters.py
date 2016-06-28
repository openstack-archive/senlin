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
import webob
from webob import exc

from oslo_config import cfg
from oslo_serialization import jsonutils

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import clusters
from senlin.common import exception as senlin_exc
from senlin.common.i18n import _
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


class ClusterDataTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterDataTest, self).setUp()
        self.body = {
            'name': 'test_cluster',
            'profile_id': 'some_profile',
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
        self.assertEqual({'tag_key': 'tag_value'}, data.metadata)
        self.assertEqual(5, data.desired_capacity)
        self.assertEqual(10, data.max_size)
        self.assertEqual(0, data.min_size)
        self.assertEqual(60, data.timeout)

    def test_timeout_use_default(self):
        body = {}
        data = clusters.ClusterData(body)
        self.assertIsNone(data.timeout)

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
            u'init_time': u'2015-01-09T09:13:11Z',
            u'created_time': u'2015-01-09T09:16:45Z',
            u'updated_time': None,
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

        result = self.controller.index(req)

        expected = {u'clusters': engine_resp}
        self.assertEqual(expected, result)

        default_args = {
            'limit': None,
            'marker': None,
            'filters': None,
            'sort': None,
            'project_safe': True,
        }
        mock_call.assert_called_once_with(
            req.context, ('cluster_list', default_args))

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelists_pagination_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'name': 'whatever',
            'limit': 'fake limit',
            'marker': 'fake marker',
            'sort': 'fake sort option',
        }
        req = self._get('/clusters', params=params)
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, w = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertEqual(5, len(engine_args))
        self.assertIn('limit', engine_args)
        self.assertIn('marker', engine_args)
        self.assertIn('sort', engine_args)
        self.assertIn('filters', engine_args)
        self.assertIn('project_safe', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelists_pagination_invalid_params(self, mock_call,
                                                        mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/clusters', params=params)
        mock_call.return_value = []
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelist_filter_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'status': 'fake status',
            'name': 'fake name',
        }
        req = self._get('/clusters', params=params)
        mock_call.return_value = []

        self.controller.index(req)

        rpc_call_args, w = mock_call.call_args
        engine_args = rpc_call_args[1][1]
        self.assertIn('filters', engine_args)

        filters = engine_args['filters']
        self.assertEqual(2, len(filters))
        self.assertIn('status', filters)
        self.assertIn('name', filters)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_whitelist_filter_invalid_params(self, mock_call,
                                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!'
        }
        req = self._get('/clusters', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_global_project_true(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'True'}
        req = self._get('/clusters', params=params)

        self.controller.index(req)

        call_args, w = mock_call.call_args
        call_args = call_args[1][1]
        self.assertIn('project_safe', call_args)
        self.assertFalse(call_args['project_safe'])

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_global_project_false(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'False'}
        req = self._get('/clusters', params=params)

        self.controller.index(req)

        call_args, w = mock_call.call_args
        call_args = call_args[1][1]
        self.assertIn('project_safe', call_args)
        self.assertTrue(call_args['project_safe'])

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_node_index_global_project_not_bool(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'No'}
        req = self._get('/clusters', params=params)

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'No' specified for 'global_project'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_index_remote_attribute_error(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/clusters')

        mock_call.side_effect = shared.to_remote_error(AttributeError())

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index, req)

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
                                              req)

        self.assertEqual(500, resp.json['code'])
        self.assertEqual('Exception', resp.json['error']['type'])
        mock_call.assert_called_once_with(
            req.context, ('cluster_list', mock.ANY))

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

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.create(req, body=body)

        mock_call.assert_called_with(
            req.context,
            ('cluster_create', {
                'name': 'test_cluster',
                'desired_capacity': 0,
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'metadata': {},
                'timeout': None
            })
        )

        self.assertEqual(engine_response, resp['cluster'])
        self.assertEqual('/actions/fake_action', resp['location'])

    def test_create_maleformed_body(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'create', True)
        body = {
            'name': 'test_cluster',
            'profile_id': 'xxxx-yyyy',
            'min_size': 0,
            'max_size': 0,
            'desired_capacity': 0,
            'metadata': {},
            'timeout': None,
        }

        req = self._post('/clusters', jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.create,
                               req, body=body)

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
                'metadata': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

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
                'metadata': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', jsonutils.dumps(body))

        error = senlin_exc.InvalidParameter(name='desired_capacity', value=-1)
        self.patchobject(rpc_client.EngineClient, 'call', side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create,
                                              req, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])

    def test_create_err_cluster_bad_reqest(self, mock_enforce):
        cfg.CONF.set_override('debug', True, enforce_type=True)
        body = {
            'cluster': {
                'name': 'test_cluster',
                'profile_id': 'xxxx-yyyy',
                'min_size': 0,
                'max_size': 0,
                'desired_capacity': 0,
                'metadata': {},
                'timeout': None,
            }
        }
        req = self._post('/clusters', jsonutils.dumps(body))

        error = senlin_exc.HTTPExceptionDisguise(webob.exc.HTTPBadRequest())
        self.controller.create = mock.MagicMock(side_effect=error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.create, req,
                                              body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('HTTPBadRequest', resp.json['error']['type'])

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
            u'init_time': u'2015-01-09T09:13:11Z',
            u'created_time': u'2015-01-09T09:16:45Z',
            u'updated_time': None,
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
        response = self.controller.get(req, cluster_id=cid)

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
                                              req, cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._get('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_delete(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', True)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.return_value = {'action': 'FAKE_ID'}

        res = self.controller.delete(req, cluster_id=cid)
        result = {'location': '/actions/FAKE_ID'}
        self.assertEqual(result, res)
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
                                              req, cluster_id=cid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_delete_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'delete', False)
        cid = 'aaaa-bbbb-cccc'
        req = self._delete('/clusters/%(cluster_id)s' % {'cluster_id': cid})
        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.delete,
                                              req, cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_update(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'cluster': {
                'desired_capacity': 5,
                'profile_id': 'xxxx-yyyy-zzzz',
                'min_size': None,
                'max_size': None,
            }
        }

        engine_resp = {
            'id': cid,
            'name': 'test_cluster',
            'profile_id': 'xxxx-yyyy-zzzz',
            'desired_capacity': 5,
            'min_size': 0,
            'max_size': -1,
            'action': 'fake_action',
        }

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        res = self.controller.update(req, cluster_id=cid, body=body)

        args = {
            'name': None,
            'metadata': None,
            'profile_id': 'xxxx-yyyy-zzzz',
            'timeout': None,
            'identity': cid,
        }
        mock_call.assert_called_once_with(req.context,
                                          ('cluster_update', args))
        self.assertEqual(engine_resp, res['cluster'])
        self.assertEqual('/actions/fake_action', res['location'])

    def test_cluster_update_missing_cluster_key(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'profile_id': 'xxxx-yyyy-zzzz'}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'cluster_update')
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.update,
                               req, cluster_id=cid, body=body)

        self.assertIn("Malformed request data, missing 'cluster' key "
                      "in request body.", six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_cluster_update_timeout_non_int(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'timeout': '10min'}}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'cluster_update')
        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.update,
                               req, cluster_id=cid, body=body)

        self.assertEqual(_("Invalid value '10min' specified for 'timeout'"),
                         six.text_type(ex))

        self.assertFalse(mock_call.called)

    def test_cluster_update_cluster_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'non-existent-cluster'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_update_unsupported_status(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.FeatureNotSupported(feature='Wrong status')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(409, resp.json['code'])
        self.assertEqual('FeatureNotSupported', resp.json['error']['type'])

    def test_cluster_update_profile_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'not-a-profile'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.ProfileNotFound(profile='not-a-profile')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ProfileNotFound', resp.json['error']['type'])

    def test_cluster_update_profile_type_mismatch(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'profile-of-diff-type'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.ProfileTypeNotMatch(message='not matching')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('ProfileTypeNotMatch', resp.json['error']['type'])

    def test_update_err_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'update', False)
        cid = 'aaaa-bbbb-cccc'
        body = {'cluster': {'profile_id': 'xxxx-yyyy-zzzz'}}

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.update,
                                              req, cluster_id=cid, body=body)

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

        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_add_nodes', {
                'identity': cid, 'nodes': ['xxxx-yyyy-zzzz'],
            })
        )
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_cluster_action_add_nodes_none(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'somearg': 'somevalue'}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('No node to add', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_add_nodes_empty(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'nodes': []}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('No node to add', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_add_nodes_bad_requests(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'add_nodes': {'nodes': ['bad-node-1']}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        error = senlin_exc.BadRequest(msg='Nodes not found: bad-node-1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('BadRequest', resp.json['error']['type'])
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

        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_del_nodes', {
                'identity': cid, 'nodes': ['xxxx-yyyy-zzzz'],
            })
        )
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_cluster_action_del_nodes_none(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'somearg': 'somevalue'}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('No node to delete', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_del_nodes_empty(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': []}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('No node to delete', six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_cluster_action_del_nodes_bad_requests(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'del_nodes': {'nodes': ['bad-node-1']}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        error = senlin_exc.BadRequest(msg='Nodes not found: bad-node-1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('BadRequest', resp.json['error']['type'])
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
        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

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
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

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
                        'cluster_id': cid}, jsonutils.dumps(body))

        error = senlin_exc.InvalidParameter(name='adjustment_type',
                                            value='NOT_QUITE_SURE')

        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)
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
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual('Missing number value for resize operation.',
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_missing_type(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'number': 2}}
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
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
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
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
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual("Invalid value '-1' specified for 'min_size'",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_max_size_neg_ok(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'max_size': -1}}
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)
        mock_call.assert_called_once_with(
            req.context,
            ('cluster_resize', {
                'identity': cid,
                'adj_type': None,
                'number': None,
                'min_size': None,
                'max_size': -1,
                'min_step': None,
                'strict': True
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_resize_max_size_too_small(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'min_size': 2, 'max_size': 1}}
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual("The specified min_size (2) is greater than "
                         "the specified max_size (1).", six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_resize_min_with_max_neg(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'min_size': 2, 'max_size': -1}}
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_resize', {
                'identity': cid,
                'adj_type': None,
                'number': None,
                'min_size': 2,
                'max_size': -1,
                'min_step': None,
                'strict': True
            })
        )
        self.assertEqual(eng_resp, resp)

    def test_cluster_action_resize_strict_non_bool(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        cid = 'aaaa-bbbb-cccc'
        body = {'resize': {'strict': 'yes'}}
        req = self._put('/clusters/%s/action' % cid, jsonutils.dumps(body))

        ex = self.assertRaises(senlin_exc.InvalidParameter,
                               self.controller.action,
                               req, cluster_id=cid, body=body)
        self.assertEqual("Invalid value 'yes' specified for 'strict'",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    def test_cluster_action_scale_out(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'scale_out': {'count': 1}}

        eng_resp = {'action': {'id': 'action-id', 'target': cid}}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

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
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

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
                        'cluster_id': cid}, jsonutils.dumps(body))

        error = senlin_exc.InvalidParameter(name='count', value='abc')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(400, resp.json['code'])
        self.assertEqual('InvalidParameter', resp.json['error']['type'])
        self.assertIn("Invalid value 'abc' specified for 'count'",
                      resp.json['error']['message'])

    def test_cluster_action_scale_out_non_int(self, mock_enforce):
        self._cluster_action_scale_non_int('scale_out', mock_enforce)

    def test_cluster_action_scale_in_non_int(self, mock_enforce):
        self._cluster_action_scale_non_int('scale_in', mock_enforce)

    def test_cluster_action_check(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'check': {}}

        eng_resp = {'action': 'action-id'}

        req = self._post('/clusters/%(cluster_id)s/action' % {
            'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_check', {
                'identity': cid,
                'params': {}
            })
        )

        self.assertEqual(eng_resp, resp)

    def test_cluster_action_check_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'unknown-cluster'
        body = {'check': {}}
        req = self._post('/clusters/%(cluster_id)s/actions' % {
            'cluster_id': cid}, jsonutils.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_action_recover(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'recover': {}}

        eng_resp = {'action': 'action-id'}

        req = self._post('/clusters/%(cluster_id)s/action' % {
            'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_recover', {
                'identity': cid,
                'params': {}
            })
        )

        self.assertEqual(eng_resp, resp)

    def test_cluster_action_recover_with_ops(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {
            'recover': {
                'operation': 'REBUILD'
            }
        }

        eng_resp = {'action': 'action-id'}

        req = self._post('/clusters/%(cluster_id)s/action' % {
            'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_recover', {
                'identity': cid,
                'params': {
                    'operation': 'REBUILD'
                }
            })
        )

        self.assertEqual(eng_resp, resp)

    def test_cluster_action_recover_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'unknown-cluster'
        body = {'recover': {}}
        req = self._post('/clusters/%(cluster_id)s/actions' % {
            'cluster_id': cid}, jsonutils.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test__sanitize_policy(self, mock_enforce):
        data = {
            'policy_id': 'FOO',
            'enabled': True
        }
        res = self.controller._sanitize_policy(data)
        self.assertEqual(res, data)

    def test__sanitize_policy_not_dict(self, mock_enforce):
        data = ['aha, bad data']
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller._sanitize_policy, data)
        self.assertEqual("The data provided is not a map.",
                         six.text_type(ex))

    def test__sanitize_policy_missing_policy_id(self, mock_enforce):
        data = {
            'Foo': 'Bar'
        }
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller._sanitize_policy, data)
        self.assertEqual("The 'policy_id' field is missing in the request.",
                         six.text_type(ex))

    def test__sanitize_policy_bad_enabled_value(self, mock_enforce):
        data = {
            'policy_id': 'FAKE',
        }

        for value in ['yes', '1', 1]:
            data['enabled'] = value
            ex = self.assertRaises(exc.HTTPBadRequest,
                                   self.controller._sanitize_policy, data)
            expected = "Invalid value '%s' specified for 'enabled'" % value
            self.assertEqual(expected, six.text_type(ex))

    def test_cluster_action_attach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'policy_id': 'xxxx-yyyy'}}

        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_attach', {
                'identity': cid, 'policy': 'xxxx-yyyy', 'enabled': True,
            })
        )
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_cluster_action_attach_policy_with_fields(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {
            'policy_id': 'xxxx-yyyy',
            'enabled': False,
        }}

        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_attach', {
                'identity': cid, 'policy': 'xxxx-yyyy', 'enabled': False,
            })
        )
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_cluster_action_attach_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_attach': {'policy_id': 'not-a-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.PolicyNotFound(policy='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_cluster_action_detach_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'xxxx-yyyy'}}

        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_detach', {
                'identity': cid, 'policy': 'xxxx-yyyy',
            })
        )
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_cluster_action_detach_policy_not_specified(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy': 'fake-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertEqual('No policy specified for detach.', six.text_type(ex))

    def test_cluster_action_detach_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_detach': {'policy_id': 'not-a-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.PolicyNotFound(policy='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_cluster_action_update_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {
            'policy_id': 'xxxx-yyyy',
            'enabled': True,
        }}

        eng_resp = {'action': 'action-id'}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=eng_resp)

        resp = self.controller.action(req, cluster_id=cid, body=body)

        mock_call.assert_called_once_with(
            req.context,
            ('cluster_policy_update', {
                'identity': cid, 'policy': 'xxxx-yyyy', 'enabled': True,
            })
        )
        result = {
            'action': 'action-id',
            'location': '/actions/action-id',
        }
        self.assertEqual(result, resp)

    def test_cluster_action_update_policy_invalid_values(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {
            'policy_id': 'xxxx-yyyy',
            'enabled': 'good',
        }}

        req = self._put('/clusters/%(cluster_id)s/action' % {
                        'cluster_id': cid}, jsonutils.dumps(body))

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.action,
                               req, cluster_id=cid, body=body)

        self.assertIn("Invalid value 'good' specified for 'enabled'",
                      six.text_type(ex))

    def test_cluster_action_update_policy_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {'policy_update': {'policy_id': 'not-a-policy'}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.PolicyNotFound(policy='not-a-policy')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyNotFound', resp.json['error']['type'])

    def test_cluster_action_cluster_notfound(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'non-existent-cluster'
        body = {'add_nodes': {'nodes': ['xxxx-yyyy-zzzz']}}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

        error = senlin_exc.ClusterNotFound(cluster=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.action,
                                              req, cluster_id=cid, body=body)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ClusterNotFound', resp.json['error']['type'])

    def test_cluster_action_missing_action(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'action', True)
        cid = 'aaaa-bbbb-cccc'
        body = {}
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

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
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

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
        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

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

        req = self._put('/clusters/%(cluster_id)s' % {'cluster_id': cid},
                        jsonutils.dumps(body))

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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.collect(req, cluster_id=cid, path=path)

        self.assertEqual(engine_response, resp)
        mock_call.assert_called_once_with(
            req.context,
            ('cluster_collect', {'identity': cid, 'path': path,
                                 'project_safe': True}),
            version='1.1')

    def test_cluster_collect_version_mismatch(self, mock_enforce):
        # NOTE: we skip the mock_enforce setup below because api version check
        #       comes before the policy enforcement and the check fails in
        #       this test case.
        # self._mock_enforce_setup(mock_enforce, 'collect', True)
        cid = 'aaaa-bbbb-cccc'
        path = 'foo.bar'
        req = self._get('/clusters/%(cid)s/attrs/%(path)s' %
                        {'cid': cid, 'path': path}, version='1.1')
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

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
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.collect,
                                              req, cluster_id=cid, path=path)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
        self.assertEqual(0, mock_call.call_count)
