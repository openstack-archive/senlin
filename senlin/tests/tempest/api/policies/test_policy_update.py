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
from senlin.tests.tempest.api import utils


class TestPolicyUpdate(base.BaseSenlinTest):

    def setUp(self):
        super(TestPolicyUpdate, self).setUp()
        self.policy_id = utils.create_a_policy(self)
        self.addCleanup(utils.delete_a_policy, self, self.policy_id)

    @decorators.idempotent_id('dbe9c6a6-882c-41cf-b862-7f648804db24')
    def test_policy_update(self):
        params = {
            'policy': {
                'name': 'updated-policy-name'
            }
        }
        res = self.client.update_obj('policies', self.policy_id, params)

        # Verify resp of policy update API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        policy = res['body']
        for key in ['created_at', 'data', 'domain', 'id', 'name', 'project',
                    'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, policy)
        self.assertEqual('updated-policy-name', policy['name'])
