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
from senlin.tests.tempest.common import utils


class TestProfileCreate(base.BaseSenlinAPITest):

    @decorators.idempotent_id('76216581-e78a-42f5-bf1d-65d83bd206fc')
    def test_profile_create(self):
        params = {
            'profile': {
                'name': 'test-profile',
                'spec': constants.spec_nova_server,
                'metadata': {'foo': 'bar'}
            }
        }
        res = self.client.create_obj('profiles', params)

        # Verify resp of profile create API
        self.assertEqual(201, res['status'])
        self.assertIsNotNone(res['body'])
        profile = res['body']
        self.addCleanup(utils.delete_a_profile, self, profile['id'])

        for key in ['created_at', 'domain', 'id', 'metadata', 'name',
                    'project', 'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, profile)
        self.assertEqual('test-profile', profile['name'])
        self.assertEqual('os.nova.server-1.0', profile['type'])
        self.assertEqual(constants.spec_nova_server, profile['spec'])
        self.assertEqual({'foo': 'bar'}, profile['metadata'])
