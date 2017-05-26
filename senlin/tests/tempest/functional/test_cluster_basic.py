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

from tempest.lib import decorators

from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestClusterCreateListDelete(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestClusterCreateListDelete, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('d2001e89-e7e7-4ceb-8497-2255becc5d7f')
    def test_cluster_create_list_delete(self):
        # Create a cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        metadata = {'k1': 'v1'}
        timeout = 120
        cluster_id1 = utils.create_a_cluster(
            self, self.profile_id, desired_capacity, min_size, max_size,
            timeout, metadata)

        # Verify creation result
        cluster1 = utils.get_a_cluster(self, cluster_id1)
        self.assertIsNotNone(cluster1)
        self.assertEqual(desired_capacity, cluster1['desired_capacity'])
        self.assertEqual(desired_capacity, len(cluster1['nodes']))
        self.assertEqual(min_size, cluster1['min_size'])
        self.assertEqual(max_size, cluster1['max_size'])
        self.assertEqual(metadata, cluster1['metadata'])
        self.assertEqual(timeout, cluster1['timeout'])

        # Create another cluster
        cluster_id2 = utils.create_a_cluster(self, self.profile_id)

        # List clusters
        clusters = utils.list_clusters(self)
        self.assertIsNotNone(clusters)
        cluster_ids = [c['id'] for c in clusters]
        self.assertIn(cluster_id1, cluster_ids)
        self.assertIn(cluster_id2, cluster_ids)

        # Delete cluster
        utils.delete_a_cluster(self, cluster_id1)
        utils.delete_a_cluster(self, cluster_id2)


class TestClusterUpdate(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestClusterUpdate, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.profile_id_new = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id_new)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 desired_capacity=3)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('308ee213-b379-4f2d-b193-0ea44b0de622')
    def test_cluster_update_basic_properties(self):
        name = 'new-name'
        metadata = {'k1': 'v1'}
        timeout = 360

        # Update cluster
        utils.update_a_cluster(self, self.cluster_id, name=name,
                               metadata=metadata, timeout=timeout)

        # Verify update result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(name, cluster['name'])
        self.assertEqual(metadata, cluster['metadata'])
        self.assertEqual(timeout, cluster['timeout'])

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('bf655d2b-11d4-47b7-b10c-8dfb8a4538a5')
    def test_cluster_update_profile(self):

        # Update cluster
        utils.update_a_cluster(self, self.cluster_id,
                               profile_id=self.profile_id_new)

        # Verify update result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(self.profile_id_new, cluster['profile_id'])
        nodes = cluster['nodes']
        for n in nodes:
            node = utils.get_a_node(self, n)
            self.assertEqual(self.profile_id_new, node['profile_id'])
