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

    @classmethod
    def resource_setup(cls):
        super(TestPolicyDeleteNegative, cls).resource_setup()
        cls.profile_id = utils.create_a_profile(cls)
        cls.cluster_id = utils.create_a_cluster(cls, cls.profile_id)
        cls.policy = cls.create_test_policy()
        cls.attach_policy(cls.cluster_id, cls.policy['id'])

    @classmethod
    def resource_cleanup(cls):
        # Detach policy from cluster and delete it
        cls.detach_policy(cls.cluster_id, cls.policy['id'])
        cls.client.delete_obj('policies', cls.policy['id'])
        utils.delete_a_cluster(cls, cls.cluster_id)
        utils.delete_a_profile(cls, cls.profile_id)
        super(TestPolicyDeleteNegative, cls).resource_cleanup()

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b8b8fca8-962f-4cad-bfca-76683df7b617')
    def test_policy_delete_conflict(self):
        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.delete_obj,
                          'policies',
                          self.policy['id'])
