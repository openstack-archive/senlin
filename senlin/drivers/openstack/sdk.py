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
import functools
from oslo_config import cfg
from oslo_log import log as logging
import six

from openstack import connection
from openstack import exceptions
from openstack import profile
from openstack import transport
from oslo_serialization import jsonutils
from requests import exceptions as reqexc

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _

USER_AGENT = 'senlin'
exc = exceptions
LOG = logging.getLogger(__name__)


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
    code = 500
    message = _('Unknown exception: %s') % ex

    if isinstance(ex, exceptions.HttpException):
        try:
            data = jsonutils.loads(ex.details)
            code = data['error'].get('code', None)
            if code is None:
                code = data['code']
            message = data['error']['message']
        except ValueError:
            # Some exceptions don't have details record, we try make a guess
            code = ex.status_code
            message = ex.message
    elif isinstance(ex, reqexc.RequestException):
        # Exceptions that are not captured by SDK
        if isinstance(ex.message, list):
            msg = ex.message[0]
        else:
            msg = ex.message
        code = ex.message[1].errno
        message = msg
    elif isinstance(ex, Exception):
        code = ex.message[1].errno
        message = six.text_type(ex)

    raise exception.InternalError(code=code, message=message)


def translate_exception(func):
    """Decorator for exception translation."""

    @functools.wraps(func)
    def invoke_with_catch(driver, *args, **kwargs):
        try:
            return func(driver, *args, **kwargs)
        except Exception as ex:
            raise parse_exception(ex)

    return invoke_with_catch


def ignore_not_found(ex):
    parsed = parse_exception(ex)
    if not isinstance(parsed, HTTPNotFound):
        raise parsed


def create_connection(ctx):
    if isinstance(ctx, dict):
        ctx = context.RequestContext.from_dict(ctx)
    kwargs = {
        'auth_url': ctx.auth_url,
        'domain_id': ctx.domain,
        'project_id': ctx.project,
        'project_name': ctx.project_name,
        'project_domain_name': ctx.project_domain_name,
        'user_domain_name': ctx.user_domain_name,
        'username': ctx.user_name,
        'user_id': ctx.user,
        'password': ctx.password,
        'trust_id': ctx.trusts,
        'token': ctx.auth_token,
        #  'auth_plugin': args.auth_plugin,
        #  'verify': OS_CACERT, TLS certificate to verify remote server
    }

    prof = profile.Profile()
    if ctx.region_name:
        prof.set_region(prof.ALL, ctx.region_name)

    try:
        conn = connection.Connection(profile=prof, user_agent=USER_AGENT,
                                     **kwargs)
    except exceptions.HttpException as ex:
        raise ex
    return conn


def authenticate(**kwargs):
    '''Authenticate using openstack sdk based on user credential'''

    # Build a context based on credential for sdk connection
    cnxt = context.RequestContext.from_dict(kwargs)

    try:
        auth = create_connection(cnxt).session.authenticator
        xport = transport.Transport()
        access_info = auth.authorize(xport)
    except exceptions.HttpException as ex:
        raise ex

    return access_info


def get_service_user_id():
    # Convert user name to user ID
    params = {
        'auth_url': cfg.CONF.authentication.auth_url,
        'user_name': cfg.CONF.authentication.service_username,
        'password': cfg.CONF.authentication.service_password,
        'project_name': cfg.CONF.authentication.service_project_name,
        'user_domain_name': cfg.CONF.authentication.service_user_domain,
        'project_domain_name': cfg.CONF.authentication.service_project_domain,
    }

    user_id = None
    try:
        access_info = authenticate(**params)
        user_id = access_info.user_id
    except Exception as ex:
        LOG.exception(_('Authentication failure: %s'), six.text_type(ex))

    return user_id
