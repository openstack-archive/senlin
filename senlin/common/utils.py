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
import six
import uuid

from oslo_utils import strutils

from senlin.common import exception
from senlin.common.i18n import _


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
        if allow_negative == False and result < 0:
            raise exception.InvalidParameter(name=name, value=value)

    return result


def parse_bool_param(name, value):
    if str(value).lower() not in ('true', 'false'):
        raise exception.InvalidParameter(name=name, value=str(value))

    return strutils.bool_from_string(value, strict=True)
