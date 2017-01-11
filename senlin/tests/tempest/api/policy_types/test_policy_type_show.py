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
from senlin.tests.tempest.common import utils


class TestPolicyTypeShow(base.BaseSenlinAPITest):

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('57791ed7-7f57-4369-ba6e-7e039169ebdc')
    def test_policy_type_show(self):
        res = self.client.get_obj('policy-types', 'senlin.policy.deletion-1.0')

        # Verify resp of policy type show API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        policy_type = res['body']
        for key in ['name', 'schema']:
            self.assertIn(key, policy_type)
        self.assertEqual('senlin.policy.deletion-1.0', policy_type['name'])

    @utils.api_microversion('1.5')
    @decorators.idempotent_id('1900b22a-012d-41f0-85a2-8aa6b65ec2ca')
    def test_policy_type_show_v1_5(self):
        res = self.client.get_obj('policy-types', 'senlin.policy.deletion-1.0')

        # Verify resp of policy type show API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        policy_type = res['body']
        for key in ['name', 'schema', 'support_status']:
            self.assertIn(key, policy_type)
        self.assertEqual('senlin.policy.deletion-1.0', policy_type['name'])
        self.assertIsNotNone(policy_type['support_status'])
