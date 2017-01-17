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
from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils


class TestClusterActionAddNodes(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionAddNodes, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.node_id = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('db0faadf-9cd2-457f-b434-4891b77938ab')
    def test_cluster_action_add_nodes(self):
        params = {
            "add_nodes": {
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


class TestClusterAddNodesNegativeInvalidNodesParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('912bb24d-73e1-4801-a6de-bdd453cbbdbf')
    def test_cluster_add_nodes_missing_nodes_params(self):
        params = {
            'add_nodes': {
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         str(message))

    @decorators.idempotent_id('6cb029f7-9b72-4f10-a28b-3ed5bd3ed7b0')
    def test_cluster_add_nodes_params_not_list(self):
        params = {
            'add_nodes': {
                'nodes': 'node_id'
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Items for 'nodes' must be unique", str(message))

    @decorators.idempotent_id('b8ae9b5f-967f-48a6-8e31-c77f86ba06aa')
    def test_cluster_add_nodes_params_empty_list(self):
        params = {
            'add_nodes': {
                'nodes': []
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Value for 'nodes' must have at least 1 item(s).",
                         str(message))

    @decorators.idempotent_id('a97f1712-46ba-43c1-abd6-12c209c9d640')
    def test_cluster_add_mult_node_with_same_name(self):
        params = {
            'add_nodes': {
                'nodes': ['id1', 'id1']
            }
        }

        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Items for 'nodes' must be unique",
                         str(message))


class TestClusterAddNodesNegativeNodeNotFound(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterAddNodesNegativeNodeNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('5ddf7e5a-3f67-4f1e-af1e-c5a7da319dc0')
    def test_cluster_add_nodes_node_not_found(self):
        params = {
            'add_nodes': {
                'nodes': ['5ddf7e5a-3f67-4f1e-af1e-c5a7da319dc0']
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Nodes not found: [u'5ddf7e5a-3f67-4f1e-af1e-c5a7da319dc0'].",
            str(message))


class TestClusterAddNodesNegativeNodeNotOrphan(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterAddNodesNegativeNodeNotOrphan, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

        self.cluster_id2 = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id2)
        self.node_id = utils.create_a_node(self, self.profile_id,
                                           cluster_id=self.cluster_id2)

    @decorators.idempotent_id('08e1271c-025e-4670-a20e-4a96fa179dca')
    def test_cluster_add_nodes_node_not_orphan(self):
        params = {
            'add_nodes': {
                'nodes': [self.node_id]
            }
        }

        # Verify conflict exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Nodes ['%s'] already owned by some cluster." % self.node_id,
            str(message))


class TestClusterAddNodesNegativeProfileTypeUnmatch(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterAddNodesNegativeProfileTypeUnmatch, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

        self.profile_id2 = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id2)
        self.node_id = utils.create_a_node(self, self.profile_id2)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('7a27c697-6d29-46f0-8b2a-3a7282c15b33')
    def test_cluster_add_nodes_profile_type_unmatch(self):
        params = {
            'add_nodes': {
                'nodes': [
                    self.node_id
                ]
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Profile type of nodes ['%s'] does not match that of the "
            "cluster." % self.node_id, str(message))


class TestClusterAddNodesNegativeSizeCheckFailed(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterAddNodesNegativeSizeCheckFailed, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 desired_capacity=1,
                                                 max_size=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.node_id = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('3b485352-53e3-481d-b471-9a042c76d758')
    def test_cluster_add_nodes_cluster_size_check_failed(self):
        params = {
            'add_nodes': {
                'nodes': [
                    self.node_id
                ]
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The target capacity (2) is greater than the cluster's "
            "max_size (1).", str(message))


class TestClusterAddNodesNegativeClusterNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('22f10d36-c29a-4cde-a975-af262a5775a1')
    def test_cluster_add_nodes_cluster_not_found(self):
        params = {
            'add_nodes': {
                'nodes': ['node_id']
            }
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action, 'clusters',
                               'db0faadf-9cd2-457f-b434-4891b77938ab', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster 'db0faadf-9cd2-457f-b434-4891b77938ab' "
            "could not be found.", str(message))
