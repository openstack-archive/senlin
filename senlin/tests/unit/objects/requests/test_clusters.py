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

from senlin.objects.requests import clusters
from senlin.tests.unit.common import base as test_base


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

        sot.obj_set_defaults()

        self.assertTrue(sot.obj_attr_is_set('min_size'))
        self.assertEqual(0, sot.min_size)
        self.assertEqual(-1, sot.max_size)
        self.assertEqual(0, sot.desired_capacity)
        self.assertEqual({}, sot.metadata)

    def test_cluster_create_request_body_full(self):
        body = copy.deepcopy(self.body)
        body['min_size'] = 1
        body['max_size'] = 10
        body['desired_capacity'] = 4
        body['metadata'] = {'foo': 'bar'}
        sot = clusters.ClusterCreateRequestBody(**body)
        self.assertEqual('test-cluster', sot.name)
        self.assertEqual('test-profile', sot.profile_id)
        self.assertEqual(1, sot.min_size)
        self.assertEqual(10, sot.max_size)
        self.assertEqual(4, sot.desired_capacity)
        self.assertEqual({'foo': 'bar'}, sot.metadata)

    def test_cluster_create_request_body_dump(self):
        sot = clusters.ClusterCreateRequestBody(**self.body)
        res = sot.obj_to_primitive()
        self.assertEqual(
            {
                'name': u'test-cluster',
                'profile_id': u'test-profile'
            },
            res['versioned_object.data']
        )
        self.assertEqual('ClusterCreateRequestBody',
                         res['versioned_object.name'])
        self.assertEqual('senlin', res['versioned_object.namespace'])
        self.assertEqual('1.0', res['versioned_object.version'])
        self.assertIn('profile_id', res['versioned_object.changes'])
        self.assertIn('name', res['versioned_object.changes'])

    def test_cluster_create_request(self):
        body = clusters.ClusterCreateRequestBody(**self.body)
        request = {'cluster': body}
        sot = clusters.ClusterCreateRequest(**request)
        self.assertIsInstance(sot.cluster, clusters.ClusterCreateRequestBody)

        self.assertEqual('test-cluster', sot.cluster.name)
        self.assertEqual('test-profile', sot.cluster.profile_id)

        res = sot.obj_to_primitive()
        self.assertEqual(['cluster'], res['versioned_object.changes'])
        self.assertEqual('ClusterCreateRequest', res['versioned_object.name'])
        self.assertEqual('senlin', res['versioned_object.namespace'])
        self.assertEqual('1.0', res['versioned_object.version'])
        data = res['versioned_object.data']['cluster']
        self.assertIn('profile_id', data['versioned_object.changes'])
        self.assertIn('name', data['versioned_object.changes'])
        self.assertEqual('ClusterCreateRequestBody',
                         data['versioned_object.name'])
        self.assertEqual('senlin', data['versioned_object.namespace'])
        self.assertEqual('1.0', data['versioned_object.version'])
        self.assertEqual(
            {'name': u'test-cluster', 'profile_id': u'test-profile'},
            data['versioned_object.data']
        )
