# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from senlin.api.openstack.v1 import version
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


class VersionControllerTest(shared.ControllerTest, base.SenlinTestCase):

    def setUp(self):
        super(VersionControllerTest, self).setUp()
        self.controller = version.VersionController({})

    def test_version(self):
        req = self._get('/')

        result = self.controller.version(req)

        response = result['version']
        self.assertEqual('1.0', response['id'])
        self.assertEqual('CURRENT', response['status'])
        self.assertEqual('2016-01-18T00:00:00Z', response['updated'])
        expected = [{
            'base': 'application/json',
            'type': 'application/vnd.openstack.clustering-v1+json'
        }]
        self.assertEqual(expected, response['media-types'])
        expected = [{
            'href': '.',
            'rel': 'self'
        }]
        self.assertEqual(expected, response['links'])
