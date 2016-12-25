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

import collections
import six

from senlin.common import exception as exc
from senlin.common.i18n import _


class BaseConstraint(collections.Mapping):
    KEYS = (
        TYPE, CONSTRAINT,
    ) = (
        'type', 'constraint',
    )

    def __str__(self):
        '''Utility method for generating schema docs.'''
        return self.desc()

    def validate(self, value, schema=None, context=None):
        '''Base entry for validation.'''
        if not self._validate(value, schema=schema, context=context):
            raise ValueError(self._error(value))

    @classmethod
    def _name(cls):
        return cls.__name__

    def __getitem__(self, key):
        if key == self.TYPE:
            return self._name()
        elif key == self.CONSTRAINT:
            return self._constraint()

        raise KeyError(key)

    def __iter__(self):
        for k in self.KEYS:
            try:
                self[k]
            except KeyError:
                pass
            else:
                yield k

    def __len__(self):
        return len(list(iter(self)))


class AllowedValues(BaseConstraint):
    def __init__(self, allowed_values):
        if (not isinstance(allowed_values, collections.Sequence) or
                isinstance(allowed_values, six.string_types)):
            msg = _('AllowedValues must be a list or a string')
            raise exc.ESchema(message=msg)

        self.allowed = tuple(allowed_values)

    def desc(self):
        values = ', '.join(str(v) for v in self.allowed)
        return _('Allowed values: %s') % values

    def _error(self, value):
        values = ', '.join(str(v) for v in self.allowed)
        return _("'%(value)s' must be one of the allowed values: "
                 "%(allowed)s") % dict(value=value, allowed=values)

    def _validate(self, value, schema=None, context=None):
        if isinstance(value, list):
            return all(v in self.allowed for v in value)

        # try implicit type conversion
        if schema is not None:
            _allowed = tuple(schema.to_schema_type(v)
                             for v in self.allowed)
            return schema.to_schema_type(value) in _allowed
        return value in self.allowed

    def _constraint(self):
        return list(self.allowed)
