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
import sys

import functools
from openstack import connection
from openstack import exceptions as sdk_exc
from openstack import utils as sdk_utils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from requests import exceptions as req_exc
import six

from senlin.common import exception as senlin_exc
from senlin import version

USER_AGENT = 'senlin'
exc = sdk_exc
LOG = logging.getLogger(__name__)

sdk_utils.enable_logging(debug=False, stream=sys.stdout)


def parse_exception(ex):
    '''Parse exception code and yield useful information.'''
    code = 500

    LOG.exception(ex)
    if isinstance(ex, sdk_exc.HttpException):
        # some exceptions don't contain status_code
        if hasattr(ex, "status_code") and ex.status_code is not None:
            code = ex.status_code
        elif hasattr(ex, "http_status") and ex.http_status is not None:
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

    if 'token' in params:
        params['auth_type'] = 'token'
    params['app_name'] = USER_AGENT
    params['app_version'] = version.version_info.version_string()
    params.setdefault('region_name', cfg.CONF.default_region_name)
    params.setdefault('identity_api_version', '3')
    params.setdefault('messaging_api_version', '2')

    try:
        conn = connection.Connection(**params)
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


class FakeResourceObject(object):
    '''Generate a fake SDK resource object based on given dictionary'''
    def __init__(self, params):
        for key in params:
            setattr(self, key, params[key])

    def to_dict(self):
        '''Override this function in subclass to handle special attributes'''
        data = {}
        for attr in dir(self):
            if not attr.startswith('__'):
                # Exclude built-in attributes of python object
                data[attr] = getattr(self, attr)

        return data
