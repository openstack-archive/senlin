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
