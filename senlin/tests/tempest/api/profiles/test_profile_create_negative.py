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


class TestProfileCreateNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0f0183b8-0f5e-4367-993d-863ff1f30d49')
    def test_profile_create_profile_data_not_specified(self):
        params = {
            'profiel': {
                'name': 'test-profile'
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'profiles', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('c341f22d-833b-4676-8b66-e6cdb0b77abd')
    def test_profile_create_name_not_specified(self):
        params = {
            'profile': {
                'spec': constants.spec_nova_server
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'profiles', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('5e644149-a7e6-4e93-8220-4a32f98d6e25')
    def test_profile_create_spec_not_specified(self):
        params = {
            'profile': {
                'name': 'test-profile',
                'spce': constants.spec_nova_server
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'profiles', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('591f3670-3fec-4645-bae2-4f6dec28d70c')
    def test_profile_create_profile_type_incorrect(self):
        spec = copy.deepcopy(constants.spec_nova_server)
        spec['type'] = 'senlin.profile.bogus'
        params = {
            'profile': {
                'name': 'test-profile',
                'spce': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'profiles', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('66977f7a-5d30-481c-a5ec-a445e80a7c0f')
    def test_profile_create_spec_validation_failed(self):
        spec = copy.deepcopy(constants.spec_nova_server)
        spec['properties']['bogus'] = 'foo'
        params = {
            'profile': {
                'name': 'test-profile',
                'spce': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'profiles', params)
