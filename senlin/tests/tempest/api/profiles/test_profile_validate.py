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


class TestProfileValidate(base.BaseSenlinAPITest):

    @decorators.idempotent_id('ff678e2d-60d0-43da-808f-cb70a3926112')
    def test_profile_validate(self):
        params = {
            'profile': {
                'spec': constants.spec_nova_server,
            }
        }
        res = self.client.validate_obj('profiles', params)

        # Verify resp of validate create API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        profile = res['body']
        for key in ['created_at', 'domain', 'id', 'metadata', 'name',
                    'project', 'spec', 'type', 'updated_at', 'user']:
            self.assertIn(key, profile)
        self.assertEqual('validated_profile', profile['name'])
        self.assertEqual('os.nova.server-1.0', profile['type'])
        self.assertEqual(constants.spec_nova_server, profile['spec'])
