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
from tempest.lib import exceptions

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestClusterActionDelNodes(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionDelNodes, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.node_id = utils.create_a_node(self, profile_id,
                                           cluster_id=self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('ab4e0738-98f9-4521-a4a9-81ed151b4c71')
    def test_cluster_action_del_nodes(self):
        params = {
            "del_nodes": {
                "nodes": [
                    self.node_id
                ]
            }
        }
        # Trigger cluster action
        res = self.client.trigger_action('clusters', self.cluster_id,
                                         params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestClusterDelNodesNegativeInvalidNodesParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('89af1e6f-17b4-4c6f-ae5f-91a2da784c05')
    def test_cluster_del_nodes_missing_nodes_params(self):
        params = {
            'del_nodes': {
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('c15c387c-3c3c-4005-8818-8fc0cdbfe679')
    def test_cluster_del_nodes_params_not_list(self):
        params = {
            'del_nodes': {
                'nodes': 'node_id'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('662c548d-a89a-40e3-a238-72b2193e5dc2')
    def test_cluster_del_nodes_params_empty_list(self):
        params = {
            'del_nodes': {
                'nodes': []
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterDelNodesNegativeNodeNotFound(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterDelNodesNegativeNodeNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('e896948b-44c0-4dfa-9466-407391504833')
    def test_cluster_del_nodes_node_not_found(self):
        params = {
            'del_nodes': {
                'nodes': ['e896948b-44c0-4dfa-9466-407391504833']
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterDelNodesNegativeOrphanNode(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterDelNodesNegativeOrphanNode, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.node_id = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('d7e77bd2-2a80-4995-b2e8-e4e9c58b3de5')
    def test_cluster_del_nodes_orphan_node(self):
        params = {
            'del_nodes': {
                'nodes': [self.node_id]
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterDelNodesNegativeNodeOfOtherCluster(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterDelNodesNegativeNodeOfOtherCluster, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.cluster_id2 = utils.create_a_cluster(self, self.profile_id)
        self.node_id = utils.create_a_node(self, self.profile_id,
                                           cluster_id=self.cluster_id2)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id2)

    @decorators.idempotent_id('e83135af-1d42-4a80-a039-7e78cbc7e3f4')
    def test_cluster_del_nodes_node_of_other_cluster(self):
        params = {
            'del_nodes': {
                'nodes': [self.node_id]
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterDelNodesNegativeSizeCheckFailed(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterDelNodesNegativeSizeCheckFailed, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 desired_capacity=1,
                                                 min_size=1)
        self.cluster = utils.get_a_cluster(self, self.cluster_id)
        self.node_id = self.cluster['nodes'][0]
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('b83bdeac-8d23-46ec-9c50-8c47140982a4')
    def test_cluster_del_nodes_cluster_size_check_failed(self):
        params = {
            'del_nodes': {
                'nodes': [
                    self.node_id
                ]
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterDelNodesNegativeClusterNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('dc8f106a-10b7-47a3-8494-c86035207351')
    def test_cluster_del_nodes_cluster_not_found(self):
        params = {
            'del_nodes': {
                'nodes': ['node_id']
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          'dc8f106a-10b7-47a3-8494-c86035207351', params)
