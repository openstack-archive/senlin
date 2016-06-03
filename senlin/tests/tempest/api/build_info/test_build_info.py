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


class TestBuildInfo(base.BaseSenlinTest):

    @decorators.idempotent_id('bf7a8bdf-d896-49ff-a7a8-7c8fdbfc3667')
    def test_build_info_get(self):
        uri = '{0}/build-info'.format(self.client.version)
        resp, info = self.client.get(uri)

        # Verify resp of get build-info API
        self.assertEqual(200, int(resp['status']))
        self.assertIsNotNone(info)
        for key in ['api', 'engine']:
            self.assertIn(key, info)
