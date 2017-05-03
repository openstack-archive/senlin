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

import mock

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.api.openstack.v1 import version
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


class FakeRequest(wsgi.Request):

    @staticmethod
    def blank(*args, **kwargs):
        kwargs['base_url'] = 'http://localhost/v1'
        version = kwargs.pop('version', wsgi.DEFAULT_API_VERSION)
        out = wsgi.Request.blank(*args, **kwargs)
        out.version_request = vr.APIVersionRequest(version)
        return out


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
            'href': '/v1',
            'rel': 'self'}, {
            'href': 'https://developer.openstack.org/api-ref/clustering',
            'rel': 'help',
        }]
        self.assertEqual(expected, response['links'])


class APIVersionTest(base.SenlinTestCase):

    def setUp(self):
        super(APIVersionTest, self).setUp()
        self.vc = version.VersionController

    def test_min_api_version(self):
        res = self.vc.min_api_version()
        expected = vr.APIVersionRequest(self.vc._MIN_API_VERSION)
        self.assertEqual(expected, res)

    def test_max_api_version(self):
        res = self.vc.max_api_version()
        expected = vr.APIVersionRequest(self.vc._MAX_API_VERSION)
        self.assertEqual(expected, res)

    def test_is_supported(self):
        req = mock.Mock()
        req.version_request = vr.APIVersionRequest(self.vc._MIN_API_VERSION)
        res = self.vc.is_supported(req)
        self.assertTrue(res)

    def test_is_supported_min_version(self):
        req = FakeRequest.blank('/fake', version='1.1')

        self.assertTrue(self.vc.is_supported(req, '1.0', '1.1'))
        self.assertTrue(self.vc.is_supported(req, '1.1', '1.1'))
        self.assertFalse(self.vc.is_supported(req, '1.2'))
        self.assertFalse(self.vc.is_supported(req, '1.3'))

    def test_is_supported_max_version(self):
        req = FakeRequest.blank('/fake', version='2.5')

        self.assertFalse(self.vc.is_supported(req, max_ver='2.4'))
        self.assertTrue(self.vc.is_supported(req, max_ver='2.5'))
        self.assertTrue(self.vc.is_supported(req, max_ver='2.6'))

    def test_is_supported_min_and_max_version(self):
        req = FakeRequest.blank('/fake', version='2.5')

        self.assertFalse(self.vc.is_supported(req, '2.3', '2.4'))
        self.assertTrue(self.vc.is_supported(req, '2.3', '2.5'))
        self.assertTrue(self.vc.is_supported(req, '2.3', '2.7'))
        self.assertTrue(self.vc.is_supported(req, '2.5', '2.7'))
        self.assertFalse(self.vc.is_supported(req, '2.6', '2.7'))
        self.assertTrue(self.vc.is_supported(req, '2.5', '2.5'))
        self.assertFalse(self.vc.is_supported(req, '2.10', '2.1'))
