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
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from six.moves import http_client
import webob

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.api.openstack import versions
from senlin.tests.unit.common import base


class FakeRequest(wsgi.Request):

    @staticmethod
    def blank(*args, **kwargs):
        kwargs['base_url'] = 'http://localhost/v1'
        version = kwargs.pop('version', wsgi.DEFAULT_API_VERSION)
        out = wsgi.Request.blank(*args, **kwargs)
        out.version_request = vr.APIVersionRequest(version)
        return out


class VersionControllerTest(base.SenlinTestCase):

    def test_init(self):
        conf = mock.Mock()

        controller = versions.Controller(conf)

        self.assertIsNotNone(controller)
        self.assertEqual(conf, controller.conf)

    def test_call(self):
        conf = mock.Mock()
        controller = versions.Controller(conf)
        environ = {
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'host',
            'SERVER_PORT': 8778,
            'SCRIPT_NAME': '/',
            'PATH_INFO': '/',
            'wsgi.url_scheme': 'http',
        }
        req = wsgi.Request(environ)
        expected_dict = {
            'versions': [{
                'id': '1.0',
                'status': 'CURRENT',
                'updated': '2016-01-18T00:00:00Z',
                'media-types': [{
                    'base': 'application/json',
                    'type': 'application/vnd.openstack.clustering-v1+json'

                }],
                'links': [{
                    'rel': 'self',
                    'href': '/v1/'
                }],
                'min_version': versions._MIN_API_VERSION,
                'max_version': versions._MAX_API_VERSION
            }]
        }
        expected_body = jsonutils.dumps(expected_dict)

        resp = controller(req)

        self.assertIsInstance(resp, webob.Response)
        self.assertEqual(expected_body, encodeutils.safe_decode(resp.body))
        self.assertEqual(http_client.MULTIPLE_CHOICES, resp.status_code)
        self.assertEqual('application/json', resp.content_type)


class VersionRangeTest(base.SenlinTestCase):

    def test_is_supported_min_version(self):
        req = FakeRequest.blank('/fake', version='1.1')

        self.assertTrue(versions.is_supported(req, min_version='1.0',
                                              max_version='1.1'))
        self.assertTrue(versions.is_supported(req, min_version='1.1',
                                              max_version='1.1'))
        self.assertFalse(versions.is_supported(req, min_version='1.2'))

    def test_is_supported_max_version(self):
        req = FakeRequest.blank('/fake', version='2.5')

        self.assertFalse(versions.is_supported(req, max_version='2.4'))
        self.assertTrue(versions.is_supported(req, max_version='2.5'))
        self.assertTrue(versions.is_supported(req, max_version='2.6'))

    def test_is_supported_min_and_max_version(self):
        req = FakeRequest.blank('/fake', version='2.5')

        self.assertFalse(versions.is_supported(req, min_version='2.3',
                                               max_version='2.4'))
        self.assertTrue(versions.is_supported(req, min_version='2.3',
                                              max_version='2.5'))
        self.assertTrue(versions.is_supported(req, min_version='2.3',
                                              max_version='2.7'))
        self.assertTrue(versions.is_supported(req, min_version='2.5',
                                              max_version='2.7'))
        self.assertFalse(versions.is_supported(req, min_version='2.6',
                                               max_version='2.7'))
        self.assertTrue(versions.is_supported(req, min_version='2.5',
                                              max_version='2.5'))
        self.assertFalse(versions.is_supported(req, min_version='2.10',
                                               max_version='2.1'))
