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
from senlin.tests.tempest.common import utils


class TestProfileTypeShow(base.BaseSenlinAPITest):

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('198165b3-1c1f-4801-8918-90c1adbf57c8')
    def test_profile_type_show(self):
        res = self.client.get_obj('profile-types', 'os.nova.server-1.0')

        # Verify resp of profile type show API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        profile_type = res['body']
        for key in ['name', 'schema']:
            self.assertIn(key, profile_type)
        self.assertEqual('os.nova.server-1.0', profile_type['name'])

    @utils.api_microversion('1.5')
    @decorators.idempotent_id('778d41df-0ce0-421f-98e5-2efdcec6d995')
    def test_profile_type_show_v1_5(self):
        res = self.client.get_obj('profile-types', 'os.nova.server-1.0')

        # Verify resp of profile type show API
        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        profile_type = res['body']
        for key in ['name', 'schema', 'support_status']:
            self.assertIn(key, profile_type)
        self.assertEqual('os.nova.server-1.0', profile_type['name'])
        self.assertIsNotNone(profile_type['support_status'])
