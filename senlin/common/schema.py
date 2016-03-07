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
import numbers
import six

from oslo_serialization import jsonutils
from oslo_utils import strutils

from senlin.common import exception
from senlin.common.i18n import _


class AnyIndexDict(collections.Mapping):
    '''Convenience schema for a list.'''
    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        if key != '*' and not isinstance(key, six.integer_types):
            raise KeyError(_('Invalid key %s') % str(key))

        return self.value

    def __iter__(self):
        yield '*'

    def __len__(self):
        return 1


class Schema(collections.Mapping):
    '''Class for validating profile and policy specifications.'''

    KEYS = (
        TYPE, DESCRIPTION, DEFAULT, REQUIRED, SCHEMA, UPDATABLE,
        CONSTRAINTS, READONLY,
    ) = (
        'type', 'description', 'default', 'required', 'schema', 'updatable',
        'constraints', 'readonly',
    )

    TYPES = (
        INTEGER, STRING, NUMBER, BOOLEAN, MAP, LIST,
    ) = (
        'Integer', 'String', 'Number', 'Boolean', 'Map', 'List',
    )

    def __init__(self, description=None, default=None,
                 required=False, schema=None, updatable=False,
                 readonly=False, constraints=None):

        if schema is not None:
            if type(self) not in (List, Map):
                msg = _('Schema valid only for List or Map, not '
                        '"%s"') % self[self.TYPE]
                raise exception.InvalidSchemaError(message=msg)

        if self[self.TYPE] == self.LIST:
            self.schema = AnyIndexDict(schema)
        else:
            self.schema = schema

        self.description = description
        self.default = default
        self.required = required
        self.updatable = updatable
        self.constraints = constraints or []
        self.readonly = readonly
        self._len = None

    def has_default(self):
        return self.default is not None

    def get_default(self):
        return self.resolve(self.default)

    def _validate_default(self, context):
        if self.default is None:
            return

        try:
            self.validate(self.default, context)
        except (ValueError, TypeError) as exc:
            raise exception.InvalidSchemaError(
                message=_('Invalid default %(default)s (%(exc)s)') %
                dict(default=self.default, exc=exc))

    def validate(self, context=None):
        '''Validates the schema.

        This method checks if the schema itself is valid.
        '''
        self._validate_default(context)

        # validated nested schema: List or Map
        if self.schema:
            if isinstance(self.schema, AnyIndexDict):
                self.schema.value.validate(context)
            else:
                for nested_schema in self.schema.values():
                    nested_schema.validate(context)

    def validate_constraints(self, value, context=None, skipped=None):
        if not skipped:
            skipped = []

        try:
            for constraint in self.constraints:
                if type(constraint) not in skipped:
                    constraint.validate(value, context)
        except ValueError as ex:
            raise exception.SpecValidationFailed(message=six.text_type(ex))

    def __getitem__(self, key):
        if key == self.DESCRIPTION:
            if self.description is not None:
                return self.description
        elif key == self.DEFAULT:
            if self.default is not None:
                return self.default
        elif key == self.SCHEMA:
            if self.schema is not None:
                return dict((n, dict(s)) for n, s in self.schema.items())
        elif key == self.REQUIRED:
            return self.required
        elif key == self.READONLY:
            return self.readonly
        elif key == self.UPDATABLE:
            return self.updatable
        elif key == self.CONSTRAINTS:
            if self.constraints:
                return [dict(c) for c in self.constraints]

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
        if self._len is None:
            self._len = len(list(iter(self)))
        return self._len


class Boolean(Schema):
    def __getitem__(self, key):
        if key == self.TYPE:
            return self.BOOLEAN
        else:
            return super(Boolean, self).__getitem__(key)

    def to_schema_type(self, value):
        return strutils.bool_from_string(str(value), strict=True)

    def resolve(self, value):
        if str(value).lower() not in ('true', 'false'):
            msg = _('The value "%s" is not a valid Boolean') % value
            raise exception.SpecValidationFailed(message=msg)

        return strutils.bool_from_string(value, strict=True)

    def validate(self, value, context=None):
        if isinstance(value, bool):
            return

        self.resolve(value)


