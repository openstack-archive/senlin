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
from oslo_log import log as logging
import six

from openstack import connection
from openstack import exceptions as sdk_exc
from openstack import profile
from openstack import transport
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
        code = ex.status_code
        message = ex.message
        data = {}
        try:
            data = jsonutils.loads(ex.details)
        except Exception:
            # Some exceptions don't have details record or
            # are not in JSON format
            pass

        # try dig more into the exception record
        code = data.get('code', code)
        error = data.get('error', None)
        if error:
            code = data['error'].get('code', code)
            message = data['error'].get('message', message)

    elif isinstance(ex, sdk_exc.SDKException):
        # Besides HttpException there are some other exceptions like
        # ResourceTimeout can be raised from SDK, handle them here.
        message = ex.message
    elif isinstance(ex, req_exc.RequestException):
        # Exceptions that are not captured by SDK
        code = ex.errno
        message = six.text_type(ex)
    elif isinstance(ex, Exception):
        message = six.text_type(ex)

    # LOG.exception(ex)
    raise senlin_exc.InternalError(code=code, message=message)


def translate_exception(func):
    """Decorator for exception translation."""

    @functools.wraps(func)
    def invoke_with_catch(driver, *args, **kwargs):
        try:
            return func(driver, *args, **kwargs)
        except Exception as ex:
            raise parse_exception(ex)

    return invoke_with_catch


def create_connection(params=None):
    if params is None:
        params = {}
    prof = profile.Profile()
    if 'region_name' in params:
        prof.set_region(prof.ALL, params['region_name'])
        params.pop('region_name')
    try:
        conn = connection.Connection(profile=prof, user_agent=USER_AGENT,
                                     **params)
    except Exception as ex:
        raise parse_exception(ex)

    return conn


def authenticate(**kwargs):
    '''Authenticate using openstack sdk based on user credential'''

    try:
        auth = create_connection(kwargs).session.authenticator
        xport = transport.Transport()
        access_info = auth.authorize(xport)
    except Exception as ex:
        raise parse_exception(ex)

    return access_info
