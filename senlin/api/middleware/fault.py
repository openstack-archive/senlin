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

"""
A middleware that turns exceptions into parsable string.
"""

from oslo_utils import reflection
import six
import webob

from senlin.api.common import serializers
from senlin.api.common import wsgi
from senlin.common import exception


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
        'BadRequest': webob.exc.HTTPBadRequest,
        'FeatureNotSupported': webob.exc.HTTPConflict,
        'Forbidden': webob.exc.HTTPForbidden,
        'InternalError': webob.exc.HTTPInternalServerError,
        'InvalidGlobalAPIVersion': webob.exc.HTTPNotAcceptable,
        'InvalidSpec': webob.exc.HTTPBadRequest,
        'MethodVersionNotFound': webob.exc.HTTPBadRequest,
        'MultipleChoices': webob.exc.HTTPBadRequest,
        'NodeNotOrphan': webob.exc.HTTPConflict,
        'PolicyBindingNotFound': webob.exc.HTTPNotFound,
        'ProfileOperationFailed': webob.exc.HTTPInternalServerError,
        'RequestLimitExceeded': webob.exc.HTTPBadRequest,
        'ResourceInUse': webob.exc.HTTPConflict,
        'ResourceNotFound': webob.exc.HTTPNotFound,
    }

    def _map_exception_to_error(self, class_exception):
        if class_exception == Exception:
            return webob.exc.HTTPInternalServerError

        if class_exception.__name__ not in self.error_map:
            return self._map_exception_to_error(class_exception.__base__)

        return self.error_map[class_exception.__name__]

    def _error(self, ex):
        traceback_marker = 'Traceback (most recent call last)'
        webob_exc = None
        if isinstance(ex, exception.HTTPExceptionDisguise):
            ex = ex.exc
            webob_exc = ex

        ex_type = reflection.get_class_name(ex, fully_qualified=False)

        is_remote = ex_type.endswith('_Remote')
        if is_remote:
            ex_type = ex_type[:-len('_Remote')]

        full_message = six.text_type(ex)
        if '\n' in full_message and is_remote:
            message = full_message.split('\n', 1)[0]
        elif traceback_marker in full_message:
            message = full_message.split(traceback_marker, 1)[0]
            message = message.rstrip('\n')
        else:
            message = full_message

        if isinstance(ex, exception.SenlinException):
            message = ex.message

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
            }
        }

        return error

    def process_request(self, req):
        try:
            return req.get_response(self.application)
        except Exception as exc:
            return req.get_response(Fault(self._error(exc)))
