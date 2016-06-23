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


class TestProfileList(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestProfileList, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)

    @decorators.idempotent_id('329d3026-12f7-4369-845b-05914e2a8678')
    def test_profile_list(self):
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
        self.assertIn(self.profile_id, ids)
