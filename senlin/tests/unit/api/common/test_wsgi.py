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

import socket

import fixtures
import mock
from oslo_config import cfg
from oslo_utils import encodeutils
import six
import webob

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.common import exception
from senlin.tests.unit.common import base

CONF = cfg.CONF


class RequestTest(base.SenlinTestCase):

    def test_content_type_missing(self):
        request = wsgi.Request.blank('/tests/123')
        self.assertRaises(exception.InvalidContentType,
                          request.get_content_type, ('application/xml'))

    def test_content_type_unsupported(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Content-Type"] = "text/html"
        self.assertRaises(exception.InvalidContentType,
                          request.get_content_type, ('application/xml'))

    def test_content_type_with_charset(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Content-Type"] = "application/json; charset=UTF-8"
        result = request.get_content_type(('application/json'))
        self.assertEqual("application/json", result)

    def test_content_type_from_accept_xml(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = "application/xml"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_accept_json(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = "application/json"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_accept_xml_json(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = "application/xml, application/json"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_accept_json_xml_quality(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = ("application/json; q=0.3, "
                                     "application/xml; q=0.9")
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_accept_default(self):
        request = wsgi.Request.blank('/tests/123.unsupported')
        request.headers["Accept"] = "application/unsupported1"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)


class ResourceTest(base.SenlinTestCase):

    def test_get_action_args(self):
        env = {
            'wsgiorg.routing_args': [
                None,
                {
                    'controller': None,
                    'format': None,
                    'action': 'update',
                    'id': 12,
                },
            ],
        }

        expected = {'action': 'update', 'id': 12}
        actual = wsgi.Resource(None).get_action_args(env)

        self.assertEqual(expected, actual)

    def test_get_action_args_invalid_index(self):
        env = {'wsgiorg.routing_args': []}
        expected = {}
        actual = wsgi.Resource(None).get_action_args(env)
        self.assertEqual(expected, actual)

    def test_get_action_args_del_controller_error(self):
        actions = {'format': None,
                   'action': 'update',
                   'id': 12}
        env = {'wsgiorg.routing_args': [None, actions]}
        expected = {'action': 'update', 'id': 12}
        actual = wsgi.Resource(None).get_action_args(env)
        self.assertEqual(expected, actual)

    def test_get_action_args_del_format_error(self):
        actions = {'action': 'update', 'id': 12}
        env = {'wsgiorg.routing_args': [None, actions]}
        expected = {'action': 'update', 'id': 12}
        actual = wsgi.Resource(None).get_action_args(env)
        self.assertEqual(expected, actual)

    def test_dispatch(self):
        class Controller(object):
            def index(self, shirt, pants=None):
                return (shirt, pants)

        resource = wsgi.Resource(None)
        actual = resource.dispatch(Controller(), 'index', 'on', pants='off')
        expected = ('on', 'off')
        self.assertEqual(expected, actual)

    def test_dispatch_default(self):
        class Controller(object):
            def default(self, shirt, pants=None):
                return (shirt, pants)

        resource = wsgi.Resource(None)
        actual = resource.dispatch(Controller(), 'index', 'on', pants='off')
        expected = ('on', 'off')
        self.assertEqual(expected, actual)

    def test_dispatch_no_default(self):
        class Controller(object):
            def show(self, shirt, pants=None):
                return (shirt, pants)

        resource = wsgi.Resource(None)
        self.assertRaises(AttributeError, resource.dispatch, Controller(),
                          'index', 'on', pants='off')

    def test_resource_call_error_handle(self):
        class Controller(object):
            def delete(self, req, identity):
                return (req, identity)

        actions = {'action': 'delete', 'id': 12, 'body': 'data'}
        env = {'wsgiorg.routing_args': [None, actions]}
        request = wsgi.Request.blank('/tests/123', environ=env)
        request.body = encodeutils.safe_encode('{"foo" : "value"}')
        resource = wsgi.Resource(Controller())

        # The Resource does not throw webob.HTTPExceptions, since they
        # would be considered responses by wsgi and the request flow would end,
        # instead they are wrapped so they can reach the fault application
        # where they are converted to a JSON response
        e = self.assertRaises(exception.HTTPExceptionDisguise,
                              resource, request)
        self.assertIsInstance(e.exc, webob.exc.HTTPBadRequest)

    @mock.patch.object(wsgi, 'translate_exception')
    def test_resource_call_error_handle_localized(self, mock_translate):
        class Controller(object):
            def delete(self, req, identity):
                return (req, identity)

        def fake_translate_exception(ex, locale):
            return translated_ex

        mock_translate.side_effect = fake_translate_exception
        actions = {'action': 'delete', 'id': 12, 'body': 'data'}
        env = {'wsgiorg.routing_args': [None, actions]}
        request = wsgi.Request.blank('/tests/123', environ=env)
        request.body = encodeutils.safe_encode('{"foo" : "value"}')
        message_es = "No Encontrado"
        translated_ex = webob.exc.HTTPBadRequest(message_es)

        resource = wsgi.Resource(Controller())

        e = self.assertRaises(exception.HTTPExceptionDisguise,
                              resource, request)
        self.assertEqual(message_es, six.text_type(e.exc))

    def test_resource_call_with_version_header(self):
        class Controller(object):
            def dance(self, req):
                return {'foo': 'bar'}

        actions = {'action': 'dance'}
        env = {'wsgiorg.routing_args': [None, actions]}
        request = wsgi.Request.blank('/tests/123', environ=env)
        request.version_request = vr.APIVersionRequest('1.0')

        resource = wsgi.Resource(Controller())
        resp = resource(request)
        self.assertEqual('{"foo": "bar"}', encodeutils.safe_decode(resp.body))
        self.assertTrue(hasattr(resp, 'headers'))
        expected = 'clustering 1.0'
        self.assertEqual(expected, resp.headers['OpenStack-API-Version'])
        self.assertEqual('OpenStack-API-Version', resp.headers['Vary'])


class ControllerTest(base.SenlinTestCase):

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_init(self, mock_client):
        x_client = mock.Mock()
        mock_client.return_value = x_client
        data = mock.Mock()

        c = wsgi.Controller(data)

        self.assertEqual(data, c.options)
        self.assertEqual(x_client, c.rpc_client)

    def test_default(self):
        data = mock.Mock()
        c = wsgi.Controller(data)

        self.assertRaises(webob.exc.HTTPNotFound, c.default, mock.Mock())


class ResourceExceptionHandlingTest(base.SenlinTestCase):
    scenarios = [
        ('client_exceptions', dict(
            exception=exception.NotAuthenticated,
            exception_catch=exception.NotAuthenticated)),
        ('webob_bad_request', dict(
            exception=webob.exc.HTTPBadRequest,
            exception_catch=exception.HTTPExceptionDisguise)),
        ('webob_not_found', dict(
            exception=webob.exc.HTTPNotFound,
            exception_catch=exception.HTTPExceptionDisguise)),
    ]

    def test_resource_client_exceptions_dont_log_error(self):
        class Controller(object):
            def __init__(self, excpetion_to_raise):
                self.excpetion_to_raise = excpetion_to_raise

            def raise_exception(self, req, body):
                raise self.excpetion_to_raise()
        actions = {'action': 'raise_exception', 'body': 'data'}
        env = {'wsgiorg.routing_args': [None, actions]}
        request = wsgi.Request.blank('/tests/123', environ=env)
        request.body = encodeutils.safe_encode('{"foo": "value"}')
        resource = wsgi.Resource(Controller(self.exception))
        e = self.assertRaises(self.exception_catch, resource, request)
        e = e.exc if hasattr(e, 'exc') else e
        self.assertNotIn(six.text_type(e), self.LOG.output)


class GetSocketTestCase(base.SenlinTestCase):

    def setUp(self):
        super(GetSocketTestCase, self).setUp()
        self.useFixture(fixtures.MonkeyPatch(
            "senlin.api.common.wsgi.get_bind_addr",
            lambda x, y: ('192.168.0.13', 1234)))
        addr_info_list = [(2, 1, 6, '', ('192.168.0.13', 80)),
                          (2, 2, 17, '', ('192.168.0.13', 80)),
                          (2, 3, 0, '', ('192.168.0.13', 80))]
        self.useFixture(fixtures.MonkeyPatch(
            "senlin.api.common.wsgi.socket.getaddrinfo",
            lambda *x: addr_info_list))
        self.useFixture(fixtures.MonkeyPatch(
            "senlin.api.common.wsgi.time.time",
            mock.Mock(side_effect=[0, 1, 5, 10, 20, 35])))
        wsgi.cfg.CONF.senlin_api.cert_file = '/etc/ssl/cert'
        wsgi.cfg.CONF.senlin_api.key_file = '/etc/ssl/key'
        wsgi.cfg.CONF.senlin_api.ca_file = '/etc/ssl/ca_cert'
        wsgi.cfg.CONF.senlin_api.tcp_keepidle = 600

    def test_correct_configure_socket(self):
        mock_socket = mock.Mock()
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.api.common.wsgi.ssl.wrap_socket',
            mock_socket))
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.api.common.wsgi.eventlet.listen',
            lambda *x, **y: mock_socket))
        server = wsgi.Server(name='senlin-api', conf=cfg.CONF.senlin_api)
        server.default_port = 1234
        server.configure_socket()
        self.assertIn(mock.call.setsockopt(socket.SOL_SOCKET,
                                           socket.SO_REUSEADDR, 1),
                      mock_socket.mock_calls)
        self.assertIn(mock.call.setsockopt(socket.SOL_SOCKET,
                                           socket.SO_KEEPALIVE, 1),
                      mock_socket.mock_calls)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            self.assertIn(mock.call().setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPIDLE,
                wsgi.cfg.CONF.senlin_api.tcp_keepidle), mock_socket.mock_calls)

    def test_get_socket_without_all_ssl_reqs(self):
        wsgi.cfg.CONF.senlin_api.key_file = None
        self.assertRaises(RuntimeError,
                          wsgi.get_socket, wsgi.cfg.CONF.senlin_api, 1234)

    def test_get_socket_with_bind_problems(self):
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.api.common.wsgi.eventlet.listen',
            mock.Mock(side_effect=(
                [wsgi.socket.error(socket.errno.EADDRINUSE)] * 3 + [None]))))
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.api.common.wsgi.ssl.wrap_socket',
            lambda *x, **y: None))

        self.assertRaises(RuntimeError,
                          wsgi.get_socket, wsgi.cfg.CONF.senlin_api, 1234)

    def test_get_socket_with_unexpected_socket_errno(self):
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.api.common.wsgi.eventlet.listen',
            mock.Mock(side_effect=wsgi.socket.error(socket.errno.ENOMEM))))
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.api.common.wsgi.ssl.wrap_socket',
            lambda *x, **y: None))
        self.assertRaises(wsgi.socket.error, wsgi.get_socket,
                          wsgi.cfg.CONF.senlin_api, 1234)


