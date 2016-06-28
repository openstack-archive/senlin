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
from tempest import test

from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestLBPolicy(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestLBPolicy, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=2)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['functional'])
    @decorators.idempotent_id('6b513a5d-75b6-447a-b95d-e17b84ac9ee8')
    def test_lb_policy(self):
        # Verify there is no lb information in node data
        cluster = utils.get_a_cluster(self, self.cluster_id)
        for n in cluster['nodes']:
            node = utils.get_a_node(self, n)
            self.assertNotIn('lb_member', node['data'])

        # Create a lb policy
        spec = constants.spec_lb_policy
        policy_id = utils.create_a_policy(self, spec)
        lb_policy = utils.get_a_policy(self, policy_id)
        self.addCleanup(utils.delete_a_policy, self, lb_policy['id'])

        # Attach lb policy to cluster
        utils.cluster_attach_policy(self, self.cluster_id, lb_policy['id'])

        # Verify lb information is added into node data
        cluster = utils.get_a_cluster(self, self.cluster_id)
        for n in cluster['nodes']:
            node = utils.get_a_node(self, n)
            self.assertIn('lb_member', node['data'])

        # Scale out cluster
        utils.cluster_scale_out(self, self.cluster_id)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, cluster['desired_capacity'])
        self.assertEqual(3, len(cluster['nodes']))

        # Verify lb information in all nodes' data
        cluster = utils.get_a_cluster(self, self.cluster_id)
        for n in cluster['nodes']:
            node = utils.get_a_node(self, n)
            self.assertIn('lb_member', node['data'])

        # Scale in cluster
        utils.cluster_scale_in(self, self.cluster_id)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))
        for n in cluster['nodes']:
            node = utils.get_a_node(self, n)
            self.assertIn('lb_member', node['data'])

        # Detach lb policy from cluster
        utils.cluster_detach_policy(self, self.cluster_id, lb_policy['id'])

        # Verify lb information has been removed from node data
        cluster = utils.get_a_cluster(self, self.cluster_id)
        for n in cluster['nodes']:
            node = utils.get_a_node(self, n)
            self.assertNotIn('lb_member', node['data'])
