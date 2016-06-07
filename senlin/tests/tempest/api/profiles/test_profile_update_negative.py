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


# TODO(Yanyan Hu): Add more negative tests for profile_update
# including profile NotFound, no property is updated.
class TestProfileUpdateNegativeBadRequest(base.BaseSenlinTest):

    def setUp(self):
        super(TestProfileUpdateNegativeBadRequest, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d2ca7de6-0069-48c9-b3de-ee975a2428dc')
    def test_profile_update_spec_not_updatable(self):
        # Try to update spec of profile which is not allowed.
        params = {
            'profile': {
                'name': 'new-name',
                'spec': {'k1': 'v1'}
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.update_obj,
                          'profiles', self.profile_id, params)
