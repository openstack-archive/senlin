# -*- coding: utf-8 -*-
#
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

'''
A middleware that turns exceptions into parsable string.
'''

import traceback

from oslo_config import cfg
import six
import webob

from senlin.common import exception
from senlin.common import serializers
from senlin.common import wsgi


class Fault(object):

    def __init__(self, error):
        self.error = error

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        serializer = serializers.JSONResponseSerializer()
        resp = webob.Response(request=req)
        default_webob_exc = webob.exc.HTTPInternalServerError()
        resp.status_code = self.error.get('code', default_webob_exc.code)
        serializer.default(resp, self.error)
        return resp


class FaultWrapper(wsgi.Middleware):
    """Replace error body with something the client can parse."""

    error_map = {
        'ActionInProgress': webob.exc.HTTPConflict,
        'ActionNotFound': webob.exc.HTTPNotFound,
        'ClusterNotFound': webob.exc.HTTPNotFound,
        'EventNotFound': webob.exc.HTTPNotFound,
        'FeatureNotSupported': webob.exc.HTTPConflict,
        'Forbidden': webob.exc.HTTPForbidden,
        'InternalError': webob.exc.HTTPInternalServerError,
        'InvalidParameter': webob.exc.HTTPBadRequest,
        'InvalidSchemaError': webob.exc.HTTPBadRequest,
        'MultipleChoices': webob.exc.HTTPBadRequest,
        'NodeNotFound': webob.exc.HTTPNotFound,
        'NodeNotOrphan': webob.exc.HTTPConflict,
        'PolicyBindingNotFound': webob.exc.HTTPNotFound,
        'PolicyNotFound': webob.exc.HTTPNotFound,
        'PolicyTypeNotFound': webob.exc.HTTPNotFound,
        'ProfileInUse': webob.exc.HTTPConflict,
        'ProfileNotFound': webob.exc.HTTPNotFound,
        'ProfileTypeNotFound': webob.exc.HTTPNotFound,
        'ProfileTypeNotMatch': webob.exc.HTTPBadRequest,
        'RequestLimitExceeded': webob.exc.HTTPBadRequest,
        'ResourceInUse': webob.exc.HTTPConflict,
        'SenlinBadRequest': webob.exc.HTTPBadRequest,
        'SpecValidationFailed': webob.exc.HTTPBadRequest,
        'TriggerNotFound': webob.exc.HTTPNotFound,
        'TriggerTypeNotFound': webob.exc.HTTPNotFound,
        'WebhookNotFound': webob.exc.HTTPNotFound,
    }

    def _map_exception_to_error(self, class_exception):
        if class_exception == Exception:
            return webob.exc.HTTPInternalServerError

        if class_exception.__name__ not in self.error_map:
            return self._map_exception_to_error(class_exception.__base__)

        return self.error_map[class_exception.__name__]

    def _error(self, ex):
        trace = None
        traceback_marker = 'Traceback (most recent call last)'
        webob_exc = None
        if isinstance(ex, exception.HTTPExceptionDisguise):
            # An HTTP exception was disguised so it could make it here
            # let's remove the disguise and set the original HTTP exception
            if cfg.CONF.debug:
                trace = ''.join(traceback.format_tb(ex.tb))
            ex = ex.exc
            webob_exc = ex

        ex_type = ex.__class__.__name__

        is_remote = ex_type.endswith('_Remote')
        if is_remote:
            ex_type = ex_type[:-len('_Remote')]

        full_message = six.text_type(ex)
        if '\n' in full_message and is_remote:
            message, msg_trace = full_message.split('\n', 1)
        elif traceback_marker in full_message:
            message, msg_trace = full_message.split(traceback_marker, 1)
            message = message.rstrip('\n')
            msg_trace = traceback_marker + msg_trace
        else:
            if six.PY3:
                msg_trace = traceback.format_exception(type(ex), ex,
                                                       ex.__traceback__)
            else:
                msg_trace = traceback.format_exc()

            message = full_message

        if isinstance(ex, exception.SenlinException):
            message = ex.message

        if cfg.CONF.debug and not trace:
            trace = msg_trace

        if not webob_exc:
            webob_exc = self._map_exception_to_error(ex.__class__)

        error = {
            'code': webob_exc.code,
            'title': webob_exc.title,
            'explanation': webob_exc.explanation,
            'error': {
                'code': webob_exc.code,
                'message': message,
                'type': ex_type,
                'traceback': trace,
            }
        }

        return error

    def process_request(self, req):
        try:
            return req.get_response(self.application)
        except Exception as exc:
            return req.get_response(Fault(self._error(exc)))
