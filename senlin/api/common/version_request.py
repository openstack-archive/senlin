# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

from senlin.common import exception
from senlin.common.i18n import _


class APIVersionRequest(object):
    """An API Version Request object."""

    def __init__(self, version_string=None):
        """Initialize an APIVersionRequest object.

        :param version_string: String representation of APIVersionRequest.
            Correct format is 'X.Y', where 'X' and 'Y' are int values.
            None value should be used to create Null APIVersionRequest,
            which is equal to '0.0'.
        """
        self.major = 0
        self.minor = 0

        if version_string is not None:
            match = re.match(r"^([1-9]\d*)\.([1-9]\d*|0)$", version_string)
            if match:
                self.major = int(match.group(1))
                self.minor = int(match.group(2))
            else:
                raise exception.InvalidAPIVersionString(version=version_string)

    def __str__(self):
        return "%s.%s" % (self.major, self.minor)

    def is_null(self):
        return self.major == 0 and self.minor == 0

    def _type_error(self, other):
        return TypeError(_("'%(other)s' must be an instance of '%(cls)s'") %
                         {"other": other, "cls": self.__class__})

    def __lt__(self, other):
        if not isinstance(other, APIVersionRequest):
            raise self._type_error(other)

        return ((self.major, self.minor) < (other.major, other.minor))

    def __eq__(self, other):
        if not isinstance(other, APIVersionRequest):
            raise self._type_error(other)

        return ((self.major, self.minor) == (other.major, other.minor))

    def __gt__(self, other):
        if not isinstance(other, APIVersionRequest):
            raise self._type_error(other)

        return ((self.major, self.minor) > (other.major, other.minor))

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return self > other or self == other

    def matches(self, min_version, max_version):
        """Check this object matches the specified min and/or max.

        This function checks if this version >= the provided min_version
        and this version <= the provided max_version.

        :param min_version: Minimum acceptable version. There is no minimum
                            limit if this is null.
        :param max_version: Maximum acceptable version. There is no maximum
                            limit if this is null.
        :returns: A boolean indicating whether the version matches.
        :raises: ValueError if self is null.
        """
        if self.is_null():
            raise ValueError
        if max_version.is_null() and min_version.is_null():
            return True
        elif max_version.is_null():
            return min_version <= self
        elif min_version.is_null():
            return self <= max_version
        else:
            return min_version <= self <= max_version
