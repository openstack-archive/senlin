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

from senlin.common.i18n import _
from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestClusterMembership(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestClusterMembership, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestClusterMembership, self).tearDown()

    def test_cluster_node_add_del(self):
        # Create cluster
        desired_capacity = 1
        min_size = 1
        max_size = 3
        cluster_name = test_utils.random_name('cluster')
        cluster = test_api.create_cluster(self.client, cluster_name,
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Create two orphan nodes
        node1 = test_api.create_node(self.client,
                                     test_utils.random_name('node1'),
                                     self.profile['id'])
        node2 = test_api.create_node(self.client,
                                     test_utils.random_name('node2'),
                                     self.profile['id'])

        node1 = test_utils.wait_for_status(test_api.get_node, self.client,
                                           node1['id'], 'ACTIVE')
        node2 = test_utils.wait_for_status(test_api.get_node, self.client,
                                           node2['id'], 'ACTIVE')

        self.assertEqual('', node1['cluster_id'])
        self.assertEqual(-1, node1['index'])
        self.assertEqual('', node2['cluster_id'])
        self.assertEqual(-1, node2['index'])

        # Add orphan nodes to cluster
        params = {
            'nodes': [node1['id'], node2['id']],
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'add_nodes', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual(3, cluster['desired_capacity'])
        self.assertEqual(3, len(cluster['nodes']))
        self.assertIn(node1['id'], cluster['nodes'])
        self.assertIn(node2['id'], cluster['nodes'])

        node1 = test_api.get_node(self.client, node1['id'])
        node2 = test_api.get_node(self.client, node2['id'])
        self.assertEqual(cluster['id'], node1['cluster_id'])
        self.assertEqual(cluster['id'], node2['cluster_id'])
        self.assertEqual([2, 3], sorted([node1['index'], node2['index']]))

        # Create one more orphan node and add it to cluster
        node3 = test_api.create_node(self.client,
                                     test_utils.random_name('node1'),
                                     self.profile['id'])
        node3 = test_utils.wait_for_status(test_api.get_node, self.client,
                                           node3['id'], 'ACTIVE')
        params = {
            'nodes': [node3['id']],
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'add_nodes',
                                      params)
        reason = _("The target capacity (4) is greater than the cluster's "
                   "max_size (3).")
        self.assertIn(reason, res)

        # Remove two nodes from cluster
        params = {
            'nodes': [node1['id'], node2['id']],
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'del_nodes', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))
        self.assertNotIn(node1['id'], cluster['nodes'])
        self.assertNotIn(node2['id'], cluster['nodes'])

        node1 = test_api.get_node(self.client, node1['id'])
        node2 = test_api.get_node(self.client, node2['id'])
        self.assertEqual('', node1['cluster_id'])
        self.assertEqual('', node2['cluster_id'])
        self.assertEqual(-1, node1['index'])
        self.assertEqual(-1, node2['index'])

        # Try to delete the last node from cluster
        last_node_id = cluster['nodes'][0]
        params = {
            'nodes': [last_node_id]
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'del_nodes',
                                      params)
        reason = _("The target capacity (0) is less than the cluster's "
                   "min_size (1).")
        self.assertIn(reason, res)

        # Delete orphan nodes
        test_api.delete_node(self.client, node1['id'])
        test_api.delete_node(self.client, node2['id'])
        test_api.delete_node(self.client, node3['id'])
        test_utils.wait_for_delete(test_api.get_node, self.client,
                                   node1['id'])
        test_utils.wait_for_delete(test_api.get_node, self.client,
                                   node2['id'])
        test_utils.wait_for_delete(test_api.get_node, self.client,
                                   node3['id'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                   cluster['id'])
