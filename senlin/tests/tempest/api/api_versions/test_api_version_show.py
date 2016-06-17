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


class TestAPIVersionShow(base.BaseSenlinAPITest):

    @decorators.idempotent_id('4a270caa-9917-4acd-98ef-6636f9618037')
    def test_API_version_show(self):
        resp, body = self.client.request('GET', '/v1/')
        res = self.client._parsed_resp(resp, body)

        # Verify resp of API version show
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        version = res['body']
        for key in ['id', 'links', 'media-types', 'status', 'updated']:
            self.assertIn(key, version)
        self.assertEqual('1.0', version['id'])
