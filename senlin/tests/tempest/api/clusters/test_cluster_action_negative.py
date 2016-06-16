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
from senlin.tests.tempest.api import utils
from senlin.tests.tempest.common import constants


class TestClusterActionNegativeCommon(base.BaseSenlinTest):

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


class TestClusterResizeNegativeInvalidResizeParams(base.BaseSenlinTest):

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


class TestClusterResizeNegativeClusterNotFound(base.BaseSenlinTest):
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


class TestClusterResizeNegativeSizeCheckFailed(base.BaseSenlinTest):

    def setUp(self):
        super(TestClusterResizeNegativeSizeCheckFailed, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('92e7d3c8-2d38-4766-86c3-41dc14bf89a1')
    def test_cluster_resize_cluster_size_check_failed(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "number": 5,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterScalingNegativeBadRequest(base.BaseSenlinTest):

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


class TestClusterScalingNegativeNotFound(base.BaseSenlinTest):

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


class TestClusterAddNodesNegativeInvalidNodesParams(base.BaseSenlinTest):

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


class TestClusterAddNodesNegativeNodeNotFound(base.BaseSenlinTest):

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


class TestClusterAddNodesNegativeNodeNotOrphan(base.BaseSenlinTest):

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

        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)


class TestClusterAddNodesNegativeProfileTypeUnmatch(base.BaseSenlinTest):

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


class TestClusterAddNodesNegativeSizeCheckFailed(base.BaseSenlinTest):

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


class TestClusterAddNodesNegativeClusterNotFound(base.BaseSenlinTest):

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
