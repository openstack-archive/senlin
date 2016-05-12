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


class TestProfileShow(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestProfileShow, cls).resource_setup()
        # Create profile
        cls.profile = cls.create_profile(constants.spec_nova_server)

    @classmethod
    def resource_cleanup(cls):
        # Delete profile
        cls.client.delete_obj('profiles', cls.profile['id'])
        super(TestProfileShow, cls).resource_setup()

    @decorators.idempotent_id('36206711-0676-4e4f-8f5d-7029912ecade')
    def test_show_profile(self):
        res = self.client.get_obj('profiles', self.profile['id'])

        # Verify resp of profile update API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        profile = res['body']
        for key in ['created_at', 'domain', 'id', 'metadata', 'name',
                    'project', 'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, profile)
