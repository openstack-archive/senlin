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

import copy
from tempest.lib import decorators
from tempest.lib import exceptions
from tempest import test

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import constants


class TestProfileValidateNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d128781c-808f-4dee-b8b6-abe4def40eb1')
    def test_profile_validate_empty_body(self):
        params = {}
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.validate_obj,
                               'profiles', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Request body missing 'profile' key.", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('7c66eaa1-a78c-4b60-9b0f-c6fa91f28778')
    def test_profile_validate_no_spec(self):
        params = {
            'profile': {}
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.validate_obj,
                               'profiles', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("'spec' is a required property", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d661c452-3752-4196-9649-4b44ac9c55a6')
    def test_profile_validate_profile_type_incorrect(self):
        spec = copy.deepcopy(constants.spec_nova_server)
        spec['type'] = 'senlin.profile.bogus'
        params = {
            'profile': {
                'spec': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.validate_obj,
                               'profiles', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The profile_type 'senlin.profile.bogus-1.0' could "
            "not be found.", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('c0fe55cf-608c-4e89-bf85-4561805fc867')
    def test_profile_validate_spec_validation_failed(self):
        spec = copy.deepcopy(constants.spec_nova_server)
        spec['properties']['bogus'] = 'foo'
        params = {
            'profile': {
                'spec': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.validate_obj,
                               'profiles', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Unrecognizable spec item 'bogus'", str(message))
