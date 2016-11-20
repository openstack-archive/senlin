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


class TestClusterActionNegativeCommon(base.BaseSenlinAPITest):

    @decorators.idempotent_id('9c972d49-81bd-4448-9afc-b93053aa835d')
    def test_cluster_action_no_action_specified(self):
        # No action is specified
        params = {}

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('997d2e19-7914-4883-9b6a-86e907898d3b')
    def test_cluster_action_multiple_action_specified(self):
        # Multiple actions are specified
        params = {
            'resize': {},
            'check': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('43e142ac-9579-40d9-845a-b8190691b91a')
    def test_cluster_action_unrecognized_action(self):
        # Unrecoginized action is specified
        params = {
            'bogus': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterResizeNegativeInvalidResizeParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('57bc61a2-df38-4bf5-a26a-d23d2cc67ca3')
    def test_cluster_resize_invalid_adj_type(self):
        params = {
            "resize": {
                "adjustment_type": "bogus",
                "max_size": 20,
                "min_size": 5,
                "number": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('cef85ed4-9dd3-4f9f-91fe-4372d9aa8956')
    def test_cluster_resize_missing_adj_type(self):
        params = {
            "resize": {
                "max_size": 20,
                "min_size": 5,
                "number": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('e42dd7e1-aa36-4e46-8b5b-2571d00574c9')
    def test_cluster_resize_missing_adj_number(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 20,
                "min_size": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('7e669b3e-8fbd-4820-a281-7cc4b29c6020')
    def test_cluster_resize_invalid_adj_number(self):
        params = {
            "resize": {
                "adjustment_type": "EXACT_CAPACITY",
                "max_size": 20,
                "min_size": 5,
                "number": -1
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('5a069782-d6d8-4389-a68c-beb32375a39e')
    def test_cluster_resize_min_size_over_max_size(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 10,
                "min_size": 20,
                "number": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterResizeNegativeClusterNotFound(base.BaseSenlinAPITest):
    @decorators.idempotent_id('087ef694-55d2-4616-a58b-1073cacb2bcd')
    def test_cluster_resize_cluster_not_found(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 20,
                "min_size": 5,
                "number": 5
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action,
                          'clusters', '087ef694-55d2-4616-a58b-1073cacb2bcd',
                          params)


class TestClusterResizeNegativeSizeCheckFailed(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterResizeNegativeSizeCheckFailed, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=2, max_size=5,
                                                 desired_capacity=3)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('92e7d3c8-2d38-4766-86c3-41dc14bf89a1')
    def test_cluster_resize_break_upper_limit(self):
        # New desired_capacity will be larger than max_size
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "number": 3,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

    @decorators.idempotent_id('9dcac577-d768-44d1-b119-02d27202ef08')
    def test_cluster_resize_break_lower_limit(self):
        # New desired_capacity will be less than min_size
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "number": -2,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

    @decorators.idempotent_id('d7a96d95-2944-4749-be34-cfe39a5dbcb4')
    def test_cluster_resize_max_size_under_current_desired_capacity(self):
        # New max_size is lower than current desired_capacity of cluster
        params = {
            "resize": {
                "max_size": 2,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

    @decorators.idempotent_id('3b35938f-a73a-4096-bf13-af3709aed47f')
    def test_cluster_resize_max_size_under_current_min_size(self):
        # New max_size is lower than current min_size of cluster
        # with strict set to False
        params = {
            "resize": {
                "max_size": 1,
                "strict": False
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

        # New max_size is lower than current min_size of cluster
        # with strict set to True
        params = {
            "resize": {
                "max_size": 1,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

    @decorators.idempotent_id('1d7595a4-a7a8-42a4-9f90-7501a4bbb7e5')
    def test_cluster_resize_min_size_over_current_desired_capacity(self):
        # New min_size is larger than current desired_capacity of cluster
        params = {
            "resize": {
                "min_size": 4,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

    @decorators.idempotent_id('606e5d3f-0857-4bfe-b52d-2ea1ad0cec16')
    def test_cluster_resize_min_size_over_current_max_size(self):
        # New min_size is larger than current max_size of cluster
        # with strict set to False
        params = {
            "resize": {
                "min_size": 6,
                "strict": False
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

        # New min_size is larger than current max_size of cluster
        # with strict set to True
        params = {
            "resize": {
                "min_size": 6,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterScalingNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterScalingNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('337a8a8f-a368-4d4f-949a-8b116dbb6a75')
    def test_cluster_scale_in_invalid_count(self):
        params = {
            "scale_in": {
                "count": -1
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)

    @decorators.idempotent_id('2bbf6e0c-a8cc-4b29-8060-83652ffd6cd2')
    def test_cluster_scale_out_invalid_count(self):
        params = {
            "scale_out": {
                "count": -1
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterScalingNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('0124c7de-66d0-4a84-9c8f-80bc4d246b79')
    def test_cluster_scale_in_cluster_not_found(self):
        params = {
            "scale_in": {
                "count": 1
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          '0124c7de-66d0-4a84-9c8f-80bc4d246b79', params)

    @decorators.idempotent_id('b7038d95-204c-455f-a866-94dc535dd840')
    def test_cluster_scale_out_cluster_not_found(self):
        params = {
            "scale_out": {
                "count": 1
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          'b7038d95-204c-455f-a866-94dc535dd840',
                          params)


class TestClusterCheckNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('9a305b4f-2f05-4aa9-95ae-e08fd24b0593')
    def test_cluster_check_params_not_dict(self):
        params = {
            'check': ['k1', 'v1']
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterCheckNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('bbbe3feb-8482-4ae4-9c29-b4732efce931')
    def test_cluster_check_cluster_not_found(self):
        params = {
            'check': {'k1': 'v1'}
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          'bbbe3feb-8482-4ae4-9c29-b4732efce931', params)


class TestClusterRecoverNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('1f93e909-b271-4e46-acd8-8cb621b27546')
    def test_cluster_recover_params_not_dict(self):
        params = {
            'recover': ['k1', 'v1']
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterRecoverNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('e6e522f4-34d4-42f7-b7f1-45004e06f3d9')
    def test_cluster_recover_cluster_not_found(self):
        params = {
            'recover': {'k1': 'v1'}
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          'e6e522f4-34d4-42f7-b7f1-45004e06f3d9', params)


class TestClusterAddNodesNegativeInvalidNodesParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('912bb24d-73e1-4801-a6de-bdd453cbbdbf')
    def test_cluster_add_nodes_missing_nodes_params(self):
        params = {
            'add_nodes': {
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('6cb029f7-9b72-4f10-a28b-3ed5bd3ed7b0')
    def test_cluster_add_nodes_params_not_list(self):
        params = {
            'add_nodes': {
                'nodes': 'node_id'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('b8ae9b5f-967f-48a6-8e31-c77f86ba06aa')
    def test_cluster_add_nodes_params_empty_list(self):
        params = {
            'add_nodes': {
                'nodes': []
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterAddNodesNegativeClusterNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('22f10d36-c29a-4cde-a975-af262a5775a1')
    def test_cluster_add_nodes_cluster_not_found(self):
        params = {
            'add_nodes': {
                'nodes': ['node_id']
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          'db0faadf-9cd2-457f-b434-4891b77938ab', params)


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


class TestClusterPolicyAttachNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('76dcdc8d-7680-4e27-bccd-26ad9d697528')
    def test_cluster_policy_attach_params_not_dict(self):
        params = {
            'policy_attach': 'POLICY_ID'
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('34f6ceec-bde2-4013-87fe-db704ada5987')
    def test_cluster_policy_attach_missing_profile_id_param(self):
        params = {
            'policy_attach': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('5f5c42be-8ef4-4150-93cf-1e6b2515a293')
    def test_cluster_policy_attach_invalid_enabled_param(self):
        params = {
            'policy_attach': {
                'policy_id': 'POLICY_ID',
                'enabled': 'flase'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterPolicyAttachNegativePolicyNotFound(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterPolicyAttachNegativePolicyNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('7ee49643-a5a0-4567-b9d0-0210b05a6138')
    def test_cluster_policy_attach_policy_not_found(self):
        params = {
            'policy_attach': {
                'poilicy_id': '7ee49643-a5a0-4567-b9d0-0210b05a6138'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterPolicyAttachNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('29e66d49-9ffa-47c9-bbe3-e0cf9c3370ee')
    def test_cluster_policy_attach_cluster_not_found(self):
        params = {
            'policy_attach': {
                'policy_id': 'POLICY_ID'
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          '29e66d49-9ffa-47c9-bbe3-e0cf9c3370ee', params)


class TestClusterPolicyDetachNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('815a1c5a-f27b-4620-8711-bbef46507447')
    def test_cluster_policy_detach_missing_profile_id_param(self):
        params = {
            'policy_detach': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterPolicyDetachNegativePolicyNotFound(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterPolicyDetachNegativePolicyNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('d8edc8bd-530c-4495-94ea-52d844633335')
    def test_cluster_policy_detach_policy_not_found(self):
        params = {
            'policy_detach': {
                'poilicy_id': '7ee49643-a5a0-4567-b9d0-0210b05a6138'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterPolicyDetachNegativeUnattached(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterPolicyDetachNegativeUnattached, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)

    @decorators.idempotent_id('f302142c-3536-4524-8ce2-da86306731cb')
    def test_cluster_policy_detach_policy_unattached(self):
        params = {
            'policy_detach': {
                'poilicy_id': self.policy_id
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterPolicyDetachNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('11ff0486-a022-4b28-9def-9b2d78d47fab')
    def test_cluster_policy_detach_cluster_not_found(self):
        params = {
            'policy_detach': {
                'policy_id': 'POLICY_ID'
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          '11ff0486-a022-4b28-9def-9b2d78d47fab', params)


class TestClusterPolicyUpdateNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('653d8ea9-9c7e-48f2-b568-6167bb7f8666')
    def test_cluster_policy_update_params_not_dict(self):
        params = {
            'policy_update': 'POLICY_ID'
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('b47dff55-3ff0-4303-b86e-c4ab5f9a0878')
    def test_cluster_policy_update_missing_profile_id_param(self):
        params = {
            'policy_update': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('4adb03f4-35e6-40eb-b867-d75315ca8a89')
    def test_cluster_policy_update_invalid_enabled_param(self):
        params = {
            'policy_update': {
                'policy_id': 'POLICY_ID',
                'enabled': 'flase'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterPolicyUpdateNegativePolicyNotFound(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterPolicyUpdateNegativePolicyNotFound, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('7528bfa5-2106-459a-9ece-f201498b3ace')
    def test_cluster_policy_update_policy_not_found(self):
        params = {
            'policy_update': {
                'poilicy_id': '7528bfa5-2106-459a-9ece-f201498b3ace'
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterPolicyUpdateNegativeUnattached(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterPolicyUpdateNegativeUnattached, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)

    @decorators.idempotent_id('81931b14-0a4c-43e5-a5eb-fdfd5386627e')
    def test_cluster_policy_update_policy_unattached(self):
        params = {
            'policy_update': {
                'poilicy_id': self.policy_id
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterPolicyUpdateNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('c7605959-3bc9-41e2-9685-7e11fa03b9e6')
    def test_cluster_policy_update_cluster_not_found(self):
        params = {
            'policy_update': {
                'policy_id': 'POLICY_ID',
                'enabled': False
            }
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action, 'clusters',
                          'c7605959-3bc9-41e2-9685-7e11fa03b9e6', params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes,
                          'clusters', 'cluster_id', params)

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('600baf2f-e74f-467d-9883-3dcf1c357b57')
    def test_cluster_replace_nodes_params_empty_map(self):
        params = {
            'replace_nodes': {
                'nodes': {}
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes,
                          'clusters', 'cluster_id', params)

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes,
                          'clusters', 'cluster_id', params)

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes,
                          'clusters', 'cluster_id', params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes,
                          'clusters', self.cluster_id, params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes,
                          'clusters', self.cluster_id, params)


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

        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.cluster_replace_nodes,
                          'clusters', self.cluster_id, params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes, 'clusters',
                          self.cluster_id, params)


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.cluster_replace_nodes, 'clusters',
                          self.cluster_id, params)


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
        self.assertRaises(exceptions.NotFound,
                          self.client.cluster_replace_nodes, 'clusters',
                          'db0faadf-9cd2-457f-b434-4891b77938ab', params)
