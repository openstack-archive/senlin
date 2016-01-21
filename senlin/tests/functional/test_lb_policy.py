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

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestLBPolicy(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestLBPolicy, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestLBPolicy, self).tearDown()

    def test_lb_policy(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 5
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Verify there is no lb information in node data
        cluster = test_api.get_cluster(self.client, cluster['id'])
        for n in cluster['nodes']:
            node = test_api.get_node(self.client, n)
            self.assertNotIn('lb_member', node['data'])

        # Create a lb policy
        spec = test_utils.spec_lb_policy
        lb_policy = test_api.create_policy(self.client,
                                           test_utils.random_name('lb-policy'),
                                           spec)

        # Attach scaling in/out policies to cluster
        params = {
            "enabled": True,
            "policy_id": lb_policy['id']
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'policy_attach', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify lb information recorded in node data
        cluster = test_api.get_cluster(self.client, cluster['id'])
        for n in cluster['nodes']:
            node = test_api.get_node(self.client, n)
            self.assertIn('lb_member', node['data'])

        # Scale out cluster
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, len(cluster['nodes']))

        # Verify lb information recorded in node data
        cluster = test_api.get_cluster(self.client, cluster['id'])
        for n in cluster['nodes']:
            node = test_api.get_node(self.client, n)
            self.assertIn('lb_member', node['data'])

        # Scale in cluster
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Detach scaling lb policy from cluster
        params = {
            "policy_id": lb_policy['id']
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'policy_detach', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify lb information recorded in node data
        cluster = test_api.get_cluster(self.client, cluster['id'])
        for n in cluster['nodes']:
            node = test_api.get_node(self.client, n)
            self.assertNotIn('lb_member', node['data'])

        # Delete policies
        test_api.delete_policy(self.client, lb_policy['id'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])
