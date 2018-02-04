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

import types

import mock
from openstack import connection
from oslo_serialization import jsonutils
from requests import exceptions as req_exc
import six

from senlin.common import exception as senlin_exc
from senlin.drivers import sdk
from senlin.tests.unit.common import base
from senlin import version


class OpenStackSDKTest(base.SenlinTestCase):

    def setUp(self):
        super(OpenStackSDKTest, self).setUp()
        self.app_version = version.version_info.version_string()

    def test_parse_exception_http_exception_with_details(self):
        details = jsonutils.dumps({
            'error': {
                'code': 404,
                'message': 'Resource BAR is not found.'
            }
        })
        raw = sdk.exc.ResourceNotFound(message='A message', details=details,
                                       response=None, http_status=404)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(404, ex.code)
        self.assertEqual('Resource BAR is not found.', six.text_type(ex))
        # key name is not 'error' case
        details = jsonutils.dumps({
            'forbidden': {
                'code': 403,
                'message': 'Quota exceeded for instances.'
            }
        })
        raw = sdk.exc.ResourceNotFound(message='A message', details=details,
                                       http_status=403)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(403, ex.code)
        self.assertEqual('Quota exceeded for instances.', six.text_type(ex))

    def test_parse_exception_http_exception_no_details(self):
        resp = mock.Mock(headers={'x-openstack-request-id': 'FAKE_ID'})
        resp.json.return_value = {}
        resp.status_code = 404

        raw = sdk.exc.ResourceNotFound(message='A message.', details=None,
                                       response=resp, http_status=404)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(404, ex.code)
        self.assertEqual('A message.', six.text_type(ex))

    def test_parse_exception_http_exception_no_details_no_response(self):
        details = "An error message"

        raw = sdk.exc.ResourceNotFound(message='A message.', details=details,
                                       http_status=404)
        raw.details = None
        raw.response = None
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)
        self.assertEqual(404, ex.code)
        self.assertEqual('A message.', six.text_type(ex))

    def test_parse_exception_http_exception_code_displaced(self):
        details = jsonutils.dumps({
            'code': 400,
            'error': {
                'message': 'Resource BAR is in error state.'
            }
        })

        raw = sdk.exc.HttpException(
            message='A message.', details=details, http_status=400)
        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(400, ex.code)
        self.assertEqual('Resource BAR is in error state.', six.text_type(ex))

    def test_parse_exception_sdk_exception(self):
        raw = sdk.exc.InvalidResponse('INVALID')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('InvalidResponse', six.text_type(ex))

    def test_parse_exception_request_exception(self):
        raw = req_exc.HTTPError(401, 'ERROR')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(401, ex.code)
        self.assertEqual('[Errno 401] ERROR', ex.message)

    def test_parse_exception_other_exceptions(self):
        raw = Exception('Unknown Error')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('Unknown Error', six.text_type(ex))

    def test_translate_exception_wrapper(self):

        @sdk.translate_exception
        def test_func(driver):
            return driver.__name__

        res = sdk.translate_exception(test_func)
        self.assertEqual(types.FunctionType, type(res))

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

    @mock.patch.object(connection, 'Connection')
    def test_create_connection_token(self, mock_conn):
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'token': 'TOKEN', 'foo': 'bar'})

        self.assertEqual(x_conn, res)
        mock_conn.assert_called_once_with(
            app_name=sdk.USER_AGENT, app_version=self.app_version,
            identity_api_version='3',
            messaging_api_version='2',
            region_name=None,
            auth_type='token',
            token='TOKEN',
            foo='bar')

    @mock.patch.object(connection, 'Connection')
    def test_create_connection_password(self, mock_conn):
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'user_id': '123', 'password': 'abc',
                                     'foo': 'bar'})

        self.assertEqual(x_conn, res)
        mock_conn.assert_called_once_with(
            app_name=sdk.USER_AGENT, app_version=self.app_version,
            identity_api_version='3',
            messaging_api_version='2',
            region_name=None,
            user_id='123',
            password='abc',
            foo='bar')

    @mock.patch.object(connection, 'Connection')
    def test_create_connection_with_region(self, mock_conn):
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'region_name': 'REGION_ONE'})

        self.assertEqual(x_conn, res)
        mock_conn.assert_called_once_with(
            app_name=sdk.USER_AGENT, app_version=self.app_version,
            identity_api_version='3',
            messaging_api_version='2',
            region_name='REGION_ONE')

    @mock.patch.object(connection, 'Connection')
    @mock.patch.object(sdk, 'parse_exception')
    def test_create_connection_with_exception(self, mock_parse, mock_conn):
        ex_raw = Exception('Whatever')
        mock_conn.side_effect = ex_raw
        mock_parse.side_effect = senlin_exc.InternalError(code=123,
                                                          message='BOOM')

        ex = self.assertRaises(senlin_exc.InternalError,
                               sdk.create_connection)

        mock_conn.assert_called_once_with(
            app_name=sdk.USER_AGENT, app_version=self.app_version,
            identity_api_version='3',
            messaging_api_version='2',
            region_name=None)
        mock_parse.assert_called_once_with(ex_raw)
        self.assertEqual(123, ex.code)
        self.assertEqual('BOOM', ex.message)

    @mock.patch.object(sdk, 'create_connection')
    def test_authenticate(self, mock_conn):
        x_conn = mock_conn.return_value
        x_conn.session.get_token.return_value = 'TOKEN'
        x_conn.session.get_user_id.return_value = 'test-user-id'
        x_conn.session.get_project_id.return_value = 'test-project-id'
        access_info = {
            'token': 'TOKEN',
            'user_id': 'test-user-id',
            'project_id': 'test-project-id'
        }

        res = sdk.authenticate(foo='bar')

        self.assertEqual(access_info, res)
        mock_conn.assert_called_once_with({'foo': 'bar'})
