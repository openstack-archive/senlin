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


from senlin.api.openstack import v1 as api_v1
from senlin.tests.unit.common import base


class RoutesTest(base.SenlinTestCase):

    def assertRoute(self, mapper, path, method, action, controller,
                    params=None):
        params = params or {}
        route = mapper.match(path, {'REQUEST_METHOD': method})
        self.assertIsNotNone(route)
        self.assertEqual(action, route['action'])
        self.assertEqual(
            controller, route['controller'].controller.__class__.__name__)
        del(route['action'])
        del(route['controller'])
        self.assertEqual(params, route)

    def setUp(self):
        super(RoutesTest, self).setUp()
        self.m = api_v1.API({}).map

    def test_profile_types_handling(self):
        self.assertRoute(
            self.m,
            '/aaaa/profile_types',
            'GET',
            'index',
            'ProfileTypeController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/profile_types/test_type',
            'GET',
            'schema',
            'ProfileTypeController',
            {
                'tenant_id': 'aaaa',
                'type_name': 'test_type'
            })

    def test_profile_handling(self):
        self.assertRoute(
            self.m,
            '/aaaa/profiles',
            'GET',
            'index',
            'ProfileController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/profiles',
            'POST',
            'create',
            'ProfileController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/profiles/bbbb',
            'GET',
            'get',
            'ProfileController',
            {
                'tenant_id': 'aaaa',
                'profile_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/profiles/bbbb',
            'PATCH',
            'update',
            'ProfileController',
            {
                'tenant_id': 'aaaa',
                'profile_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/profiles/bbbb',
            'DELETE',
            'delete',
            'ProfileController',
            {
                'tenant_id': 'aaaa',
                'profile_id': 'bbbb'
            })

    def test_policy_types_handling(self):
        self.assertRoute(
            self.m,
            '/aaaa/policy_types',
            'GET',
            'index',
            'PolicyTypeController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/policy_types/test_type',
            'GET',
            'schema',
            'PolicyTypeController',
            {
                'tenant_id': 'aaaa',
                'type_name': 'test_type'
            })

    def test_policy_handling(self):
        self.assertRoute(
            self.m,
            '/aaaa/policies',
            'GET',
            'index',
            'PolicyController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/policies',
            'POST',
            'create',
            'PolicyController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/policies/bbbb',
            'GET',
            'get',
            'PolicyController',
            {
                'tenant_id': 'aaaa',
                'policy_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/policies/bbbb',
            'PATCH',
            'update',
            'PolicyController',
            {
                'tenant_id': 'aaaa',
                'policy_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/policies/bbbb',
            'DELETE',
            'delete',
            'PolicyController',
            {
                'tenant_id': 'aaaa',
                'policy_id': 'bbbb'
            })

    def test_cluster_collection(self):
        self.assertRoute(
            self.m,
            '/aaaa/clusters',
            'GET',
            'index',
            'ClusterController',
            {
                'tenant_id': 'aaaa'
            })

        self.assertRoute(
            self.m,
            '/aaaa/clusters',
            'POST',
            'create',
            'ClusterController',
            {
                'tenant_id': 'aaaa'
            })

        self.assertRoute(
            self.m,
            '/aaaa/clusters/bbbb',
            'GET',
            'get',
            'ClusterController',
            {
                'tenant_id': 'aaaa',
                'cluster_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/clusters/bbbb',
            'PATCH',
            'update',
            'ClusterController',
            {
                'tenant_id': 'aaaa',
                'cluster_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/clusters/bbbb/action',
            'PUT',
            'action',
            'ClusterController',
            {
                'tenant_id': 'aaaa',
                'cluster_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/aaaa/clusters/bbbb',
            'DELETE',
            'delete',
            'ClusterController',
            {
                'tenant_id': 'aaaa',
                'cluster_id': 'bbbb'
            })

    def test_node_collection(self):
        self.assertRoute(
            self.m,
            '/aaaa/nodes',
            'GET',
            'index',
            'NodeController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/nodes',
            'POST',
            'create',
            'NodeController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/nodes/bbbb',
            'GET',
            'get',
            'NodeController',
            {
                'tenant_id': 'aaaa',
                'node_id': 'bbbb',
            })

        self.assertRoute(
            self.m,
            '/aaaa/nodes/bbbb',
            'PATCH',
            'update',
            'NodeController',
            {
                'tenant_id': 'aaaa',
                'node_id': 'bbbb',
            })

        self.assertRoute(
            self.m,
            '/aaaa/nodes/bbbb/action',
            'PUT',
            'action',
            'NodeController',
            {
                'tenant_id': 'aaaa',
                'node_id': 'bbbb',
            })

        self.assertRoute(
            self.m,
            '/aaaa/nodes/bbbb',
            'DELETE',
            'delete',
            'NodeController',
            {
                'tenant_id': 'aaaa',
                'node_id': 'bbbb',
            })

    def test_cluster_policy(self):
        self.assertRoute(
            self.m,
            '/aaaa/clusters/bbbb/policies',
            'GET',
            'index',
            'ClusterPolicyController',
            {
                'tenant_id': 'aaaa',
                'cluster_id': 'bbbb',
            })

        self.assertRoute(
            self.m,
            '/aaaa/clusters/bbbb/policies/cccc',
            'GET',
            'get',
            'ClusterPolicyController',
            {
                'tenant_id': 'aaaa',
                'cluster_id': 'bbbb',
                'policy_id': 'cccc'
            })

    def test_action_collection(self):
        self.assertRoute(
            self.m,
            '/aaaa/actions',
            'GET',
            'index',
            'ActionController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/actions',
            'POST',
            'create',
            'ActionController',
            {
                'tenant_id': 'aaaa',
            })

        self.assertRoute(
            self.m,
            '/aaaa/actions/bbbb',
            'GET',
            'get',
            'ActionController',
            {
                'tenant_id': 'aaaa',
                'action_id': 'bbbb'
            })

    def test_build_info(self):
        self.assertRoute(
            self.m,
            '/aaaa/build_info',
            'GET',
            'build_info',
            'BuildInfoController',
            {
                'tenant_id': 'aaaa',
            }
        )
