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


class TestProfileTypeList(base.BaseSenlinAPITest):

    @decorators.idempotent_id('fa0cf9e3-5b75-4d4d-9a0f-1748772b65d3')
    def test_profile_type_list(self):
        res = self.client.list_objs('profile-types')

        # Verify resp of profile type list API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        profile_types = res['body']
        expected_profile_types = [
            {'name': 'os.nova.server-1.0'},
            {'name': 'os.heat.stack-1.0'},
            {'name': 'container.dockerinc.docker-1.0'}
        ]
        for profile_type in expected_profile_types:
            self.assertIn(profile_type, profile_types)
