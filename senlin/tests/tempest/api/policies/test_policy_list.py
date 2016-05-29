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


class TestPolicyList(base.BaseSenlinTest):

    def setUp(self):
        super(TestPolicyList, self).setUp()
        self.policy_id = self.create_test_policy()['id']
        self.addCleanup(self.client.delete_obj, 'policies', self.policy_id)

    @decorators.idempotent_id('67ce5d15-c1fd-402f-bcd8-2974dbd93da8')
    def test_list_policy(self):
        res = self.client.list_objs('policies')

        # Verify resp of policy list API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        policies = res['body']
        ids = []
        for policy in policies:
            for key in ['created_at', 'data', 'domain', 'id', 'name',
                        'project', 'spec', 'type', 'updated_at', 'user']:
                self.assertIn(key, policy)
            ids.append(policy['id'])
        self.assertIn(self.policy_id, ids)
