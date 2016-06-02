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

from oslo_serialization import jsonutils
from oslo_utils import timeutils
import pytz

from sqlalchemy.dialects import mysql
from sqlalchemy.ext import mutable
from sqlalchemy import types


class MutableList(mutable.Mutable, list):
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return mutable.Mutable.coerce(key, value)
        else:
            return value

    def __init__(self, initval=None):
        list.__init__(self, initval or [])

    def __getitem__(self, key):
        value = list.__getitem__(self, key)
        for obj, key in self._parents.items():
            value._parents[obj] = key
        return value

    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return list(self)

    def __setstate__(self, state):
        self[:] = state

    def append(self, value):
        list.append(self, value)
        self.changed()

    def extend(self, iterable):
        list.extend(self, iterable)
        self.changed()

    def insert(self, index, item):
        list.insert(self, index, item)
        self.changed()

    def __setslice__(self, i, j, other):
        list.__setslice__(self, i, j, other)
        self.changed()

    def pop(self, index=-1):
        item = list.pop(self, index)
        self.changed()
        return item

    def remove(self, value):
        list.remove(self, value)
        self.changed()


class Dict(types.TypeDecorator):
    impl = types.Text

    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(mysql.LONGTEXT())
        else:
            return self.impl

    def process_bind_param(self, value, dialect):
        return jsonutils.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return jsonutils.loads(value)


class List(types.TypeDecorator):
    impl = types.Text

    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(mysql.LONGTEXT())
        else:
            return self.impl

    def process_bind_param(self, value, dialect):
        return jsonutils.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return jsonutils.loads(value)


class TZAwareDateTime(types.TypeDecorator):
    """A DB type that is time zone aware."""
    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'mysql':
            return timeutils.normalize_time(value)

        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=pytz.utc)


mutable.MutableDict.associate_with(Dict)
MutableList.associate_with(List)
