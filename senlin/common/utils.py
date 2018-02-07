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

"""
Common utilities module.
"""

import random
import re
import string

from jsonpath_rw import parse
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils
from oslo_utils import timeutils
import requests
import six
from six.moves import urllib

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.objects import service as service_obj

cfg.CONF.import_opt('max_response_size', 'senlin.common.config')
cfg.CONF.import_opt('periodic_interval', 'senlin.common.config')

LOG = logging.getLogger(__name__)
_ISO8601_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class URLFetchError(exception.Error, IOError):
    pass


def get_positive_int(v):
    """Util function converting/checking a value of positive integer.

    :param v: A value to be checked.
    :returns: (b, v) where v is (converted) value if bool is True.
              b is False if the value fails validation.
    """
    if strutils.is_int_like(v):
        count = int(v)
        if count > 0:
            return True, count
    return False, 0


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


def level_from_number(value):
    """Parse a given level value(from number to string).

    :param value: event level number.
    :return: A translated value.
    """
    n = int(value)
    levels = {value: key for key, value in consts.EVENT_LEVELS.items()}
    return levels.get(n, None)


def url_fetch(url, allowed_schemes=('http', 'https')):
    '''Get the data at the specified URL.

    The URL must use the http: or https: schemes.
    The file: scheme is also supported if you override
    the allowed_schemes argument.
    Raise an IOError if getting the data fails.
    '''
    LOG.info('Fetching data from %s', url)

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

    except requests.exceptions.RequestException as ex:
        raise URLFetchError(_('Failed to retrieve data: %s') % ex)


def random_name(length=8):
    if length <= 0:
        return ''

    lead = random.choice(string.ascii_letters)
    tail = ''.join(random.choice(string.ascii_letters + string.digits)
                   for _ in range(length - 1))
    return lead + tail


def format_node_name(fmt, cluster, index):
    """Generates a node name using the given format.

    :param fmt: A string containing format directives. Currently we only
                support the following keys:
                - "$nR": a random string with at most 'n' characters where
                         'n' defaults to 8.
                - "$nI": a string representation of the node index where 'n'
                         instructs the number of digits generated with 0s
                         padded to the left.
    :param cluster: The DB object for the cluster to which the node belongs.
                    This parameter is provided for future extension.
    :param index: The index for the node in the target cluster.
    :returns: A string containing the generated node name.
    """
    # for backward compatibility
    if not fmt:
        fmt = "node-$8R"

    result = ""
    last = 0
    pattern = re.compile("(\$\d{0,8}[RI])")
    for m in pattern.finditer(fmt):
        group = m.group()
        t = group[-1]
        width = group[1:-1]
        if t == "R":  # random string
            if width != "":
                sub = random_name(int(width))
            else:
                sub = random_name(8)
        elif t == "I":  # node index
            if width != "":
                str_index = str(index)
                sub = str_index.zfill(int(width))
            else:
                sub = str(index)
        result += fmt[last:m.start()] + sub
        last = m.end()
    result += fmt[last:]

    return result


def isotime(at):
    """Stringify time in ISO 8601 format.

    oslo.versionedobject is using this function for datetime formatting.
    """
    if at is None:
        return None

    st = at.strftime(_ISO8601_TIME_FORMAT)
    tz = at.tzinfo.tzname(None) if at.tzinfo else 'UTC'
    st += ('Z' if tz == 'UTC' or tz == "UTC+00:00" else tz)
    return st


def get_path_parser(path):
    """Get a JsonPath parser based on a path string.

    :param path: A string containing a JsonPath.
    :returns: A parser used for path matching.
    :raises: An exception of `BadRequest` if the path fails validation.
    """
    try:
        expr = parse(path)
    except Exception as ex:
        error_text = six.text_type(ex)
        error_msg = error_text.split(':', 1)[1]
        raise exception.BadRequest(
            msg=_("Invalid attribute path - %s") % error_msg.strip())

    return expr


def is_engine_dead(ctx, engine_id, duration=None):
    """Check if an engine is dead.

    If engine hasn't reported its status for the given duration, it is treated
    as a dead engine.

    :param ctx: A request context.
    :param engine_id: The ID of the engine to test.
    :param duration: The time duration in seconds.
    """
    if not duration:
        duration = 2 * cfg.CONF.periodic_interval

    eng = service_obj.Service.get(ctx, engine_id)
    if not eng:
        return True
    if timeutils.is_older_than(eng.updated_at, duration):
        return True
    return False
