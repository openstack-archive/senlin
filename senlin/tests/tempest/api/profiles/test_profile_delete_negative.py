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
from senlin.tests.tempest.common import constants


class TestProfileDeleteNegative(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestProfileDeleteNegative, cls).resource_setup()
        cls.profile = cls.create_profile(constants.spec_nova_server)
        cls.cluster = utils.create_a_cluster(cls, cls.profile['id'])

    @classmethod
    def resource_cleanup(cls):
        # Delete test cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestProfileDeleteNegative, cls).resource_cleanup()

    @test.attr(type=['negative'])
    @decorators.idempotent_id('8e5e8414-b757-41f4-b633-e0fa83d72ea2')
    def test_profile_delete_conflict(self):
        # Verify conflict exception(409) is raised.
        self.assertRaises(exceptions.Conflict,
                          self.client.delete_obj,
                          'profiles',
                          self.profile['id'])
