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

from senlin.common.i18n import _
from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestScalingPolicy(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestScalingPolicy, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestScalingPolicy, self).tearDown()

    def test_scaling_policy(self):
        # Create cluster
        desired_capacity = 1
        min_size = 0
        max_size = 5
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Create a scaling policy targets on CLUSTER_SCALE_OUT action
        spec = test_utils.spec_scaling_policy
        spec['properties'] = {
            'event': 'CLUSTER_SCALE_OUT',
            'adjustment': {
                'type': 'CHANGE_IN_CAPACITY',
                'number': 2,
                'min_step': 1,
                'best_effort': True
            }
        }
        scaling_out_policy = test_api.create_policy(
            self.client, test_utils.random_name('policy'), spec)

        # Create a scaling policy targets on CLUSTER_SCALE_IN action
        spec['properties'] = {
            'event': 'CLUSTER_SCALE_IN',
            'adjustment': {
                'type': 'CHANGE_IN_PERCENTAGE',
                'number': 50,
                'min_step': 2,
                'best_effort': False
            }
        }
        scaling_in_policy = test_api.create_policy(
            self.client, test_utils.random_name('policy'), spec)

        # Attach scaling in/out policies to cluster
        for policy in [scaling_in_policy, scaling_out_policy]:
            params = {
                "enabled": True,
                "policy_id": policy['id']
            }
            action_id = test_api.action_cluster(self.client, cluster['id'],
                                                'policy_attach', params)
            test_utils.wait_for_status(test_api.get_action, self.client,
                                       action_id, 'SUCCEEDED')

        # Scale out cluster without params
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, len(cluster['nodes']))

        # Scale out with count set to 1
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out', {'count': 1})
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, len(cluster['nodes']))

        # Scale out with count set to 3 to verify best_effort param
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out', {'count': 3})
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, len(cluster['nodes']))

        # Scale in cluster without params
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale in result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, len(cluster['nodes']))

        # Scale in without param to verify min_step param
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale in result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Scale in with count set to 2 to verify best_effort param
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in', {'count': 2})
        action = test_utils.wait_for_status(test_api.get_action, self.client,
                                            action_id, 'FAILED')

        reason = _("Policy check failure: The target capacity (-1) is less "
                   "than the cluster's min_size (0).")
        self.assertEqual(reason, action['status_reason'])

        # Verify cluster scale in result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Detach scaling in/out policies from cluster
        for policy in [scaling_in_policy, scaling_out_policy]:
            params = {
                "policy_id": policy['id']
            }
            action_id = test_api.action_cluster(self.client, cluster['id'],
                                                'policy_detach', params)
            test_utils.wait_for_status(test_api.get_action, self.client,
                                       action_id, 'SUCCEEDED')

        # Delete policies
        test_api.delete_policy(self.client, scaling_in_policy['id'])
        test_api.delete_policy(self.client, scaling_out_policy['id'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])
