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


class TestProfileUpdate(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestProfileUpdate, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)

    @decorators.idempotent_id('d7efdd92-1687-444e-afcc-b7f9c7e37478')
    def test_profile_update(self):
        params = {
            'profile': {
                'name': 'updated-profile-name',
                'metadata': {'bar': 'foo'}
            }
        }
        res = self.client.update_obj('profiles', self.profile_id, params)

        # Verify resp of profile update API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        profile = res['body']
        for key in ['created_at', 'domain', 'id', 'metadata', 'name',
                    'project', 'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, profile)
        self.assertEqual('updated-profile-name', profile['name'])
        self.assertEqual({'bar': 'foo'}, profile['metadata'])
