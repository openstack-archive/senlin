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

from oslo_config import cfg
import six

from senlin.common import consts
from senlin.objects.requests import clusters
from senlin.tests.unit.common import base as test_base

CONF = cfg.CONF
CONF.import_opt('default_action_timeout', 'senlin.common.config')
CONF.import_opt('max_nodes_per_cluster', 'senlin.common.config')


class TestClusterCreate(test_base.SenlinTestCase):

    body = {
        'name': 'test-cluster',
        'profile_id': 'test-profile',
    }

    def test_cluster_create_request_body(self):
        sot = clusters.ClusterCreateRequestBody(**self.body)
        self.assertEqual('test-cluster', sot.name)
        self.assertEqual('test-profile', sot.profile_id)

        self.assertFalse(sot.obj_attr_is_set('min_size'))
        self.assertFalse(sot.obj_attr_is_set('max_size'))
        self.assertFalse(sot.obj_attr_is_set('desired_capacity'))
        self.assertFalse(sot.obj_attr_is_set('metadata'))
        self.assertFalse(sot.obj_attr_is_set('timeout'))
        self.assertFalse(sot.obj_attr_is_set('config'))

        sot.obj_set_defaults()

        self.assertTrue(sot.obj_attr_is_set('min_size'))
        self.assertEqual(consts.CLUSTER_DEFAULT_MIN_SIZE, sot.min_size)
        self.assertEqual(consts.CLUSTER_DEFAULT_MAX_SIZE, sot.max_size)
        self.assertEqual({}, sot.metadata)
        self.assertEqual(CONF.default_action_timeout, sot.timeout)
        self.assertEqual({}, sot.config)

    def test_cluster_create_request_body_full(self):
        body = copy.deepcopy(self.body)
        body['min_size'] = 1
        body['max_size'] = 10
        body['desired_capacity'] = 4
        body['metadata'] = {'foo': 'bar'}
        body['timeout'] = 121
        body['config'] = {'k1': 'v1'}

        sot = clusters.ClusterCreateRequestBody(**body)

        self.assertEqual('test-cluster', sot.name)
        self.assertEqual('test-profile', sot.profile_id)
        self.assertEqual(1, sot.min_size)
        self.assertEqual(10, sot.max_size)
        self.assertEqual(4, sot.desired_capacity)
        self.assertEqual({'foo': 'bar'}, sot.metadata)
        self.assertEqual(121, sot.timeout)
        self.assertEqual({'k1': 'v1'}, sot.config)

    def test_request_body_to_primitive(self):
        sot = clusters.ClusterCreateRequestBody(**self.body)
        res = sot.obj_to_primitive()
        self.assertEqual(
            {
                'name': u'test-cluster',
                'profile_id': u'test-profile'
            },
            res['senlin_object.data']
        )
        self.assertEqual('ClusterCreateRequestBody',
                         res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.1', res['senlin_object.version'])
        self.assertIn('profile_id', res['senlin_object.changes'])
        self.assertIn('name', res['senlin_object.changes'])

    def test_request_to_primitive(self):
        body = clusters.ClusterCreateRequestBody(**self.body)
        request = {'cluster': body}
        sot = clusters.ClusterCreateRequest(**request)
        self.assertIsInstance(sot.cluster, clusters.ClusterCreateRequestBody)

        self.assertEqual('test-cluster', sot.cluster.name)
        self.assertEqual('test-profile', sot.cluster.profile_id)

        res = sot.obj_to_primitive()
        self.assertEqual(['cluster'], res['senlin_object.changes'])
        self.assertEqual('ClusterCreateRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])
        data = res['senlin_object.data']['cluster']
        self.assertIn('profile_id', data['senlin_object.changes'])
        self.assertIn('name', data['senlin_object.changes'])
        self.assertEqual('ClusterCreateRequestBody',
                         data['senlin_object.name'])
        self.assertEqual('senlin', data['senlin_object.namespace'])
        self.assertEqual('1.1', data['senlin_object.version'])
        self.assertEqual(
            {'name': u'test-cluster', 'profile_id': u'test-profile'},
            data['senlin_object.data']
        )

    def test_init_body_err_min_size_too_low(self):
        body = copy.deepcopy(self.body)
        body['min_size'] = -1

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual("The value for the min_size field must be greater "
                         "than or equal to 0.",
                         six.text_type(ex))

    def test_init_body_err_min_size_too_high(self):
        body = copy.deepcopy(self.body)
        body['min_size'] = CONF.max_nodes_per_cluster + 1

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual("The value for the min_size field must be less than "
                         "or equal to %s." % CONF.max_nodes_per_cluster,
                         six.text_type(ex))

    def test_init_body_err_max_size_too_low(self):
        body = copy.deepcopy(self.body)
        body['max_size'] = -2

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual("The value for the max_size field must be greater "
                         "than or equal to -1.",
                         six.text_type(ex))

    def test_init_body_err_max_size_too_high(self):
        body = copy.deepcopy(self.body)
        body['max_size'] = CONF.max_nodes_per_cluster + 1

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual("The value for the max_size field must be less than "
                         "or equal to %s." % CONF.max_nodes_per_cluster,
                         six.text_type(ex))

    def test_init_body_err_desired_too_low(self):
        body = copy.deepcopy(self.body)
        body['desired_capacity'] = -1

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual("The value for the desired_capacity field must be "
                         "greater than or equal to 0.",
                         six.text_type(ex))

    def test_init_body_err_desired_too_high(self):
        body = copy.deepcopy(self.body)
        body['desired_capacity'] = CONF.max_nodes_per_cluster + 1

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual(("The value for the desired_capacity field must be "
                          "less than or equal to %s." %
                          CONF.max_nodes_per_cluster),
                         six.text_type(ex))

    def test_init_body_err_timeout_negative(self):
        body = copy.deepcopy(self.body)
        body['timeout'] = -1

        ex = self.assertRaises(ValueError,
                               clusters.ClusterCreateRequestBody,
                               **body)

        self.assertEqual("Value must be >= 0 for field 'timeout'.",
                         six.text_type(ex))


class TestClusterList(test_base.SenlinTestCase):

    params = {
        'project_safe': True,
    }

    def test_init(self):
        sot = clusters.ClusterListRequest()

        self.assertFalse(sot.obj_attr_is_set('project_safe'))
        self.assertFalse(sot.obj_attr_is_set('name'))
        self.assertFalse(sot.obj_attr_is_set('status'))
        self.assertFalse(sot.obj_attr_is_set('limit'))
        self.assertFalse(sot.obj_attr_is_set('marker'))
        self.assertFalse(sot.obj_attr_is_set('sort'))

        sot.obj_set_defaults()

        self.assertTrue(sot.project_safe)
        self.assertFalse(sot.obj_attr_is_set('name'))
        self.assertFalse(sot.obj_attr_is_set('status'))
        self.assertFalse(sot.obj_attr_is_set('limit'))
        self.assertFalse(sot.obj_attr_is_set('marker'))
        self.assertIsNone(sot.sort)

    def test_cluster_list_request_body_full(self):
        params = {
            'name': ['name1'],
            'status': ['ACTIVE'],
            'limit': '4',  # a test of having string as limit
            'marker': '09013587-c1e9-4c98-9c0c-d357004363e1',
            'sort': 'name:asc',
            'project_safe': 'False',  # a test of flexible boolean
        }
        sot = clusters.ClusterListRequest(**params)
        self.assertEqual(['name1'], sot.name)
        self.assertEqual(['ACTIVE'], sot.status)
        self.assertEqual(4, sot.limit)
        self.assertEqual('09013587-c1e9-4c98-9c0c-d357004363e1', sot.marker)
        self.assertEqual('name:asc', sot.sort)
        self.assertFalse(sot.project_safe)


class TestClusterGet(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterGetRequest(identity='foo')

        self.assertEqual('foo', sot.identity)


class TestClusterUpdate(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterUpdateRequest(identity='foo')

        self.assertEqual('foo', sot.identity)
        self.assertFalse(sot.obj_attr_is_set('name'))
        self.assertFalse(sot.obj_attr_is_set('profile_id'))
        self.assertFalse(sot.obj_attr_is_set('metadata'))
        self.assertFalse(sot.obj_attr_is_set('timeout'))
        self.assertFalse(sot.obj_attr_is_set('profile_only'))
        self.assertFalse(sot.obj_attr_is_set('config'))

    def test_init_with_params(self):
        sot = clusters.ClusterUpdateRequest(identity='foo', name='new-name',
                                            profile_id='new-profile',
                                            metadata={'newkey': 'newvalue'},
                                            timeout=4567, profile_only=True,
                                            config={'foo': 'bar'})

        self.assertEqual('foo', sot.identity)
        self.assertEqual('new-name', sot.name)
        self.assertEqual('new-profile', sot.profile_id)
        self.assertEqual({'newkey': 'newvalue'}, sot.metadata)
        self.assertEqual(4567, sot.timeout)
        self.assertTrue(sot.profile_only)
        self.assertEqual({'foo': 'bar'}, sot.config)


class TestClusterAddNodes(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterAddNodesRequest(identity='foo', nodes=['abc'])

        self.assertEqual('foo', sot.identity)
        self.assertEqual(['abc'], sot.nodes)

    def test_init_failed(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterAddNodesRequest,
                               identity='foo', nodes=[])
        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         six.text_type(ex))


class TestClusterDelNodes(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterDelNodesRequest(identity='foo', nodes=['abc'],
                                              destroy_after_deletion=True)

        self.assertEqual('foo', sot.identity)
        self.assertEqual(['abc'], sot.nodes)
        self.assertTrue(sot.destroy_after_deletion)

    def test_init_without_destroy(self):
        sot = clusters.ClusterDelNodesRequest(identity='foo', nodes=['abc'],
                                              destroy_after_deletion=False)

        self.assertEqual('foo', sot.identity)
        self.assertEqual(['abc'], sot.nodes)
        self.assertFalse(sot.destroy_after_deletion)

    def test_init_failed(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterDelNodesRequest,
                               identity='foo', nodes=[])
        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         six.text_type(ex))


class TestClusterResize(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterResizeRequest(identity='foo')

        self.assertEqual('foo', sot.identity)
        self.assertFalse(sot.obj_attr_is_set('adjustment_type'))
        self.assertFalse(sot.obj_attr_is_set('number'))
        self.assertFalse(sot.obj_attr_is_set('min_size'))
        self.assertFalse(sot.obj_attr_is_set('max_size'))
        self.assertFalse(sot.obj_attr_is_set('min_step'))
        self.assertFalse(sot.obj_attr_is_set('strict'))

    def test_init_with_params(self):
        sot = clusters.ClusterResizeRequest(identity='foo',
                                            adjustment_type='EXACT_CAPACITY',
                                            number=100,
                                            min_size=10,
                                            max_size=100,
                                            min_step=1,
                                            strict=False)

        self.assertEqual('foo', sot.identity)
        self.assertEqual('EXACT_CAPACITY', sot.adjustment_type)
        self.assertEqual(100, sot.number)
        self.assertEqual(10, sot.min_size)
        self.assertEqual(100, sot.max_size)
        self.assertEqual(1, sot.min_step)
        self.assertFalse(sot.strict)

    def test_init_failed_type(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterResizeRequest,
                               identity='foo', adjustment_type='BOGUS')
        self.assertEqual("Value 'BOGUS' is not acceptable for field "
                         "'adjustment_type'.",
                         six.text_type(ex))

    def test_init_failed_number(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterResizeRequest,
                               identity='foo', number='foo')
        self.assertIn("could not convert string to float", six.text_type(ex))

    def test_init_failed_min_size(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterResizeRequest,
                               identity='foo', min_size=-1)
        self.assertEqual("The value for the min_size field must be greater "
                         "than or equal to 0.",
                         six.text_type(ex))

    def test_init_failed_max_size(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterResizeRequest,
                               identity='foo', max_size=-2)
        self.assertEqual("The value for the max_size field must be greater "
                         "than or equal to -1.",
                         six.text_type(ex))

    def test_init_failed_min_step(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterResizeRequest,
                               identity='foo', min_step=-3)
        self.assertEqual("Value must be >= 0 for field 'min_step'.",
                         six.text_type(ex))

    def test_init_failed_strict(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterResizeRequest,
                               identity='foo', strict='fake')
        self.assertIn("Unrecognized value 'fake'", six.text_type(ex))


class TestClusterScaleIn(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterScaleInRequest(identity='foo', count=5)

        self.assertEqual('foo', sot.identity)
        self.assertEqual(5, sot.count)

    def test_init_failed(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterScaleInRequest,
                               identity='foo', count=-1)
        self.assertEqual("Value must be >= 0 for field 'count'.",
                         six.text_type(ex))


class TestClusterScaleOut(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterScaleOutRequest(identity='foo', count=5)

        self.assertEqual('foo', sot.identity)
        self.assertEqual(5, sot.count)

    def test_init_failed(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterScaleOutRequest,
                               identity='foo', count=-1)
        self.assertEqual("Value must be >= 0 for field 'count'.",
                         six.text_type(ex))


class TestClusterAttachPolicy(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterAttachPolicyRequest(identity='foo',
                                                  policy_id='bar')

        self.assertEqual('foo', sot.identity)
        self.assertEqual('bar', sot.policy_id)
        self.assertFalse(sot.obj_attr_is_set('enabled'))

        sot.obj_set_defaults()
        self.assertTrue(sot.obj_attr_is_set('enabled'))
        self.assertTrue(sot.enabled)

    def test_init_failed(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterAttachPolicyRequest,
                               identity='foo', enabled='Bogus')

        self.assertIn("Unrecognized value 'Bogus'", six.text_type(ex))


class TestClusterUpdatePolicy(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterUpdatePolicyRequest(identity='foo',
                                                  policy_id='bar')

        self.assertEqual('foo', sot.identity)
        self.assertEqual('bar', sot.policy_id)
        self.assertFalse(sot.obj_attr_is_set('enabled'))

        sot.obj_set_defaults()
        self.assertTrue(sot.obj_attr_is_set('enabled'))
        self.assertTrue(sot.enabled)

    def test_init_failed(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterUpdatePolicyRequest,
                               identity='foo', enabled='Bogus')

        self.assertIn("Unrecognized value 'Bogus'", six.text_type(ex))


class TestClusterDetachPolicy(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterDetachPolicyRequest(identity='foo',
                                                  policy_id='bar')
        self.assertEqual('foo', sot.identity)
        self.assertEqual('bar', sot.policy_id)


class TestClusterCheck(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterCheckRequest(identity='cluster',
                                           params={'foo': 'bar'})
        self.assertEqual('cluster', sot.identity)
        self.assertEqual({'foo': 'bar'}, sot.params)

    def test_init_partial(self):
        sot = clusters.ClusterCheckRequest(identity='cluster')
        self.assertEqual('cluster', sot.identity)
        self.assertFalse(sot.obj_attr_is_set('params'))


class TestClusterRecover(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterRecoverRequest(identity='cluster',
                                             params={'foo': 'bar'})
        self.assertEqual('cluster', sot.identity)
        self.assertEqual({'foo': 'bar'}, sot.params)

    def test_init_partial(self):
        sot = clusters.ClusterRecoverRequest(identity='cluster')
        self.assertEqual('cluster', sot.identity)
        self.assertFalse(sot.obj_attr_is_set('params'))


class TestClusterReplaceNodes(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterReplaceNodesRequest(
            identity='foo', nodes={'old1': 'new1', 'old2': 'new2'})

        self.assertEqual('foo', sot.identity)
        self.assertEqual({'old1': 'new1', 'old2': 'new2'}, sot.nodes)

    def test_init_missing_value(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterReplaceNodesRequest,
                               identity='foo',
                               nodes={'old1': None, 'old2': 'new2'})

        self.assertEqual("Field `nodes[old1]' cannot be None",
                         six.text_type(ex))

    def test_init_duplicated_nodes(self):
        ex = self.assertRaises(ValueError,
                               clusters.ClusterReplaceNodesRequest,
                               identity='foo',
                               nodes={'old1': 'new2', 'old2': 'new2'})

        self.assertEqual("Map contains duplicated values",
                         six.text_type(ex))


class TestClusterCollect(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterCollectRequest(identity='foo',
                                             path='path/to/attr')

        self.assertEqual('foo', sot.identity)
        self.assertEqual('path/to/attr', sot.path)


class TestClusterOperation(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterOperationRequest(
            identity='foo', filters={'role': 'slave'},
            operation='dance', params={'style': 'tango'})

        self.assertEqual('foo', sot.identity)
        self.assertEqual('dance', sot.operation)
        self.assertEqual({'role': 'slave'}, sot.filters)
        self.assertEqual({'style': 'tango'}, sot.params)

    def test_init_minimal(self):
        sot = clusters.ClusterOperationRequest(identity='foo',
                                               operation='dance')

        self.assertEqual('foo', sot.identity)
        self.assertEqual('dance', sot.operation)
        self.assertFalse(sot.obj_attr_is_set('filters'))
        self.assertFalse(sot.obj_attr_is_set('params'))
        sot.obj_set_defaults()
        self.assertEqual({}, sot.filters)
        self.assertEqual({}, sot.params)


class TestClusterDelete(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterDeleteRequest(identity='foo')
        self.assertEqual('foo', sot.identity)


class TestClusterCompleteLifecycle(test_base.SenlinTestCase):

    def test_init(self):
        sot = clusters.ClusterCompleteLifecycleRequest(
            identity='foo', lifecycle_action_token='abc')

        self.assertEqual('foo', sot.identity)
        self.assertEqual('abc', sot.lifecycle_action_token)
