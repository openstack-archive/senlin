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

from oslo_utils import reflection

from senlin.api.openstack.v1 import router as api_v1
from senlin.tests.unit.common import base


class RoutesTest(base.SenlinTestCase):

    def assertRoute(self, mapper, path, method, action, controller,
                    params=None):
        params = params or {}
        route = mapper.match(path, {'REQUEST_METHOD': method})
        self.assertIsNotNone(route)
        self.assertEqual(action, route['action'])
        obj = route['controller'].controller
        obj_name = reflection.get_class_name(obj, fully_qualified=False)
        self.assertEqual(controller, obj_name)
        del(route['action'])
        del(route['controller'])
        self.assertEqual(params, route)

    def setUp(self):
        super(RoutesTest, self).setUp()
        self.m = api_v1.API({}).map

    def test_version_handling(self):
        self.assertRoute(
            self.m,
            '/',
            'GET',
            'version',
            'VersionController')

    def test_profile_types_handling(self):
        self.assertRoute(
            self.m,
            '/profile-types',
            'GET',
            'index',
            'ProfileTypeController')

        self.assertRoute(
            self.m,
            '/profile-types/test_type',
            'GET',
            'get',
            'ProfileTypeController',
            {
                'type_name': 'test_type'
            })

    def test_profile_handling(self):
        self.assertRoute(
            self.m,
            '/profiles',
            'GET',
            'index',
            'ProfileController')

        self.assertRoute(
            self.m,
            '/profiles',
            'POST',
            'create',
            'ProfileController',
            {
                'success': '201',
            })

        self.assertRoute(
            self.m,
            '/profiles/bbbb',
            'GET',
            'get',
            'ProfileController',
            {
                'profile_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/profiles/bbbb',
            'PATCH',
            'update',
            'ProfileController',
            {
                'profile_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/profiles/bbbb',
            'DELETE',
            'delete',
            'ProfileController',
            {
                'profile_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/profiles/validate',
            'POST',
            'validate',
            'ProfileController')

    def test_policy_types_handling(self):
        self.assertRoute(
            self.m,
            '/policy-types',
            'GET',
            'index',
            'PolicyTypeController')

        self.assertRoute(
            self.m,
            '/policy-types/test_type',
            'GET',
            'get',
            'PolicyTypeController',
            {
                'type_name': 'test_type'
            })

    def test_policy_handling(self):
        self.assertRoute(
            self.m,
            '/policies',
            'GET',
            'index',
            'PolicyController')

        self.assertRoute(
            self.m,
            '/policies',
            'POST',
            'create',
            'PolicyController',
            {
                'success': '201',
            })

        self.assertRoute(
            self.m,
            '/policies/bbbb',
            'GET',
            'get',
            'PolicyController',
            {
                'policy_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/policies/bbbb',
            'PATCH',
            'update',
            'PolicyController',
            {
                'policy_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/policies/bbbb',
            'DELETE',
            'delete',
            'PolicyController',
            {
                'policy_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/policies/validate',
            'POST',
            'validate',
            'PolicyController')

    def test_cluster_collection(self):
        self.assertRoute(
            self.m,
            '/clusters',
            'GET',
            'index',
            'ClusterController')

        self.assertRoute(
            self.m,
            '/clusters',
            'POST',
            'create',
            'ClusterController',
            {
                'success': '202',
            })

        self.assertRoute(
            self.m,
            '/clusters/bbbb',
            'GET',
            'get',
            'ClusterController',
            {
                'cluster_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/clusters/bbbb',
            'PATCH',
            'update',
            'ClusterController',
            {
                'cluster_id': 'bbbb',
                'success': '202',
            })

        self.assertRoute(
            self.m,
            '/clusters/bbbb/actions',
            'POST',
            'action',
            'ClusterController',
            {
                'cluster_id': 'bbbb',
                'success': '202',
            })

        self.assertRoute(
            self.m,
            '/clusters/bbbb',
            'DELETE',
            'delete',
            'ClusterController',
            {
                'cluster_id': 'bbbb',
                'success': '202',
            })

    def test_node_collection(self):
        self.assertRoute(
            self.m,
            '/nodes',
            'GET',
            'index',
            'NodeController')

        self.assertRoute(
            self.m,
            '/nodes',
            'POST',
            'create',
            'NodeController',
            {
                'success': '202'
            })

        self.assertRoute(
            self.m,
            '/nodes/adopt',
            'POST',
            'adopt',
            'NodeController')

        self.assertRoute(
            self.m,
            '/nodes/adopt-preview',
            'POST',
            'adopt_preview',
            'NodeController')

        self.assertRoute(
            self.m,
            '/nodes/bbbb',
            'GET',
            'get',
            'NodeController',
            {
                'node_id': 'bbbb',
            })

        self.assertRoute(
            self.m,
            '/nodes/bbbb',
            'PATCH',
            'update',
            'NodeController',
            {
                'node_id': 'bbbb',
                'success': '202',
            })

        self.assertRoute(
            self.m,
            '/nodes/bbbb/actions',
            'POST',
            'action',
            'NodeController',
            {
                'node_id': 'bbbb',
                'success': '202',
            })

        self.assertRoute(
            self.m,
            '/nodes/bbbb',
            'DELETE',
            'delete',
            'NodeController',
            {
                'node_id': 'bbbb',
                'success': '202',
            })

    def test_cluster_policy(self):
        self.assertRoute(
            self.m,
            '/clusters/bbbb/policies',
            'GET',
            'index',
            'ClusterPolicyController',
            {
                'cluster_id': 'bbbb',
            })

        self.assertRoute(
            self.m,
            '/clusters/bbbb/policies/cccc',
            'GET',
            'get',
            'ClusterPolicyController',
            {
                'cluster_id': 'bbbb',
                'policy_id': 'cccc'
            })

    def test_action_collection(self):
        self.assertRoute(
            self.m,
            '/actions',
            'GET',
            'index',
            'ActionController')

        self.assertRoute(
            self.m,
            '/actions',
            'POST',
            'create',
            'ActionController',
            {
                'success': '201',
            })

        self.assertRoute(
            self.m,
            '/actions/bbbb',
            'GET',
            'get',
            'ActionController',
            {
                'action_id': 'bbbb'
            })

    def test_receiver_collection(self):
        self.assertRoute(
            self.m,
            '/receivers',
            'GET',
            'index',
            'ReceiverController')

        self.assertRoute(
            self.m,
            '/receivers',
            'POST',
            'create',
            'ReceiverController',
            {
                'success': '201',
            })

        self.assertRoute(
            self.m,
            '/receivers/bbbb',
            'GET',
            'get',
            'ReceiverController',
            {
                'receiver_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/receivers/bbbb',
            'DELETE',
            'delete',
            'ReceiverController',
            {
                'receiver_id': 'bbbb'
            })

        self.assertRoute(
            self.m,
            '/receivers/bbbb/notify',
            'POST',
            'notify',
            'ReceiverController',
            {
                'receiver_id': 'bbbb'
            })

    def test_webhook_collection(self):
        self.assertRoute(
            self.m,
            '/webhooks/bbbbb/trigger',
            'POST',
            'trigger',
            'WebhookController',
            {
                'webhook_id': 'bbbbb',
                'success': '202',
            })

    def test_build_info(self):
        self.assertRoute(
            self.m,
            '/build-info',
            'GET',
            'build_info',
            'BuildInfoController')
