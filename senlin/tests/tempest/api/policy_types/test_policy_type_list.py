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


class TestPolicyTypeList(base.BaseSenlinAPITest):

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('72cc0347-3eab-4cf6-b1ee-531b11f20550')
    def test_policy_type_list(self):
        res = self.client.list_objs('policy-types')

        # Verify resp of policy type list API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        policy_types = res['body']
        for policy_type in policy_types:
            self.assertIn('name', policy_type)

    @utils.api_microversion('1.5')
    @decorators.idempotent_id('1900b22a-012d-41f0-85a2-8aa6b65ec2ca')
    def test_profile_type_list_v1_5(self):
        res = self.client.list_objs('policy-types')

        # Verify resp of profile type list API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        profile_types = res['body']
        expected_names = [
            'senlin.policy.affinity',
            'senlin.policy.batch',
            'senlin.policy.deletion',
            'senlin.policy.health',
            'senlin.policy.loadbalance',
            'senlin.policy.region_placement',
            'senlin.policy.scaling',
            'senlin.policy.zone_placement',
        ]
        for t in profile_types:
            self.assertIn(t['name'], expected_names)
            self.assertIsNotNone(t['support_status'])
            self.assertIsNotNone(t['version'])
