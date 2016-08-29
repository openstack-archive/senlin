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

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import constants


class TestPolicyValidate(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestPolicyValidate, self).setUp()
        self.policy_id = None

    @decorators.idempotent_id('a3f5ad0d-4f3d-4b40-b473-1cfc562cfcee')
    def test_policy_validate(self):
        params = {
            'policy': {
                'spec': constants.spec_scaling_policy,
            }
        }
        res = self.client.validate_obj('policies', params)

        # Verify resp of policy validate API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        policy = res['body']

        for key in ['created_at', 'data', 'domain', 'id', 'name', 'project',
                    'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, policy)
        self.assertEqual('validated_policy', policy['name'])
        self.assertEqual('senlin.policy.scaling-1.0', policy['type'])
        self.assertEqual(constants.spec_scaling_policy, policy['spec'])
