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

from senlin.common import consts
from senlin.objects.requests import clusters
from senlin.tests.unit.common import base as test_base

CONF = cfg.CONF
CONF.import_opt('default_action_timeout', 'senlin.common.config')


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
        self.assertFalse(sot.obj_attr_is_set('timeout'))

        sot.obj_set_defaults()

        self.assertTrue(sot.obj_attr_is_set('min_size'))
        self.assertEqual(consts.CLUSTER_DEFAULT_MIN_SIZE, sot.min_size)
        self.assertEqual(consts.CLUSTER_DEFAULT_MAX_SIZE, sot.max_size)
        self.assertEqual(consts.CLUSTER_DEFAULT_MIN_SIZE, sot.desired_capacity)
        self.assertEqual({}, sot.metadata)
        self.assertEqual(CONF.default_action_timeout, sot.timeout)

    def test_cluster_create_request_body_full(self):
        body = copy.deepcopy(self.body)
        body['min_size'] = 1
        body['max_size'] = 10
        body['desired_capacity'] = 4
        body['metadata'] = {'foo': 'bar'}
        body['timeout'] = 121
        sot = clusters.ClusterCreateRequestBody(**body)
        self.assertEqual('test-cluster', sot.name)
        self.assertEqual('test-profile', sot.profile_id)
        self.assertEqual(1, sot.min_size)
        self.assertEqual(10, sot.max_size)
        self.assertEqual(4, sot.desired_capacity)
        self.assertEqual({'foo': 'bar'}, sot.metadata)
        self.assertEqual(121, sot.timeout)

    def test_cluster_create_request_body_dump(self):
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
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertIn('profile_id', res['senlin_object.changes'])
        self.assertIn('name', res['senlin_object.changes'])

    def test_cluster_create_request(self):
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
        self.assertEqual('1.0', data['senlin_object.version'])
        self.assertEqual(
            {'name': u'test-cluster', 'profile_id': u'test-profile'},
            data['senlin_object.data']
        )


class TestClusterList(test_base.SenlinTestCase):

    params = {
        'project_safe': True,
    }

    def test_init(self):
        sot = clusters.ClusterListRequestBody()

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
            'limit': 4,
            'marker': '09013587-c1e9-4c98-9c0c-d357004363e1',
            'sort': 'name:asc',
            'project_safe': False,
        }
        sot = clusters.ClusterListRequestBody(**params)
        self.assertEqual(['name1'], sot.name)
        self.assertEqual(['ACTIVE'], sot.status)
        self.assertEqual(4, sot.limit)
        self.assertEqual('09013587-c1e9-4c98-9c0c-d357004363e1', sot.marker)
        self.assertEqual('name:asc', sot.sort)
        self.assertFalse(sot.project_safe)
