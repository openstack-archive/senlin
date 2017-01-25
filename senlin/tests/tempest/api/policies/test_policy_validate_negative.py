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


class TestPolicyValidateNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('4b55bb3e-12d6-4728-9b53-9db5094ac8b5')
    def test_policy_validate_with_empty_body(self):
        params = {}
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.validate_obj,
                               'policies', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Request body missing 'policy' key.", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('4c9f26cc-f4f3-4303-9f29-f30fae400843')
    def test_policy_validate_invalid_param(self):
        params = {
            'policy': {
                'name': 'fake'
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.validate_obj,
                               'policies', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Additional properties are not allowed (u'name' "
            "was unexpected)", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('a1c35d93-2d19-4a72-919f-cfd70f5cbf06')
    def test_policy_validate_no_spec(self):
        params = {
            'policy': {}
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.validate_obj,
                               'policies', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "'spec' is a required property", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('6073da36-ee3e-4925-bce1-6c9a158e710d')
    def test_policy_validate_policy_type_incorrect(self):
        spec = copy.deepcopy(constants.spec_scaling_policy)
        spec['type'] = 'senlin.policy.bogus'
        params = {
            'policy': {
                'spec': spec
            }
        }
        # Verify badrequest exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.validate_obj,
                               'policies', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The policy_type 'senlin.policy.bogus-1.0' could "
            "not be found.", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('1e1833ea-4a67-4ac1-b6e2-f9afff51c945')
    def test_policy_validate_spec_validation_failed(self):
        spec = copy.deepcopy(constants.spec_scaling_policy)
        spec['properties']['bogus'] = 'foo'
        params = {
            'policy': {
                'spec': spec
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.ServerFault,
                               self.client.validate_obj,
                               'policies', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Unrecognizable spec item 'bogus'", str(message))
