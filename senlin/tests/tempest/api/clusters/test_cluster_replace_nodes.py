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


class TestClusterActionReplaceNodes(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionReplaceNodes, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.origin_node = utils.create_a_node(
            self, profile_id, cluster_id=self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.origin_node)
        self.replace_node = utils.create_a_node(self, profile_id)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('a17c2bff-eab7-4d02-a49f-9388eb53aa14')
    def test_cluster_action_replace(self):
        params = {
            "replace_nodes": {
                'nodes': {
                    self.origin_node: self.replace_node
                }
            }
        }
        # Trigger cluster action
        res = self.client.cluster_replace_nodes('clusters', self.cluster_id,
                                                params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('action', res['location'])
        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestClusterReplaceNodesNegativeInvalidParams(base.BaseSenlinAPITest):

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('fbfb0819-6a15-4926-a21f-44fda6960bed')
    def test_cluster_replace_nodes_params_not_map(self):
        params = {
            'replace_nodes': {
                'nodes': []
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("The data provided is not a map",
                         str(message))

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('600baf2f-e74f-467d-9883-3dcf1c357b57')
    def test_cluster_replace_nodes_params_empty_map(self):
        params = {
            'replace_nodes': {
                'nodes': {}
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("The data provided is not a map",
                         str(message))

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('3e227f8f-7da3-4dc1-b647-68ed8fbdd111')
    def test_cluster_replace_nodes_missing_new_node(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    'old_node': None
                }
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Field `nodes[old_node]' cannot be None",
                         str(message))

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('82ebbd5a-47fc-4d32-be3c-7bf3262dd574')
    def test_cluster_replace_nodes_duplicated_node(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    'old_node1': 'new_node',
                    'old_node2': 'new_node'
                }
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Map contains duplicated values",
                         str(message))


class TestClusterReplaceNodesNegativeOldNotFound(base.BaseSenlinAPITest):
    def setUp(self):
        super(TestClusterReplaceNodesNegativeOldNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.new_node = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.new_node)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('911d6e85-220f-4208-9a0b-b91e83c5e787')
    def test_cluster_replace_nodes_old_node_not_found(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    'old_node': self.new_node
                }
            }
        }

        # Verify not found badrequest is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Original nodes not found: [u'old_node'].",
                         str(message))


class TestClusterReplaceNodesNegativeNewNotFound(base.BaseSenlinAPITest):
    def setUp(self):
        super(TestClusterReplaceNodesNegativeNewNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.old_node = utils.create_a_node(self, self.profile_id,
                                            cluster_id=self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.old_node)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('1282c521-c479-42f3-b375-8d6d62b1d5dc')
    def test_cluster_replace_nodes_old_node_not_found(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    self.old_node: 'new_node'
                }
            }
        }

        # Verify badrequest exception is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Replacement nodes not found: [u'new_node'].",
                         str(message))


class TestClusterReplaceNodesNegativeNewNotOrphan(base.BaseSenlinAPITest):
    def setUp(self):
        super(TestClusterReplaceNodesNegativeNewNotOrphan, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.old_node = utils.create_a_node(self, self.profile_id,
                                            cluster_id=self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.old_node)

        self.cluster_id2 = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id2)
        self.new_node = utils.create_a_node(self, self.profile_id,
                                            self.cluster_id2)
        self.addCleanup(utils.delete_a_node, self, self.new_node)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('e001ba28-f7ad-4af5-a281-5652ca040c65')
    def test_cluster_replace_nodes_new_node_not_orphan(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    self.old_node: self.new_node
                }
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Nodes [u'%s'] already member of a cluster." % self.new_node,
            str(message))


class TestClusterReplaceNodeNegativeProfileUnmatch(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterReplaceNodeNegativeProfileUnmatch, self).setUp()
        self.profile_id = utils.create_a_profile(
            self, spec=constants.spec_nova_server)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.old_node = utils.create_a_node(self, self.profile_id,
                                            self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.old_node)

        self.profile_id2 = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id2)
        self.new_node = utils.create_a_node(self, self.profile_id2)
        self.addCleanup(utils.delete_a_node, self, self.new_node)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('d1cb2068-b23c-4023-ad25-271f8e5b1bfa')
    def test_cluster_replace_nodes_profile_type_unmatch(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    self.old_node: self.new_node
                }
            }
        }

        # Verify badrequest exception is raised
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Profile type of nodes [u'%s'] do not match that of the "
            "cluster." % self.new_node, str(message))


class TestClusterReplaceNodeNegativeOldOrphan(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterReplaceNodeNegativeOldOrphan, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

        self.old_node = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.old_node)
        self.new_node = utils.create_a_node(self, self.profile_id)
        self.addCleanup(utils.delete_a_node, self, self.new_node)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('ca0afe22-e758-477c-8ca5-cd1b686747dc')
    def test_cluster_replace_nodes_old_node_orphan(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    self.old_node: self.new_node
                }
            }
        }

        # Versify badrequest exeception is raised
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_replace_nodes, 'clusters',
                               self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified nodes [u'%s'] to be replaced are not members "
            "of the cluster %s." % (self.old_node, self.cluster_id),
            str(message))


class TestClusterReplaceNodeNegativeClusterNotFound(base.BaseSenlinAPITest):

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('086c0657-f7a1-4722-a585-ac281725bcfc')
    def test_cluster_replace_nodes_cluster_not_found(self):
        params = {
            'replace_nodes': {
                'nodes': {
                    'old_node': 'new_node'
                }
            }
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.cluster_replace_nodes, 'clusters',
                               'db0faadf-9cd2-457f-b434-4891b77938ab',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster 'db0faadf-9cd2-457f-b434-4891b77938ab' could "
            "not be found.", str(message))
