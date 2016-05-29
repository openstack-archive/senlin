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
from tempest import test

from senlin.tests.tempest.api import base
from senlin.tests.tempest.api import utils


class TestPolicyDeleteNegative(base.BaseSenlinTest):

    def setUp(self):
        super(TestPolicyDeleteNegative, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        self.policy_id = self.create_test_policy()['id']
        self.addCleanup(self.client.delete_obj, 'policies', self.policy_id)

        self.attach_policy(cluster_id, self.policy_id)
        self.addCleanup(self.detach_policy, cluster_id, self.policy_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b8b8fca8-962f-4cad-bfca-76683df7b617')
    def test_policy_delete_conflict(self):
        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.delete_obj,
                          'policies', self.policy_id)
