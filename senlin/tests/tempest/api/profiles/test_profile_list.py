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


class TestProfileList(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestProfileList, cls).resource_setup()
        # Create profile
        cls.profile = cls.create_profile(constants.spec_nova_server)

    @classmethod
    def resource_cleanup(cls):
        # Delete profile
        cls.client.delete_obj('profiles', cls.profile['id'])
        super(TestProfileList, cls).resource_cleanup()

    @decorators.idempotent_id('329d3026-12f7-4369-845b-05914e2a8678')
    def test_list_profile(self):
        res = self.client.list_objs('profiles')

        # Verify resp of profile list API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        profiles = res['body']
        ids = []
        for profile in profiles:
            for key in ['created_at', 'domain', 'id', 'metadata', 'name',
                        'project', 'spec', 'type', 'updated_at', 'user']:
                self.assertIn(key, profile)
            ids.append(profile['id'])
        self.assertIn(self.profile['id'], ids)
