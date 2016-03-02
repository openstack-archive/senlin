# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestClusterBasic(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestClusterBasic, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestClusterBasic, self).tearDown()

    def test_cluster_create_delete(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster_name = test_utils.random_name('cluster')
        cluster = test_api.create_cluster(self.client, cluster_name,
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)

        # Wait and verify cluster creation result
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')
        self.assertEqual(cluster_name, cluster['name'])
        self.assertEqual(desired_capacity, cluster['desired_capacity'])
        self.assertEqual(min_size, cluster['min_size'])
        self.assertEqual(max_size, cluster['max_size'])
        self.assertEqual(desired_capacity, len(cluster['nodes']))

        # Create cluster2
        desired_capacity = 1
        min_size = 1
        max_size = 3
        cluster2_name = test_utils.random_name('cluster')
        cluster2 = test_api.create_cluster(self.client, cluster2_name,
                                           self.profile['id'],
                                           desired_capacity,
                                           min_size, max_size)

        # List clusters
        clusters = test_api.list_clusters(self.client)
        clusters_id = [c['id'] for c in clusters]
        self.assertIn(cluster['id'], clusters_id)
        self.assertIn(cluster2['id'], clusters_id)

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_api.delete_cluster(self.client, cluster2['id'])
        test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                   cluster['id'])
        test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                   cluster2['id'])


class TestClusterUpdate(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestClusterUpdate, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestClusterUpdate, self).tearDown()

    def test_cluster_update_basic_properties(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster_name = test_utils.random_name('cluster')
        cluster = test_api.create_cluster(self.client, cluster_name,
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size,
                                          metadata={'k1': 'v1'},
                                          timeout=120)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')
        self.assertEqual(cluster_name, cluster['name'])
        self.assertEqual({'k1': 'v1'}, cluster['metadata'])
        self.assertEqual(120, cluster['timeout'])

        # Update basic properties of cluster
        action_id = test_api.update_cluster(self.client, cluster['id'],
                                            name='cluster_new_name',
                                            metadata={'k2': 'v2'},
                                            timeout=240)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify update result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('cluster_new_name', cluster['name'])
        self.assertEqual({'k2': 'v2'}, cluster['metadata'])
        self.assertEqual(240, cluster['timeout'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                   cluster['id'])

    def test_cluster_update_profile(self):
        spec_nova_server = copy.deepcopy(test_utils.spec_nova_server)
        spec_nova_server['properties']['flavor'] = 'new_flavor'
        spec_nova_server['properties']['image'] = 'new_image'
        new_profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            spec_nova_server)

        # Create cluster with original profile
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster_name = test_utils.random_name('cluster')
        cluster = test_api.create_cluster(self.client, cluster_name,
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Update cluster with new profile
        action_id = test_api.update_cluster(self.client, cluster['id'],
                                            profile=new_profile['id'])
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify update result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual(new_profile['id'], cluster['profile_id'])
        nodes = cluster['nodes']
        for n in nodes:
            node = test_api.get_node(self.client, n, show_details=True)
            self.assertEqual(new_profile['id'], node['profile_id'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                   cluster['id'])
        # Delete new profile
        test_api.delete_profile(self.client, new_profile['id'])
