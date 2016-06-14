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


class TestPolicyDeleteNegativeConflict(base.BaseSenlinTest):

    def setUp(self):
        super(TestPolicyDeleteNegativeConflict, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)

        utils.attach_policy(self, cluster_id, self.policy_id)
        self.addCleanup(utils.detach_policy, self, cluster_id, self.policy_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b8b8fca8-962f-4cad-bfca-76683df7b617')
    def test_policy_delete_conflict(self):
        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.delete_obj,
                          'policies', self.policy_id)


class TestPolicyDeleteNegativeNotFound(base.BaseSenlinTest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('5591416f-4646-46c2-83b4-231e72aa4bfe')
    def test_policy_delete_not_found(self):
        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.delete_obj,
                          'policies', '5591416f-4646-46c2-83b4-231e72aa4bfe')


class TestPolicyDeleteNegativeBadRequest(base.BaseSenlinTest):

    def setUp(self):
        super(TestPolicyDeleteNegativeBadRequest, self).setUp()
        self.policy_id1 = utils.create_a_policy(self, name='p-01')
        self.addCleanup(utils.delete_a_policy, self, self.policy_id1)
        self.policy_id2 = utils.create_a_policy(self, name='p-01')
        self.addCleanup(utils.delete_a_policy, self, self.policy_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d6f35043-2db5-49ff-8bc4-ba14a652f748')
    def test_policy_delete_multiple_choice(self):
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.delete_obj,
                          'policies', 'p-01')
