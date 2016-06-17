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
from tempest.lib import exceptions

from senlin.tests.tempest.api import base


class TestAPIVersionShowNegative(base.BaseSenlinAPITest):

    @decorators.idempotent_id('a3b02638-2459-41ab-a70b-a6f1a269914e')
    def test_API_version_show_invalid_version(self):
        resp, body = self.client.request('GET', '/v1/')
        self.assertRaises(exceptions.NotFound,
                          self.client.request,
                          'GET', '/vx')
