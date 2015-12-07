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

import os
import testtools

from senlin.tests.functional.common import client


class SenlinFunctionalTest(testtools.TestCase):

    def setUp(self):
        super(SenlinFunctionalTest, self).setUp()
        self.username = os.getenv('OS_USERNAME')
        self.password = os.getenv('OS_PASSWORD')
        self.project_name = (os.getenv('OS_TENANT_NAME') or
                             os.getenv('OS_PROJECT_NAME'))
        self.user_domain_name = os.getenv('OS_USER_DOMAIN_NAME',
                                          'Default')
        self.project_domain_name = os.getenv('OS_PROJECT_DOMAIN_NAME',
                                             'Default')
        self.region_name = os.getenv('OS_REGION_NAME', 'RegionOne')
        self.auth_url = os.getenv('OS_AUTH_URL')
        self.client = client.TestSenlinAPIClient(self.username,
                                                 self.password,
                                                 self.project_name,
                                                 self.user_domain_name,
                                                 self.project_domain_name,
                                                 self.region_name,
                                                 self.auth_url)
