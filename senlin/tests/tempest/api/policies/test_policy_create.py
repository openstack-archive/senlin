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


class TestPolicyCreate(base.BaseSenlinTest):

    def setUp(self):
        super(TestPolicyCreate, self).setUp()
        self.policy_id = None

    @decorators.idempotent_id('f50648d9-f38c-479a-a82b-3c6909733496')
    def test_policy_create(self):
        params = {
            'policy': {
                'name': 'test-scaling-policy',
                'spec': constants.spec_scaling_policy,
            }
        }
        res = self.client.create_obj('policies', params)

        # Verify resp of receiver create API
        self.assertEqual(201, res['status'])
        self.assertIsNotNone(res['body'])
        policy = res['body']

        self.addCleanup(self.client.delete_obj, 'policies', policy['id'])

        for key in ['created_at', 'data', 'domain', 'id', 'name', 'project',
                    'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, policy)
        self.assertEqual('test-scaling-policy', policy['name'])
        self.assertEqual('senlin.policy.scaling-1.0', policy['type'])
        self.assertEqual(constants.spec_scaling_policy, policy['spec'])
