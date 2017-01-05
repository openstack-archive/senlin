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
