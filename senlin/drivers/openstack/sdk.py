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
from openstack import exceptions as sdk_exc
from openstack import profile
from oslo_serialization import jsonutils
from requests import exceptions as req_exc

from senlin.common import exception as senlin_exc

USER_AGENT = 'senlin'
exc = sdk_exc
LOG = logging.getLogger(__name__)


def parse_exception(ex):
    '''Parse exception code and yield useful information.'''
    code = 500

    if isinstance(ex, sdk_exc.HttpException):
        # some exceptions don't contain status_code
        if ex.http_status is not None:
            code = ex.http_status
        message = ex.message
        data = {}
        if ex.details is None and ex.response is not None:
            data = ex.response.json()
        else:
            try:
                data = jsonutils.loads(ex.details)
            except Exception:
                # Some exceptions don't have details record or
                # are not in JSON format
                pass

        # try dig more into the exception record
        # usually 'data' has two types of format :
        # type1: {"forbidden": {"message": "error message", "code": 403}
        # type2: {"code": 404, "error": { "message": "not found"}}
        if data:
            code = data.get('code', code)
            message = data.get('message', message)
            error = data.get('error', None)
            if error:
                code = data.get('code', code)
                message = data['error'].get('message', message)
            else:
                for value in data.values():
                    code = value.get('code', code)
                    message = value.get('message', message)

    elif isinstance(ex, sdk_exc.SDKException):
        # Besides HttpException there are some other exceptions like
        # ResourceTimeout can be raised from SDK, handle them here.
        message = ex.message
    elif isinstance(ex, req_exc.RequestException):
        # Exceptions that are not captured by SDK
        code = ex.errno
        message = six.text_type(ex)
    else:
        # This could be a generic exception or something we don't understand
        message = six.text_type(ex)

    raise senlin_exc.InternalError(code=code, message=message)


def translate_exception(func):
    """Decorator for exception translation."""

    @functools.wraps(func)
    def invoke_with_catch(driver, *args, **kwargs):
        try:
            return func(driver, *args, **kwargs)
        except Exception as ex:
            LOG.exception(ex)
            raise parse_exception(ex)

    return invoke_with_catch


def create_connection(params=None):
    if params is None:
        params = {}

    if params.get('token', None):
        auth_plugin = 'token'
    else:
        auth_plugin = 'password'

    prof = profile.Profile()
    prof.set_version('identity', 'v3')
    if 'region_name' in params:
        prof.set_region(prof.ALL, params['region_name'])
        params.pop('region_name')
    elif cfg.CONF.default_region_name:
        prof.set_region(prof.ALL, cfg.CONF.default_region_name)
    try:
        conn = connection.Connection(profile=prof, user_agent=USER_AGENT,
                                     auth_plugin=auth_plugin, **params)
    except Exception as ex:
        raise parse_exception(ex)

    return conn


def authenticate(**kwargs):
    '''Authenticate using openstack sdk based on user credential'''

    conn = create_connection(kwargs)
    access_info = {
        'token': conn.session.get_token(),
        'user_id': conn.session.get_user_id(),
        'project_id': conn.session.get_project_id()
    }

    return access_info
