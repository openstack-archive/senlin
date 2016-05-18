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


class TestPolicyShow(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestPolicyShow, cls).resource_setup()
        # Create policy
        cls.policy = cls.create_test_policy()

    @classmethod
    def resource_cleanup(cls):
        # Delete policy
        cls.client.delete_obj('policies', cls.policy['id'])
        super(TestPolicyShow, cls).resource_cleanup()

    @decorators.idempotent_id('7ab18be1-e554-452d-91ac-9b5e5c87430b')
    def test_show_policy(self):
        res = self.client.get_obj('policies', self.policy['id'])

        # Verify resp of policy show API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        policy = res['body']
        for key in ['created_at', 'data', 'domain', 'id', 'name', 'project',
                    'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, policy)
