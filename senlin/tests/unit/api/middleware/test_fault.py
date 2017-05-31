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

import inspect
import re
import six
import webob

from oslo_config import cfg
from oslo_log import log
from oslo_messaging._drivers import common as rpc_common

import senlin.api.middleware.fault as fault
from senlin.common import exception as senlin_exc
from senlin.tests.unit.common import base


class ClusterNotFoundChild(senlin_exc.ResourceNotFound):
    pass


class ErrorWithNewline(webob.exc.HTTPBadRequest):
    pass


class FaultMiddlewareTest(base.SenlinTestCase):
    def setUp(self):
        super(FaultMiddlewareTest, self).setUp()
        log.register_options(cfg.CONF)

    def test_disguised_http_exception_with_newline(self):
        wrapper = fault.FaultWrapper(None)
        newline_error = ErrorWithNewline('Error with \n newline')
        msg = wrapper._error(senlin_exc.HTTPExceptionDisguise(newline_error))
        expected = {
            'code': 400,
            'error': {
                'code': 400,
                'message': 'Error with \n newline',
                'type': 'ErrorWithNewline'
            },
            'explanation': 'The server could not comply with the request '
                           'since it is either malformed or otherwise '
                           'incorrect.',
            'title': 'Bad Request'
        }
        self.assertEqual(expected, msg)

    def test_openstack_exception_with_kwargs(self):
        wrapper = fault.FaultWrapper(None)
        msg = wrapper._error(senlin_exc.ResourceNotFound(type='cluster',
                                                         id='a'))

        expected = {
            "code": 404,
            "error": {
                "code": 404,
                "message": "The cluster 'a' could not be found.",
                "type": "ResourceNotFound"
            },
            "explanation": "The resource could not be found.",
            "title": "Not Found"
        }
        self.assertEqual(expected, msg)

    def test_openstack_exception_without_kwargs(self):
        wrapper = fault.FaultWrapper(None)
        msg = wrapper._error(senlin_exc.PolicyNotSpecified())
        expected = {
            'code': 500,
            'error': {
                'code': 500,
                'message': 'Policy not specified.',
                'type': 'PolicyNotSpecified'
            },
            'explanation': 'The server has either erred or is incapable of '
                           'performing the requested operation.',
            'title': 'Internal Server Error'
        }
        self.assertEqual(expected, msg)

    def test_exception_with_non_ascii_chars(self):
        # We set debug to true to test the code path for serializing traces too
        cfg.CONF.set_override('debug', True)
        msg = u'Error with non-ascii chars \x80'

        class TestException(senlin_exc.SenlinException):
            msg_fmt = msg

        wrapper = fault.FaultWrapper(None)
        msg = wrapper._error(TestException())

        self.assertEqual(500, msg['code'])
        self.assertEqual(500, msg['error']['code'])
        self.assertEqual(u'Error with non-ascii chars \x80',
                         msg['error']['message'])
        self.assertEqual('TestException', msg['error']['type'])
        self.assertEqual('The server has either erred or is incapable of '
                         'performing the requested operation.',
                         msg['explanation'])
        self.assertEqual('Internal Server Error', msg['title'])

    def test_remote_exception(self):
        cfg.CONF.set_override('debug', True)
        error = senlin_exc.ResourceNotFound(type='cluster', id='a')
        exc_info = (type(error), error, None)
        serialized = rpc_common.serialize_remote_exception(exc_info)
        remote_error = rpc_common.deserialize_remote_exception(
            serialized, ["senlin.common.exception"])
        wrapper = fault.FaultWrapper(None)
        msg = wrapper._error(remote_error)
        expected_message = six.text_type(remote_error).split('\n', 1)[0]
        expected = {
            'code': 404,
            'error': {
                'code': 404,
                'message': expected_message,
                'type': 'ResourceNotFound'
            },
            'explanation': 'The resource could not be found.',
            'title': 'Not Found'
        }
        self.assertEqual(expected, msg)

    def remote_exception_helper(self, name, error):
        exc_info = (type(error), error, None)

        serialized = rpc_common.serialize_remote_exception(exc_info)
        remote_error = rpc_common.deserialize_remote_exception(
            serialized, name)
        wrapper = fault.FaultWrapper(None)
        msg = wrapper._error(remote_error)
        expected = {
            'code': 500,
            'error': {
                'code': 500,
                'message': msg['error']['message'],
                'type': 'RemoteError'
            },
            'explanation': msg['explanation'],
            'title': 'Internal Server Error'
        }
        self.assertEqual(expected, msg)

    def test_all_remote_exceptions(self):
        for name, obj in inspect.getmembers(
                senlin_exc, lambda x: inspect.isclass(x) and issubclass(
                    x, senlin_exc.SenlinException)):

            if '__init__' in obj.__dict__:
                if obj == senlin_exc.SenlinException:
                    continue
                elif obj == senlin_exc.Error:
                    error = obj('Error')
                elif obj == senlin_exc.ResourceNotFound:
                    error = obj()
                else:
                    continue
                self.remote_exception_helper(name, error)
                continue

            if hasattr(obj, 'msg_fmt'):
                kwargs = {}
                spec_names = re.findall('%\((\w+)\)([cdeEfFgGinorsxX])',
                                        obj.msg_fmt)

                for key, convtype in spec_names:
                    if convtype == 'r' or convtype == 's':
                        kwargs[key] = '"' + key + '"'
                    else:
                        # this is highly unlikely
                        raise Exception("test needs additional conversion"
                                        " type added due to %s exception"
                                        " using '%c' specifier" % (
                                            obj, convtype))

                error = obj(**kwargs)
                self.remote_exception_helper(name, error)

    def test_should_not_ignore_parent_classes(self):
        wrapper = fault.FaultWrapper(None)

        msg = wrapper._error(ClusterNotFoundChild(type='cluster', id='a'))
        expected = {
            "code": 404,
            "error": {
                "code": 404,
                "message": "The cluster 'a' could not be found.",
                "type": "ClusterNotFoundChild"
            },
            "explanation": "The resource could not be found.",
            "title": "Not Found"
        }
        self.assertEqual(expected, msg)

    def test_internal_server_error_when_exception_and_parents_not_mapped(self):
        wrapper = fault.FaultWrapper(None)

        class NotMappedException(Exception):
            pass

        msg = wrapper._error(NotMappedException('A message'))
        expected = {
            "code": 500,
            "error": {
                "code": 500,
                "message": "A message",
                "type": "NotMappedException"
            },
            "explanation": ("The server has either erred or is incapable "
                            "of performing the requested operation."),
            "title": "Internal Server Error"
        }
        self.assertEqual(expected, msg)

    def test_should_not_ignore_parent_classes_even_for_remote_ones(self):
        cfg.CONF.set_override('debug', True)

        error = ClusterNotFoundChild(type='cluster', id='a')
        exc_info = (type(error), error, None)
        serialized = rpc_common.serialize_remote_exception(exc_info)
        remote_error = rpc_common.deserialize_remote_exception(
            serialized, ["senlin.tests.unit.api.middleware.test_fault"])

        wrapper = fault.FaultWrapper(None)
        msg = wrapper._error(remote_error)
        expected_message = six.text_type(remote_error).split('\n', 1)[0]
        expected = {
            'code': 404,
            'error': {
                'code': 404,
                'message': expected_message,
                'type': 'ClusterNotFoundChild'
            },
            'explanation': 'The resource could not be found.',
            'title': 'Not Found'
        }
        self.assertEqual(expected, msg)
