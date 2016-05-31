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
Utilities module.
'''

import random
import string

import requests
from requests import exceptions
from six.moves import urllib

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI

cfg.CONF.import_opt('max_response_size', 'senlin.common.config')
LOG = logging.getLogger(__name__)
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class URLFetchError(exception.Error, IOError):
    pass


def parse_int_param(name, value, allow_zero=True, allow_negative=False,
                    lower_limit=None, upper_limit=None):
    if value is None:
        return None

    if value in ('0', 0):
        if allow_zero:
            return int(value)
        raise exception.InvalidParameter(name=name, value=value)

    try:
        result = int(value)
    except (TypeError, ValueError):
        raise exception.InvalidParameter(name=name, value=value)
    else:
        if any([(allow_negative is False and result < 0),
                (lower_limit and result < lower_limit),
                (upper_limit and result > upper_limit)]):
            raise exception.InvalidParameter(name=name, value=value)

    return result


def parse_bool_param(name, value):
    if str(value).lower() not in ('true', 'false'):
        raise exception.InvalidParameter(name=name, value=str(value))

    return strutils.bool_from_string(value, strict=True)


def validate_sort_param(value, whitelist):
    """Validate a string value and see if it is a valid sort param.

    :param value: A string as the input which should be one of the following
                  formats:
                  - 'key1,key2,key3'
                  - 'key1:asc,key2,key3:desc'
                  - 'key1:asc,key2:asc,key3:desc'
    :param whitelist: A list of permitted sorting keys.
    :return: None if validation succeeds or an exception of `InvalidParameter`
             otherwise.
    """

    if value is None:
        return None

    for s in value.split(','):
        s_key, _sep, s_dir = s.partition(':')
        if not s_key or s_key not in whitelist:
            raise exception.InvalidParameter(name='sort key', value=s_key)
        if s_dir and s_dir not in ('asc', 'desc'):
            raise exception.InvalidParameter(name='sort dir', value=s_dir)


def parse_level_values(values):
    """Parse a given list of level values to numbers.

    :param values: A list of event level values.
    :return: A list of translated values.
    """
    if not isinstance(values, list):
        values = [values]
    result = []
    for v in values:
        if v in consts.EVENT_LEVELS:
            result.append(consts.EVENT_LEVELS[v])
        elif isinstance(v, int):
            result.append(v)

    if result == []:
        return None
    return result


def url_fetch(url, allowed_schemes=('http', 'https')):
    '''Get the data at the specified URL.

    The URL must use the http: or https: schemes.
    The file: scheme is also supported if you override
    the allowed_schemes argument.
    Raise an IOError if getting the data fails.
    '''
    LOG.info(_LI('Fetching data from %s'), url)

    components = urllib.parse.urlparse(url)

    if components.scheme not in allowed_schemes:
        raise URLFetchError(_('Invalid URL scheme %s') % components.scheme)

    if components.scheme == 'file':
        try:
            return urllib.request.urlopen(url).read()
        except urllib.error.URLError as uex:
            raise URLFetchError(_('Failed to retrieve data: %s') % uex)

    try:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        # We cannot use resp.text here because it would download the entire
        # file, and a large enough file would bring down the engine.  The
        # 'Content-Length' header could be faked, so it's necessary to
        # download the content in chunks to until max_response_size is reached.
        # The chunk_size we use needs to balance CPU-intensive string
        # concatenation with accuracy (eg. it's possible to fetch 1000 bytes
        # greater than max_response_size with a chunk_size of 1000).
        reader = resp.iter_content(chunk_size=1000)
        result = ""
        for chunk in reader:
            result += chunk
            if len(result) > cfg.CONF.max_response_size:
                raise URLFetchError("Data exceeds maximum allowed size (%s"
                                    " bytes)" % cfg.CONF.max_response_size)
        return result

    except exceptions.RequestException as ex:
        raise URLFetchError(_('Failed to retrieve data: %s') % ex)


def random_name(length=8):
    if length <= 0:
        return ''

    lead = random.choice(string.ascii_letters)
    tail = ''.join(random.choice(string.ascii_letters + string.digits)
                   for i in range(length - 1))
    return lead + tail


def format_time(value):
    """Cut microsecond and format to isoformat string."""
    if value:
        value = value.replace(microsecond=0)
        value = value.isoformat()
    return value


def isotime(at):
    """Stringify time in ISO 8601 format.

    oslo.versionedobject is using this function for datetime formatting.
    """
    if at is None:
        return None

    st = at.strftime(_ISO8601_TIME_FORMAT)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if tz == 'UTC' else tz)
    return st
