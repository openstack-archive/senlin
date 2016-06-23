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

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestClusterActionResize(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionResize, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('f5f75882-df3d-481f-bd05-019e4d08af65')
    def test_cluster_action_resize(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 20,
                "min_step": 1,
                "min_size": 5,
                "number": 20,
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


class TestClusterActionScaleOut(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionScaleOut, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('f15ff8cc-4be3-4c93-9979-6be428e83cd7')
    def test_cluster_action_scale_out(self):
        params = {
            "scale_out": {
                "count": "1"
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


class TestClusterActionScaleIn(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionScaleIn, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('a579cd01-8096-4bee-9978-d095025f605c')
    def test_cluster_action_scale_in(self):
        params = {
            "scale_in": {
                "count": "1"
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


class TestClusterActionCheck(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionCheck, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('0d2063a8-b3d3-489d-b949-e2c61a0997ee')
    def test_cluster_action_check(self):
        params = {
            "check": {}
        }
        # Trigger cluster action
        res = self.client.trigger_action('clusters', self.cluster_id,
                                         params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestClusterActionRecover(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionRecover, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('9020bc7e-db2a-47d0-9f78-7e6a3d231fad')
    def test_cluster_action_recover(self):
        params = {
            "recover": {
                "operation": "rebuild"
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


class TestClusterActionPolicyAttach(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionPolicyAttach, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)
        self.addCleanup(utils.cluster_detach_policy, self, self.cluster_id,
                        self.policy_id)

    @decorators.idempotent_id('214c48f8-cca9-4512-a904-2985743a1155')
    def test_cluster_action_policy_attach(self):
        params = {
            "policy_attach": {
                "enabled": True,
                "policy_id": self.policy_id
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


class TestClusterActionPolicyDetach(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionPolicyDetach, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)
        utils.cluster_attach_policy(self, self.cluster_id, self.policy_id)

    @decorators.idempotent_id('8643245e-ee32-41bb-a736-e33c9e77202a')
    def test_cluster_action_policy_detach(self):
        params = {
            "policy_detach": {
                "policy_id": self.policy_id
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


class TestClusterActionPolicyUpdate(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionPolicyUpdate, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)
        utils.cluster_attach_policy(self, self.cluster_id, self.policy_id)
        self.addCleanup(utils.cluster_detach_policy, self, self.cluster_id,
                        self.policy_id)

    @decorators.idempotent_id('0b9efe3e-0abf-4230-a278-b282578df111')
    def test_cluster_action_policy_update(self):
        params = {
            "policy_update": {
                "enabled": False,
                "policy_id": self.policy_id
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
