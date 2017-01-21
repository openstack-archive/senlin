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


class TestClusterPolicyUpdateNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('653d8ea9-9c7e-48f2-b568-6167bb7f8666')
    def test_cluster_policy_update_params_not_dict(self):
        params = {
            'policy_update': 'POLICY_ID'
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("The data provided is not a map",
                         str(message))

    @decorators.idempotent_id('b47dff55-3ff0-4303-b86e-c4ab5f9a0878')
    def test_cluster_policy_update_missing_profile_id_param(self):
        params = {
            'policy_update': {}
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("'policy_id' is a required property",
                         str(message))

    @decorators.idempotent_id('4adb03f4-35e6-40eb-b867-d75315ca8a89')
    def test_cluster_policy_update_invalid_enabled_param(self):
        params = {
            'policy_update': {
                'policy_id': 'POLICY_ID',
                'enabled': 'not-bool'
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Unrecognized value 'not-bool', acceptable values are: '0', '1', "
            "'f', 'false', 'n', 'no', 'off', 'on', 't', 'true', 'y', 'yes'",
            str(message))


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
                'policy_id': '7528bfa5-2106-459a-9ece-f201498b3ace'
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified policy '7528bfa5-2106-459a-9ece-f201498b3ace' "
            "could not be found.", str(message))


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
                'policy_id': self.policy_id
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The policy '%s' is not attached to the specified cluster "
            "'%s'." % (self.policy_id, self.cluster_id), str(message))


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
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action, 'clusters',
                               'c7605959-3bc9-41e2-9685-7e11fa03b9e6',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster 'c7605959-3bc9-41e2-9685-7e11fa03b9e6' could "
            "not be found.", str(message))
