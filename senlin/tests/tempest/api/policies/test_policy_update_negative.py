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


class TestPolicyUpdateNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('5df90d82-9889-4c6f-824c-30272bcfa767')
    def test_policy_update_policy_not_found(self):
        self.assertRaises(exceptions.NotFound,
                          self.client.update_obj,
                          'policies', '5df90d82-9889-4c6f-824c-30272bcfa767',
                          {'policy': {'name': 'new-name'}})


class TestPolicyUpdateNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestPolicyUpdateNegativeBadRequest, self).setUp()
        # Create a policy
        policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, policy_id)
        self.policy_id = policy_id

    @test.attr(type=['negative'])
    @decorators.idempotent_id('31242de5-55ac-4589-87a1-a9940e4beca2')
    def test_policy_update_no_property_updated(self):
        # No property is updated.
        params = {
            'policy': {}
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.update_obj,
                          'policies', self.policy_id, params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d2ca7de6-0069-48c9-b3de-ee975a2428dc')
    def test_policy_update_spec_not_updatable(self):
        # Try to update spec of policy.
        # Note: name is the only property that can be updated
        # after policy is created.
        params = {
            'policy': {
                'name': 'new-name',
                'spec': {'k1': 'v1'}
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.update_obj,
                          'policies', self.policy_id, params)
