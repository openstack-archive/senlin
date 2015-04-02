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

'''
SDK Client
'''

from oslo_serialization import jsonutils

from openstack import connection
from openstack import exceptions
from openstack import user_preference
from requests import exceptions as reqexc
from senlin.common.i18n import _

USER_AGENT = 'senlin'

exc = exceptions
verbose = False


class BaseException(Exception):
    '''An error occurred.'''
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.message or self.__class__.__doc__


class HTTPException(BaseException):
    """Base exception for all HTTP-derived exceptions."""
    code = 'N/A'

    def __init__(self, error=None):
        super(HTTPException, self).__init__(error)
        try:
            self.error = error
            if 'error' not in self.error:
                raise KeyError(_('Key "error" not exists'))
        except KeyError:
            # If key 'error' does not exist, self.message becomes
            # no sense. In this case, we return doc of current
            # exception class instead.
            self.error = {'error': {'message': self.__class__.__doc__}}
        except Exception:
            self.error = {'error':
                          {'message': self.message or self.__class__.__doc__}}

    def __str__(self):
        message = self.error['error'].get('message', 'Internal Error')
        if verbose:
            traceback = self.error['error'].get('traceback', '')
            return (_('ERROR: %(message)s\n%(traceback)s') %
                    {'message': message, 'traceback': traceback})
        else:
            code = self.error['error'].get('code', 'Unknown')
            return _('ERROR(%(code)s): %(message)s') % {'code': code,
                                                        'message': message}


class ClientError(HTTPException):
    pass


class ServerError(HTTPException):
    pass


class ConnectionRefused(HTTPException):
    # 111
    pass


class HTTPBadRequest(ClientError):
    # 400
    pass


class HTTPUnauthorized(ClientError):
    # 401
    pass


class HTTPForbidden(ClientError):
    # 403
    pass


class HTTPNotFound(ClientError):
    # 404
    pass


class HTTPInternalServerError(ServerError):
    # 500
    pass


class HTTPNotImplemented(ServerError):
    # 501
    pass


class HTTPServiceUnavailable(ServerError):
    # 503
    pass


_EXCEPTION_MAP = {
    111: ConnectionRefused,
    400: HTTPBadRequest,
    401: HTTPUnauthorized,
    403: HTTPForbidden,
    404: HTTPNotFound,
    500: HTTPInternalServerError,
    501: HTTPNotImplemented,
    503: HTTPServiceUnavailable,
}


def parse_exception(ex):
    '''Parse exception code and yield useful information.

    :param details: details of the exception.
    '''
    if isinstance(ex, exc.HttpException):
        record = jsonutils.loads(ex.details)
    elif isinstance(ex, reqexc.RequestException):
        # Exceptions that are not captured by SDK
        code = ex.message[1].errno
        record = {
            'error': {
                'code': code,
                'message': ex.message[0],
            }
        }
    else:
        print(_('Unknown exception: %s') % ex)
        return

    try:
        code = record['error'].get('code', None)
        if code is None:
            code = record['code']
            record['error']['code'] = code
    except KeyError as err:
        print(_('Malformed exception record, missing field "%s"') % err)
        print(_('Original error record: %s') % record)
        return

    if code in _EXCEPTION_MAP:
        inst = _EXCEPTION_MAP.get(code)
        return inst(record)
    else:
        return HTTPException(record)


def ignore_not_found(ex):
    parsed = parse_exception(ex)
    if not isinstance(parsed, HTTPNotFound):
        raise parsed


def create_connection(context):
    kwargs = {
        'auth_url': context.auth_url,
        'domain_id': context.domain_id,
        'project_id': context.project_id,
        'project_domain_id': context.project_domain_id,
        'user_domain_id': context.user_domain_id,
        'username': context.username,
        'user_id': context.user_id,
        'password': context.password,
        'token': context.auth_token,
        #  'auth_plugin': args.auth_plugin,
        #  'verify': OS_CACERT, TLS certificate to verify remote server
    }

    pref = user_preference.UserPreference()
    if context.region_name:
        pref.set_region(pref.ALL, context.region_name)

    try:
        conn = connection.Connection(preference=pref, user_agent=USER_AGENT,
                                     **kwargs)
    except exceptions.HttpException as ex:
        raise ex
    return conn
