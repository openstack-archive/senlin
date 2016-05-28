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


class TestClusterDeleteNegative(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterDeleteNegative, cls).resource_setup()
        cls.profile_id = utils.create_a_profile(cls)
        cls.cluster_id = utils.create_a_cluster(cls, cls.profile_id)['id']
        cls.policy = cls.create_test_policy()
        cls.attach_policy(cls.cluster_id, cls.policy['id'])

    @classmethod
    def resource_cleanup(cls):
        # Detach policy from cluster and delete it
        cls.detach_policy(cls.cluster_id, cls.policy['id'])
        cls.client.delete_obj('policies', cls.policy['id'])
        utils.delete_a_cluster(cls, cls.cluster_id)
        utils.delete_a_profile(cls, cls.profile_id)
        super(TestClusterDeleteNegative, cls).resource_cleanup()

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0de81427-2b2f-4821-9462-c893d35fb212')
    def test_cluster_delete_conflict(self):
        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.delete_obj,
                          'clusters', self.cluster_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('8a583b8e-eeaa-4920-a6f5-2880b070624f')
    def test_cluster_delete_not_found(self):
        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.delete_obj,
                          'clusters', '8a583b8e-eeaa-4920-a6f5-2880b070624f')