class Integer(Schema):
    def __getitem__(self, key):
        if key == self.TYPE:
            return self.INTEGER
        else:
            return super(Integer, self).__getitem__(key)

    def to_schema_type(self, value):
        if isinstance(value, six.integer_types):
            return value
        try:
            num = int(value)
        except ValueError:
            raise ValueError(_('%s is not an intger.') % num)

        return num

    def resolve(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            msg = _('The value "%s" cannot be converted into an '
                    'integer.') % value
            raise exception.SpecValidationFailed(message=msg)

    def validate(self, value, context=None):
        if not isinstance(value, six.integer_types):
            value = self.resolve(value)

        self.validate_constraints(value, self, context)


class String(Schema):
    def __getitem__(self, key):
        if key == self.TYPE:
            return self.STRING
        else:
            return super(String, self).__getitem__(key)

    def to_schema_type(self, value):
        return str(value)

    def resolve(self, value):
        try:
            return str(value)
        except (TypeError, ValueError) as ex:
            raise ex

    def validate(self, value, context=None):
        if not isinstance(value, six.string_types):
            msg = _('The value "%s" cannot be converted into a '
                    'string.') % value
            raise exception.SpecValidationFailed(message=msg)

        self.resolve(value)
        self.validate_constraints(value, self, context)


class Number(Schema):
    def __getitem__(self, key):
        if key == self.TYPE:
            return self.NUMBER
        else:
            return super(Number, self).__getitem__(key)

    def to_schema_type(self, value):
        if isinstance(value, numbers.Number):
            return value

        try:
            return int(value)
        except ValueError:
            return float(value)

    def resolve(self, value):
        if isinstance(value, numbers.Number):
            return value

        try:
            return int(value)
        except ValueError:
            return float(value)

    def validate(self, value, context=None):
        if isinstance(value, numbers.Number):
            return

        self.resolve(value)
        self.resolve_constraints(value, self, context)


class List(Schema):
    def __getitem__(self, key):
        if key == self.TYPE:
            return self.LIST
        else:
            return super(List, self).__getitem__(key)

    def _get_children(self, values, keys, context):
        sub_schema = self.schema
        if sub_schema is not None:
            # We have a child schema specified for list elements
            # Fake a dict of array elements, since we have only one schema
            schema_arr = dict((k, sub_schema[k]) for k in keys)
            subspec = Spec(schema_arr, dict(values))
            subspec.validate()

            return ((k, subspec[k]) for k in keys)
        else:
            return values

    def get_default(self):
        if not isinstance(self.default, collections.Sequence):
            raise TypeError(_('"%s" is not a List') % self.default)

        return self.default

    def resolve(self, value, context=None):
        if not isinstance(value, collections.Sequence):
            raise TypeError(_('"%s" is not a List') % value)

        return [v[1] for v in self._get_children(enumerate(value),
                                                 list(range(len(value))),
                                                 context)]

    def validate(self, value, context=None):
        if not isinstance(value, collections.Mapping):
            raise TypeError(_('"%s" is not a Map') % value)

        for key, child in self.schema.items():
            item_value = value.get(key)
            child.validate(item_value, context)


class Map(Schema):
    def __getitem__(self, key):
        if key == self.TYPE:
            return self.MAP
        else:
            return super(Map, self).__getitem__(key)

    def _get_children(self, values, context=None):
        # There are cases where the Map is not specified to the very detailed
        # levels, we treat them as valid specs as well.
        if self.schema is None:
            return values

        sub_schema = self.schema
        if sub_schema is not None:
            # sub_schema shoud be a dict here
            subspec = Spec(sub_schema, dict(values))
            subspec.validate()

            return ((k, subspec[k]) for k in sub_schema)
        else:
            return values

    def get_default(self):
        if not isinstance(self.default, collections.Mapping):
            raise TypeError(_('"%s" is not a Map') % self.default)

        return self.default

    def resolve(self, value, context=None):
        if isinstance(value, six.string_types):
            try:
                value = jsonutils.loads(value)
            except (TypeError, ValueError):
                pass

        if not isinstance(value, collections.Mapping):
            raise TypeError(_('"%s" is not a Map') % value)

        return dict(self._get_children(six.iteritems(value), context))

    def validate(self, value, context=None):
        if not isinstance(value, collections.Mapping):
            raise TypeError(_('"%s" is not a Map') % value)

        for key, child in self.schema.items():
            item_value = value.get(key)
            child.validate(item_value, context)


class Spec(collections.Mapping):
    '''A class that contains all spec items.'''
    def __init__(self, schema, data):
        self._schema = schema
        self._data = data

    def validate(self):
        '''Validate the schema.'''
        for (k, s) in self._schema.items():
            try:
                # validate through resolve
                self.resolve_value(k)
            except (TypeError, ValueError) as err:
                msg = _('Spec validation error (%(key)s): %(err)s') % dict(
                    key=k, err=six.text_type(err))
                raise exception.SpecValidationFailed(message=msg)

        for key in self._data:
            if key not in self._schema:
                msg = _('Unrecognizable spec item "%s"') % key
                raise exception.SpecValidationFailed(message=msg)

    def resolve_value(self, key):
        if key not in self:
            raise KeyError(_('Invalid spec item: "%s"') % key)

        schema_item = self._schema[key]
        if key in self._data:
            raw_value = self._data[key]
            return schema_item.resolve(raw_value)
        elif schema_item.has_default():
            return schema_item.get_default()
        elif schema_item.required:
            raise ValueError(_('Required spec item "%s" not assigned') % key)

    def __getitem__(self, key):
        '''Lazy evaluation for spec items.'''
        return self.resolve_value(key)

    def __len__(self):
        '''Number of items in the spec.

        A spec always contain all keys though some may be not specified.
        '''
        return len(self._schema)

    def __contains__(self, key):
        return key in self._schema

    def __iter__(self):
        return iter(self._schema)


def get_spec_version(spec):
    if not isinstance(spec, dict):
        msg = _('The provided spec is not a map.')
        raise exception.SpecValidationFailed(message=msg)

    if 'type' not in spec:
        msg = _("The 'type' key is missing from the provided spec map.")
        raise exception.SpecValidationFailed(message=msg)

    if 'version' not in spec:
        msg = _("The 'version' key is missing from the provided spec map.")
        raise exception.SpecValidationFailed(message=msg)

    return (spec['type'], six.text_type(spec['version']))
