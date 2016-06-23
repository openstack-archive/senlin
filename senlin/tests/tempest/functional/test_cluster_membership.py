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
from tempest import test

from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestClusterMembership(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestClusterMembership, self).setUp()
        # Create a profile
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        # Create a cluster
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 desired_capacity=0,
                                                 min_size=0, max_size=3)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        # Create three orphan nodes
        self.node_id1 = utils.create_a_node(self, self.profile_id)
        self.node_id2 = utils.create_a_node(self, self.profile_id)
        self.node_id3 = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id1)
        self.addCleanup(utils.delete_a_node, self, self.node_id2)
        self.addCleanup(utils.delete_a_node, self, self.node_id3)

    @test.attr(type=['functional'])
    @decorators.idempotent_id('137a36d9-b4ee-485d-8bff-51ebb6113e9b')
    def test_cluster_node_add_del(self):
        # Add one node to cluster
        utils.cluster_add_nodes(self, self.cluster_id, [self.node_id1])

        # Verify result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(1, len(cluster['nodes']))
        self.assertIn(self.node_id1, cluster['nodes'])
        node1 = utils.get_a_node(self, self.node_id1)
        self.assertEqual(self.cluster_id, node1['cluster_id'])
        self.assertEqual(1, node1['index'])

        # Add two nodes to cluster
        nodes = [self.node_id2, self.node_id3]
        utils.cluster_add_nodes(self, self.cluster_id, nodes)

        # Verify result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(3, len(cluster['nodes']))
        self.assertIn(self.node_id2, cluster['nodes'])
        self.assertIn(self.node_id3, cluster['nodes'])
        node2 = utils.get_a_node(self, self.node_id2)
        node3 = utils.get_a_node(self, self.node_id3)
        self.assertEqual(self.cluster_id, node2['cluster_id'])
        self.assertEqual(self.cluster_id, node3['cluster_id'])
        self.assertEqual([2, 3], sorted([node2['index'], node3['index']]))

        # Delete one node from cluster
        utils.cluster_del_nodes(self, self.cluster_id, [self.node_id1])

        # Verify result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(2, len(cluster['nodes']))
        self.assertNotIn(self.node_id1, cluster['nodes'])
        node1 = utils.get_a_node(self, self.node_id1)
        self.assertEqual('', node1['cluster_id'])
        self.assertEqual(-1, node1['index'])

        # Delete two nodes from cluster
        nodes = [self.node_id2, self.node_id3]
        utils.cluster_del_nodes(self, self.cluster_id, nodes)

        # Verify result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(0, len(cluster['nodes']))
        node2 = utils.get_a_node(self, self.node_id2)
        node3 = utils.get_a_node(self, self.node_id3)
        self.assertEqual('', node2['cluster_id'])
        self.assertEqual('', node3['cluster_id'])
        self.assertEqual(-1, node2['index'])
        self.assertEqual(-1, node3['index'])
