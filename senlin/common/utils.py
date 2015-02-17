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

import base64
import requests
from requests import exceptions
import six
from six.moves import urllib
import uuid

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI

cfg.CONF.import_opt('max_response_size', 'senlin.common.config')
LOG = logging.getLogger(__name__)


class URLFetchError(exception.Error, IOError):
    pass


def _to_byte_string(value, num_bits):
    """Convert an integer to a big-endian string of bytes with padding.

    Padding is added at the end (i.e. after the least-significant bit) if
    required.
    """
    shifts = six.moves.xrange(num_bits - 8, -8, -8)
    byte_at = lambda off: (value >> off if off >= 0 else value << -off) & 0xff
    return ''.join(chr(byte_at(offset)) for offset in shifts)


def get_id(source_uuid):
    """Derive a short (12 character) id from a random UUID.

    The supplied UUID must be a version 4 UUID object.
    """
    if isinstance(source_uuid, six.string_types):
        source_uuid = uuid.UUID(source_uuid)
    if source_uuid.version != 4:
        raise ValueError(_('Invalid UUID version (%d)') % source_uuid.version)

    # The "time" field of a v4 UUID contains 60 random bits
    # (see RFC4122, Section 4.4)
    random_bytes = _to_byte_string(source_uuid.time, 60)
    # The first 12 bytes (= 60 bits) of base32-encoded output is our data
    encoded = base64.b32encode(random_bytes)[:12]

    return encoded.lower()


def generate_id():
    """Generate a short (12 character), random id."""
    return get_id(uuid.uuid4())


def parse_int_param(name, value, allow_zero=True, allow_negative=False):
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
        if allow_negative is False and result < 0:
            raise exception.InvalidParameter(name=name, value=value)

    return result


def parse_bool_param(name, value):
    if str(value).lower() not in ('true', 'false'):
        raise exception.InvalidParameter(name=name, value=str(value))

    return strutils.bool_from_string(value, strict=True)


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
        # download the content in chunks to until max_reponse_size is reached.
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
