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

from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestBatchPolicy(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestBatchPolicy, self).setUp()
        self.new_profile2 = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.new_profile2)
        self.new_profile = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.new_profile)
        self.old_profile = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.old_profile)
        self.cluster_id = utils.create_a_cluster(self, self.old_profile,
                                                 min_size=0, max_size=2,
                                                 desired_capacity=2)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('b35e63ed-f1d5-4ec6-afb0-2378d260afcb')
    def test_batch_policy(self):
        # Create a batch policy targets on CLUSTER_UPDATE action
        spec = constants.spec_batch_policy
        policy_id = utils.create_a_policy(self, spec)
        self.addCleanup(utils.delete_a_policy, self, policy_id)

        # Attach batch policy to cluster
        utils.cluster_attach_policy(self, self.cluster_id, policy_id)
        self.addCleanup(utils.cluster_detach_policy, self,
                        self.cluster_id, policy_id)

        utils.update_a_cluster(self, self.cluster_id,
                               profile_id=self.new_profile)

        # Verify cluster update result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, len(cluster['nodes']))
        self.assertEqual(self.new_profile, cluster['profile_id'])
