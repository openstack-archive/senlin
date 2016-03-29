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

import six
import webob

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.api.middleware import version_negotiation as vn
from senlin.api.openstack import versions as os_ver
from senlin.common import exception
from senlin.tests.unit.common import base


class VersionController(object):
    pass


class VersionNegotiationMiddlewareTest(base.SenlinTestCase):
    def _version_controller_factory(self, conf):
        return VersionController()

    def test_match_version_string(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({})
        major = 1
        minor = 0

        match = version_negotiation._match_version_string(
            'v{0}.{1}'.format(major, minor), request)
        self.assertTrue(match)
        self.assertEqual(major, request.environ['api.major'])
        self.assertEqual(minor, request.environ['api.minor'])

    def test_not_match_version_string(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({})

        match = version_negotiation._match_version_string("invalid", request)
        self.assertFalse(match)

    def test_return_version_controller_when_request_path_is_version(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({'PATH_INFO': 'versions'})

        response = version_negotiation.process_request(request)

        self.assertIsInstance(response, VersionController)

    def test_return_version_controller_when_request_path_is_empty(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({'PATH_INFO': '/'})

        response = version_negotiation.process_request(request)

        self.assertIsInstance(response, VersionController)

    def test_request_path_contains_valid_version(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        major = 1
        minor = 0
        request = webob.Request({'PATH_INFO':
                                 'v{0}.{1}/resource'.format(major, minor)})

        response = version_negotiation.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(major, request.environ['api.major'])
        self.assertEqual(minor, request.environ['api.minor'])

    def test_removes_version_from_request_path(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        expected_path = 'resource'
        request = webob.Request({'PATH_INFO': 'v1.0/%s' % expected_path})

        response = version_negotiation.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(expected_path, request.path_info_peek())

    def test_request_path_contains_unknown_version(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({'PATH_INFO': 'v2.0/resource'})

        response = version_negotiation.process_request(request)

        self.assertIsInstance(response, VersionController)

    def test_accept_header_contains_valid_version(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        major = 1
        minor = 0
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers['Accept'] = 'application/vnd.openstack.clustering-v1.0'

        response = version_negotiation.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(major, request.environ['api.major'])
        self.assertEqual(minor, request.environ['api.minor'])

    def test_accept_header_contains_unknown_version(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers['Accept'] = 'application/vnd.openstack.clustering-v2.0'

        response = version_negotiation.process_request(request)

        self.assertIsInstance(response, VersionController)

        request.headers['Accept'] = 'application/vnd.openstack.clustering-vab'
        response = version_negotiation.process_request(request)
        self.assertIsNone(response)

    def test_no_URI_version_accept_header_contains_invalid_MIME_type(self):
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers['Accept'] = 'application/invalidMIMEType'
        response = version_negotiation.process_request(request)
        self.assertIsInstance(response, webob.exc.HTTPNotFound)

        request.headers['Accept'] = ''
        response = version_negotiation.process_request(request)
        self.assertIsInstance(response, webob.exc.HTTPNotFound)

    def test_check_version_request(self):
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'cluster 1.0,compute 2.0'
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)

        version_negotiation.check_version_request(request)
        self.assertIsNotNone(request.version_request)
        expected = vr.APIVersionRequest('1.0')
        self.assertEqual(expected, request.version_request)

    def test_check_version_request_default(self):
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'compute 2.0'
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)

        version_negotiation.check_version_request(request)
        self.assertIsNotNone(request.version_request)
        expected = vr.APIVersionRequest(wsgi.DEFAULT_API_VERSION)
        self.assertEqual(expected, request.version_request)

    def test_check_version_request_invalid_format(self):
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'cluster 2.03'
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)

        ex = self.assertRaises(webob.exc.HTTPBadRequest,
                               version_negotiation.check_version_request,
                               request)
        self.assertEqual("API Version String (2.03) is of invalid format. It "
                         "must be of format 'major.minor'.",
                         six.text_type(ex))

    def test_check_version_request_invalid_version(self):
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'cluster 2.3'
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)

        ex = self.assertRaises(exception.InvalidGlobalAPIVersion,
                               version_negotiation.check_version_request,
                               request)
        expected = ("Version 2.3 is not supported by the API. Minimum is "
                    "%(min_ver)s and maximum is %(max_ver)s." %
                    {'min_ver': str(os_ver.min_api_version()),
                     'max_ver': str(os_ver.max_api_version())})
        self.assertEqual(expected, six.text_type(ex))

    def test_check_version_request_latest(self):
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'cluster Latest'
        version_negotiation = vn.VersionNegotiationFilter(
            self._version_controller_factory, None, None)

        version_negotiation.check_version_request(request)
        self.assertIsNotNone(request.version_request)
        expected = os_ver.max_api_version()
        self.assertEqual(expected, request.version_request)
