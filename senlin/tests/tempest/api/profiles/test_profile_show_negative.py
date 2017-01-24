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
from senlin.tests.tempest.common import utils


class TestProfileShowNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('887aa1a5-e623-4b49-bdba-e62366b8b636')
    def test_profile_show_not_found(self):
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.get_obj, 'profiles',
                               '887aa1a5-e623-4b49-bdba-e62366b8b636')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The profile '887aa1a5-e623-4b49-bdba-e62366b8b636' "
            "could not be found.", str(message))


class TestProfileShowNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestProfileShowNegativeBadRequest, self).setUp()
        profile_id1 = utils.create_a_profile(self, name='p-01')
        profile_id2 = utils.create_a_profile(self, name='p-01')
        self.addCleanup(utils.delete_a_profile, self, profile_id1)
        self.addCleanup(utils.delete_a_profile, self, profile_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f0ea4ff1-81f9-49e1-ba1b-40964677f7da')
    def test_profile_show_multiple_choice(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.get_obj,
                               'profiles', 'p-01')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Multiple results found matching the query criteria "
            "'p-01'. Please be more specific.", str(message))
