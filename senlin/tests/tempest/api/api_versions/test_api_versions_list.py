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


class TestAPIVersions(base.BaseSenlinAPITest):

    @decorators.idempotent_id('c7378a80-9a82-4148-937d-25e046c6316f')
    def test_API_versions_list(self):
        resp, body = self.client.request('GET', '/')
        res = self.client.get_resp(resp, body)

        # Verify resp of API versions list
        self.assertEqual(300, res['status'])
        self.assertIsNotNone(res['body'])
        versions = res['body']
        for version in versions:
            for key in ['id', 'links', 'max_version', 'media-types',
                        'min_version', 'status', 'updated']:
                self.assertIn(key, version)
        # Only version 1.0 API is now supported
        self.assertEqual(1, len(versions))
        self.assertEqual('1.0', versions[0]['id'])
