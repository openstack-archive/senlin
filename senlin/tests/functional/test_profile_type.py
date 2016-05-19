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

from senlin.tests.functional import base


class TestProfileType(base.SenlinFunctionalTest):

    def test_get_profile_types(self):
        # Check that listing profile types works.
        rel_url = 'profile-types'
        status = [200]
        resp = self.client.api_request('GET', rel_url, resp_status=status)
        profile_types = resp.body['profile_types']
        expected_profile_types = [
            {'name': 'os.nova.server-1.0'},
            {'name': 'os.heat.stack-1.0'},
            {'name': 'container.dockerinc.docker-1.0'}
        ]
        for profile_type in expected_profile_types:
            self.assertIn(profile_type, profile_types)
