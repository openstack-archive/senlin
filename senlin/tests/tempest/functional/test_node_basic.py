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

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest import test

from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestNodeCreateShowListDelete(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestNodeCreateShowListDelete, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['functional'])
    @decorators.idempotent_id('eff142d3-e7fd-4f2a-aaff-46c210d9fa0d')
    def test_node_create_show_list_delete(self):
        # Create an orphan node
        name = data_utils.rand_name('node')
        metadata = {'k1': 'v1'}
        role = 'individual'
        node_id1 = utils.create_a_node(
            self, self.profile_id, metadata=metadata, role=role, name=name)

        # Verify creation result
        node1 = utils.get_a_node(self, node_id1)
        self.assertIsNotNone(node1)
        self.assertEqual(name, node1['name'])
        self.assertEqual(metadata, node1['metadata'])
        self.assertEqual(role, node1['role'])
        self.assertEqual('', node1['cluster_id'])
        self.assertNotIn('details', node1)

        # Get node with detail
        node1 = utils.get_a_node(self, node_id1, show_details=True)
        self.assertIn('details', node1)
        self.assertIsNotNone(node1['details'])

        # Create second node with target cluster
        name = data_utils.rand_name('node')
        node_id2 = utils.create_a_node(
            self, self.profile_id, cluster_id=self.cluster_id,
            metadata=metadata, role=role, name=name)

        # Verify creation result
        node2 = utils.get_a_node(self, node_id2)
        self.assertIsNotNone(node2)
        self.assertEqual(self.cluster_id, node2['cluster_id'])
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertIn(node_id2, cluster['nodes'])

        # List nodes
        nodes = utils.list_nodes(self)
        self.assertIsNotNone(nodes)
        self.assertEqual(2, len(nodes))
        node_ids = [n['id'] for n in nodes]
        self.assertIn(node_id1, node_ids)
        self.assertIn(node_id2, node_ids)

        # Delete nodes
        utils.delete_a_node(self, node_id1)
        utils.delete_a_node(self, node_id2)


class TestNodeUpdate(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestNodeUpdate, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.profile_id_new = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id_new)
        self.node_id = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @test.attr(type=['functional'])
    @decorators.idempotent_id('d373fb1d-33a1-434f-a850-fb78eff15d18')
    def test_node_update_basic_properties(self):
        name = 'new-name'
        role = 'new-role'
        metadata = {'k2': 'v2'}

        # Update node
        utils.update_a_node(self, self.node_id, name=name, metadata=metadata,
                            role=role)

        # Verify update result
        node = utils.get_a_node(self, self.node_id)
        self.assertEqual(name, node['name'])
        self.assertEqual(metadata, node['metadata'])
        self.assertEqual(role, node['role'])

    @test.attr(type=['functional'])
    @decorators.idempotent_id('361e051d-b55b-4943-8a01-462f6fc5be43')
    def test_node_update_profile(self):

        # Update node
        utils.update_a_node(self, self.node_id, profile_id=self.profile_id_new)

        # Verify update result
        node = utils.get_a_node(self, self.node_id)
        self.assertEqual(self.profile_id_new, node['profile_id'])
