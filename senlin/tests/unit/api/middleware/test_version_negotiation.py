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
import six
import webob

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.api.middleware import version_negotiation as vn
from senlin.common import exception
from senlin.tests.unit.common import base


@mock.patch("senlin.api.openstack.versions.Controller")
class VersionNegotiationTest(base.SenlinTestCase):

    def test__get_version_controller(self, mock_vc):
        gvc = mock_vc.return_value
        xvc = mock.Mock()
        gvc.get_controller = mock.Mock(return_value=xvc)
        vnf = vn.VersionNegotiationFilter(None, None)
        request = webob.Request({})

        res = vnf._get_controller('v1.0', request)

        self.assertEqual(xvc, res)
        self.assertEqual(1, request.environ['api.major'])
        self.assertEqual(0, request.environ['api.minor'])
        gvc.get_controller.assert_called_once_with('1.0')

    def test__get_version_controller_shorter_version(self, mock_vc):
        gvc = mock_vc.return_value
        xvc = mock.Mock()
        gvc.get_controller = mock.Mock(return_value=xvc)
        vnf = vn.VersionNegotiationFilter(None, None)
        request = webob.Request({})

        res = vnf._get_controller('v1', request)

        self.assertEqual(xvc, res)
        self.assertEqual(1, request.environ['api.major'])
        self.assertEqual(0, request.environ['api.minor'])
        gvc.get_controller.assert_called_once_with('1.0')

    def test__get_controller_not_match_version(self, mock_vc):
        gvc = mock_vc.return_value
        gvc.get_controller = mock.Mock(return_value=None)
        vnf = vn.VersionNegotiationFilter(None, None)
        request = webob.Request({})

        res = vnf._get_controller("invalid", request)

        self.assertIsNone(res)
        self.assertEqual(0, gvc.get_controller.call_count)

    def test_request_path_is_version(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        request = webob.Request({'PATH_INFO': 'versions'})

        response = vnf.process_request(request)

        self.assertIs(mock_vc.return_value, response)

    def test_request_path_is_empty(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        request = webob.Request({'PATH_INFO': '/'})

        response = vnf.process_request(request)

        self.assertIs(mock_vc.return_value, response)

    def test_request_path_contains_valid_version(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        gvc = mock_vc.return_value
        x_controller = mock.Mock()
        gvc.get_controller = mock.Mock(return_value=x_controller)
        mock_check = self.patchobject(vnf, '_check_version_request')
        major = 1
        minor = 0
        request = webob.Request({'PATH_INFO': 'v1.0/resource'})

        response = vnf.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(major, request.environ['api.major'])
        self.assertEqual(minor, request.environ['api.minor'])
        gvc.get_controller.assert_called_once_with('1.0')
        mock_check.assert_called_once_with(request, x_controller)

    def test_removes_version_from_request_path(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        self.patchobject(vnf, '_check_version_request')
        expected_path = 'resource'
        request = webob.Request({'PATH_INFO': 'v1.0/%s' % expected_path})

        response = vnf.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(expected_path, request.path_info_peek())

    def test_simple_version_on_request_path(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        self.patchobject(vnf, '_check_version_request')
        fake_vc = mock.Mock(return_value={'foo': 'bar'})
        self.patchobject(vnf.versions_app, 'get_controller',
                         return_value=fake_vc)
        request = webob.Request({'PATH_INFO': 'v1'})

        response = vnf.process_request(request)

        self.assertEqual({'foo': 'bar'}, response)

    def test_full_version_on_request_path(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        self.patchobject(vnf, '_check_version_request')
        fake_vc = mock.Mock(return_value={'foo': 'bar'})
        self.patchobject(vnf.versions_app, 'get_controller',
                         return_value=fake_vc)
        request = webob.Request({'PATH_INFO': 'v1.0'})

        response = vnf.process_request(request)

        self.assertEqual({'foo': 'bar'}, response)

    def test_request_path_contains_unknown_version(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        gvc = mock_vc.return_value
        gvc.get_controller = mock.Mock(return_value=None)
        self.patchobject(vnf, '_check_version_request')

        request = webob.Request({'PATH_INFO': 'v2.0/resource'})
        request.headers['Accept'] = '*/*'

        response = vnf.process_request(request)

        self.assertIs(mock_vc.return_value, response)

    def test_accept_header_contains_valid_version(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        self.patchobject(vnf, '_check_version_request')
        major = 1
        minor = 0
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers['Accept'] = 'application/vnd.openstack.clustering-v1.0'

        response = vnf.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(major, request.environ['api.major'])
        self.assertEqual(minor, request.environ['api.minor'])

    def test_accept_header_contains_simple_version(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        self.patchobject(vnf, '_check_version_request')
        fake_vc = mock.Mock(return_value={'foo': 'bar'})
        self.patchobject(vnf.versions_app, 'get_controller',
                         return_value=fake_vc)
        major = 1
        minor = 0
        request = webob.Request({'PATH_INFO': ''})
        request.headers['Accept'] = 'application/vnd.openstack.clustering-v1.0'

        response = vnf.process_request(request)

        self.assertEqual(major, request.environ['api.major'])
        self.assertEqual(minor, request.environ['api.minor'])
        self.assertEqual({'foo': 'bar'}, response)

    def test_accept_header_contains_unknown_version(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        self.patchobject(vnf, '_check_version_request')
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers['Accept'] = 'application/vnd.openstack.clustering-v2.0'

        response = vnf.process_request(request)

        self.assertIsNone(response)

        request.headers['Accept'] = 'application/vnd.openstack.clustering-vab'
        response = vnf.process_request(request)

        self.assertIsInstance(response, webob.exc.HTTPNotFound)

    def test_no_URI_version_accept_with_invalid_MIME_type(self, mock_vc):
        vnf = vn.VersionNegotiationFilter(None, None)
        gvc = mock_vc.return_value
        gvc.get_controller = mock.Mock(side_effect=[None, None])
        self.patchobject(vnf, '_check_version_request')

        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers['Accept'] = 'application/invalidMIMEType'

        response = vnf.process_request(request)

        self.assertIsInstance(response, webob.exc.HTTPNotFound)

        request.headers['Accept'] = ''
        response = vnf.process_request(request)
        self.assertEqual(gvc, response)

    def test__check_version_request(self, mock_vc):
        controller = mock.Mock()
        minv = vr.APIVersionRequest('1.0')
        maxv = vr.APIVersionRequest('1.3')
        controller.min_api_version = mock.Mock(return_value=minv)
        controller.max_api_version = mock.Mock(return_value=maxv)

        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'clustering 1.0,compute 2.0'
        vnf = vn.VersionNegotiationFilter(None, None)

        vnf._check_version_request(request, controller)
        self.assertIsNotNone(request.version_request)
        expected = vr.APIVersionRequest('1.0')
        self.assertEqual(expected, request.version_request)

    def test__check_version_request_default(self, mock_vc):
        controller = mock.Mock()
        controller.DEFAULT_API_VERSION = "1.0"
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'compute 2.0'
        vnf = vn.VersionNegotiationFilter(None, None)

        vnf._check_version_request(request, controller)

        self.assertIsNotNone(request.version_request)
        expected = vr.APIVersionRequest(controller.DEFAULT_API_VERSION)
        self.assertEqual(expected, request.version_request)

    def test__check_version_request_invalid_format(self, mock_vc):
        controller = mock.Mock()
        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'clustering 2.03'
        vnf = vn.VersionNegotiationFilter(None, None)

        ex = self.assertRaises(webob.exc.HTTPBadRequest,
                               vnf._check_version_request,
                               request, controller)
        self.assertEqual("API Version String '2.03' is of invalid format. It "
                         "must be of format 'major.minor'.",
                         six.text_type(ex))

    def test__check_version_request_invalid_version(self, mock_vc):
        controller = mock.Mock()
        minv = vr.APIVersionRequest('1.0')
        maxv = vr.APIVersionRequest('1.100')
        controller.min_api_version = mock.Mock(return_value=minv)
        controller.max_api_version = mock.Mock(return_value=maxv)

        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'clustering 2.3'
        vnf = vn.VersionNegotiationFilter(None, None)

        ex = self.assertRaises(exception.InvalidGlobalAPIVersion,
                               vnf._check_version_request,
                               request, controller)
        expected = ("Version '2.3' is not supported by the API. Minimum is "
                    "'%(min_ver)s' and maximum is '%(max_ver)s'." %
                    {'min_ver': str(minv), 'max_ver': str(maxv)})
        self.assertEqual(expected, six.text_type(ex))

    def test__check_version_request_latest(self, mock_vc):
        controller = mock.Mock()
        controller.max_api_version = mock.Mock(return_value='12.34')

        request = webob.Request({'PATH_INFO': 'resource'})
        request.headers[wsgi.API_VERSION_KEY] = 'clustering Latest'
        vnf = vn.VersionNegotiationFilter(None, None)

        vnf._check_version_request(request, controller)

        self.assertIsNotNone(request.version_request)
        expected = '12.34'
        self.assertEqual(expected, request.version_request)
