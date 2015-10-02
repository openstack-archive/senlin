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
from openstack import connection
from openstack import profile
from openstack import transport
from oslo_serialization import jsonutils
from requests import exceptions as req_exc
import six

from senlin.common import exception as senlin_exc
from senlin.drivers.openstack import sdk
from senlin.tests.unit.common import base


class OpenStackSDKTest(base.SenlinTestCase):

    def setUp(self):
        super(OpenStackSDKTest, self).setUp()

    def test_parser_exception_http_exception_with_details(self):
        details = jsonutils.dumps({
            'error': {
                'code': 404,
                'message': 'Resource BAR is not found.'
            }
        })
        raw = sdk.exc.ResourceNotFound('A message', details, 404)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(404, ex.code)
        self.assertEqual('Resource BAR is not found.', six.text_type(ex))

    def test_parser_exception_http_exception_no_details(self):
        details = "An error message"

        raw = sdk.exc.ResourceNotFound('A message.', details, 404)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(404, ex.code)
        self.assertEqual('A message.', six.text_type(ex))

    def test_parser_exception_http_exception_code_displaced(self):
        details = jsonutils.dumps({
            'code': 400,
            'error': {
                'message': 'Resource BAR is in error state.'
            }
        })

        raw = sdk.exc.HttpException('A message.', details)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(400, ex.code)
        self.assertEqual('Resource BAR is in error state.', six.text_type(ex))

    def test_parser_exception_sdk_exception(self):
        raw = sdk.exc.AuthorizationFailure()

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('AuthorizationFailure', six.text_type(ex))

    def test_parser_exception_request_exception(self):
        raw = req_exc.HTTPError(401, 'ERROR')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(401, ex.code)
        self.assertEqual('[Errno 401] ERROR', ex.message)

    def test_parser_exception_other_exceptions(self):
        raw = Exception('Unknown Error')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('Unknown Error', six.text_type(ex))

    def test_translate_exception_wrapper(self):

        test_func = mock.Mock()
        test_func.__name__ = 'test_func'

        res = sdk.translate_exception(test_func)
        self.assertEqual('function', res.__class__.__name__)

    def test_translate_exception_with_exception(self):

        @sdk.translate_exception
        def test_func(driver):
            raise(Exception('test exception'))

        error = senlin_exc.InternalError(code=500, message='BOOM')
        self.patchobject(sdk, 'parse_exception', side_effect=error)
        ex = self.assertRaises(senlin_exc.InternalError,
                               test_func, mock.Mock())

        self.assertEqual(500, ex.code)
        self.assertEqual('BOOM', ex.message)

    @mock.patch.object(profile, 'Profile')
    @mock.patch.object(connection, 'Connection')
    def test_create_connection(self, mock_conn, mock_profile):
        x_profile = mock.Mock()
        mock_profile.return_value = x_profile
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'foo': 'bar'})

        self.assertEqual(x_conn, res)
        mock_profile.assert_called_once_with()
        mock_conn.assert_called_once_with(profile=x_profile,
                                          user_agent=sdk.USER_AGENT,
                                          foo='bar')

    @mock.patch.object(profile, 'Profile')
    @mock.patch.object(connection, 'Connection')
    def test_create_connection_with_region(self, mock_conn, mock_profile):
        x_profile = mock.Mock()
        mock_profile.return_value = x_profile
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'region_name': 'REGION_ONE'})

        self.assertEqual(x_conn, res)
        mock_profile.assert_called_once_with()
        x_profile.set_region.assert_called_once_with(x_profile.ALL,
                                                     'REGION_ONE')
        mock_conn.assert_called_once_with(profile=x_profile,
                                          user_agent=sdk.USER_AGENT)

    @mock.patch.object(profile, 'Profile')
    @mock.patch.object(connection, 'Connection')
    @mock.patch.object(sdk, 'parse_exception')
    def test_create_connection_with_exception(self, mock_parse, mock_conn,
                                              mock_profile):
        x_profile = mock.Mock()
        mock_profile.return_value = x_profile
        ex_raw = Exception('Whatever')
        mock_conn.side_effect = ex_raw
        mock_parse.side_effect = senlin_exc.InternalError(code=123,
                                                          message='BOOM')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.create_connection)

        mock_profile.assert_called_once_with()
        mock_conn.assert_called_once_with(profile=x_profile,
                                          user_agent=sdk.USER_AGENT)
        mock_parse.assert_called_once_with(ex_raw)
        self.assertEqual(123, ex.code)
        self.assertEqual('BOOM', ex.message)

    @mock.patch.object(sdk, 'create_connection')
    @mock.patch.object(transport, 'Transport')
    def test_authenticate(self, mock_transport, mock_conn):
        x_conn = mock_conn.return_value
        x_auth = x_conn.session.authenticator
        x_transport = mock_transport.return_value
        x_access_info = mock.Mock()
        mock_authorize = mock.Mock(return_value=x_access_info)
        x_auth.authorize = mock_authorize

        res = sdk.authenticate(foo='bar')

        self.assertEqual(x_access_info, res)
        mock_conn.assert_called_once_with({'foo': 'bar'})
        mock_transport.assert_called_once_with()
        mock_authorize.assert_called_once_with(x_transport)

    @mock.patch.object(sdk, 'create_connection')
    @mock.patch.object(transport, 'Transport')
    @mock.patch.object(sdk, 'parse_exception')
    def test_authenticate_with_exception(self, mock_parse, mock_transport,
                                         mock_conn):
        x_conn = mock_conn.return_value
        x_auth = x_conn.session.authenticator
        x_transport = mock_transport.return_value
        error = Exception('test exception')
        x_auth.authorize.side_effect = error
        mock_parse.side_effect = senlin_exc.InternalError(code=123,
                                                          message='BOOM')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.authenticate, foo='bar')

        mock_conn.assert_called_once_with({'foo': 'bar'})
        mock_transport.assert_called_once_with()
        x_auth.authorize.assert_called_once_with(x_transport)
        mock_parse.assert_called_once_with(error)
        self.assertEqual(123, ex.code)
        self.assertEqual('BOOM', ex.message)
