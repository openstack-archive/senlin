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


class TestPolicyTypeShow(base.BaseSenlinTest):

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
