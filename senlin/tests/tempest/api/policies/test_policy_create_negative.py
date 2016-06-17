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


class TestPolicyCreateNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('3fea4aa9-6dee-4202-8611-cf2d008a4d42')
    def test_policy_create_policy_data_not_specified(self):
        params = {
            'poliyc': {
                'name': 'test-policy'
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'policies', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('4a4d6c83-f0fa-4c9e-914b-d89478903d95')
    def test_policy_create_name_not_specified(self):
        params = {
            'policy': {
                'spec': constants.spec_scaling_policy
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'policies', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b898de6c-996a-4bc3-bdef-6490e62fb3b0')
    def test_policy_create_spec_not_specified(self):
        params = {
            'policy': {
                'name': 'test-policy',
                'spce': constants.spec_scaling_policy
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'policies', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('1c0ed145-bca6-4e53-b222-44fc6978eb1f')
    def test_policy_create_policy_type_incorrect(self):
        spec = copy.deepcopy(constants.spec_scaling_policy)
        spec['type'] = 'senlin.policy.bogus'
        params = {
            'policy': {
                'name': 'test-policy',
                'spce': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'policies', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f55dc7eb-9863-49c2-b001-368d2057c53c')
    def test_policy_create_spec_validation_failed(self):
        spec = copy.deepcopy(constants.spec_scaling_policy)
        spec['properties']['bogus'] = 'foo'
        params = {
            'policy': {
                'name': 'test-policy',
                'spce': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'policies', params)