class FakeController(wsgi.Controller):

    @wsgi.Controller.api_version('2.0')
    def index(self, req):
        return {'foo': 'bar'}

    def foo(self, req):
        return {'bar': 'zoo'}

    @wsgi.Controller.api_version('2.0', '3.0')
    def dance(self, req):
        return {'score': 100}

    @wsgi.Controller.api_version('4.0')   # noqa
    def dance(self, req):
        return {'score': 60}


class MicroversionTest(base.SenlinTestCase):

    def test_versioned_request_empty(self):
        data = mock.Mock()
        request = wsgi.Request.blank('/tests/123')
        request.version_request = vr.APIVersionRequest('1.0')
        c = FakeController(data)

        ex = self.assertRaises(exception.MethodVersionNotFound,
                               c.index, request)
        self.assertEqual("API version '1.0' is not supported on "
                         "this method.", six.text_type(ex))

        res = c.foo(request)
        self.assertEqual({'bar': 'zoo'}, res)

        ex = self.assertRaises(exception.MethodVersionNotFound,
                               c.dance, request)
        self.assertEqual("API version '1.0' is not supported on "
                         "this method.", six.text_type(ex))

    def test_versioned_request_lower(self):
        data = mock.Mock()
        request = wsgi.Request.blank('/tests/123')
        request.version_request = vr.APIVersionRequest('2.0')
        c = FakeController(data)

        res = c.index(request)
        self.assertEqual({'foo': 'bar'}, res)

        res = c.foo(request)
        self.assertEqual({'bar': 'zoo'}, res)

        res = c.dance(request)
        self.assertEqual({'score': 100}, res)

    def test_versioned_request_middle(self):
        data = mock.Mock()
        request = wsgi.Request.blank('/tests/123')
        request.version_request = vr.APIVersionRequest('2.5')
        c = FakeController(data)

        res = c.index(request)
        self.assertEqual({'foo': 'bar'}, res)

        res = c.foo(request)
        self.assertEqual({'bar': 'zoo'}, res)

        res = c.dance(request)
        self.assertEqual({'score': 100}, res)

    def test_versioned_request_upper(self):
        data = mock.Mock()
        request = wsgi.Request.blank('/tests/123')
        request.version_request = vr.APIVersionRequest('3.0')
        c = FakeController(data)

        res = c.index(request)
        self.assertEqual({'foo': 'bar'}, res)

        res = c.foo(request)
        self.assertEqual({'bar': 'zoo'}, res)

        res = c.dance(request)
        self.assertEqual({'score': 100}, res)

    def test_versioned_request_too_high(self):
        data = mock.Mock()
        request = wsgi.Request.blank('/tests/123')
        request.version_request = vr.APIVersionRequest('3.5')
        c = FakeController(data)

        res = c.index(request)
        self.assertEqual({'foo': 'bar'}, res)

        res = c.foo(request)
        self.assertEqual({'bar': 'zoo'}, res)

        ex = self.assertRaises(exception.MethodVersionNotFound,
                               c.dance, request)
        self.assertEqual("API version '3.5' is not supported on "
                         "this method.", six.text_type(ex))

    def test_versioned_request_inner_functions(self):
        data = mock.Mock()
        request = wsgi.Request.blank('/tests/123')
        request.version_request = vr.APIVersionRequest('3.0')
        c = FakeController(data)

        res = c.dance(request)
        self.assertEqual({'score': 100}, res)

        request.version_request = vr.APIVersionRequest('4.0')
        res = c.dance(request)
        self.assertEqual({'score': 60}, res)
