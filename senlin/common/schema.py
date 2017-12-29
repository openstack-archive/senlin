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

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import strutils

from senlin.common import exception as exc
from senlin.common.i18n import _

LOG = logging.getLogger(__name__)


class AnyIndexDict(collections.Mapping):
    """Convenience schema for a list."""

    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        if key != '*' and not isinstance(key, six.integer_types):
            raise KeyError("Invalid key %s" % str(key))

        return self.value

    def __iter__(self):
        yield '*'

    def __len__(self):
        return 1


class SchemaBase(collections.Mapping):
    """Class for validating property or operation schemas."""

    KEYS = (
        TYPE, DESCRIPTION, DEFAULT, REQUIRED, SCHEMA, CONSTRAINTS,
        MIN_VERSION, MAX_VERSION,
    ) = (
        'type', 'description', 'default', 'required', 'schema', 'constraints',
        'min_version', 'max_version',
    )

    TYPES = (
        INTEGER, STRING, NUMBER, BOOLEAN, MAP, LIST,
    ) = (
        'Integer', 'String', 'Number', 'Boolean', 'Map', 'List',
    )

    def __init__(self, description=None, default=None, required=False,
                 schema=None, constraints=None, min_version=None,
                 max_version=None):
        if schema is not None:
            if type(self) not in (List, Map, Operation):
                msg = _('Schema valid only for List or Map, not %s'
                        ) % self[self.TYPE]
                raise exc.ESchema(message=msg)

        if self[self.TYPE] == self.LIST:
            self.schema = AnyIndexDict(schema)
        else:
            self.schema = schema

        self.description = description
        self.default = default
        self.required = required
        self.constraints = constraints or []
        self._len = None
        self.min_version = min_version
        self.max_version = max_version

    def has_default(self):
        return self.default is not None

    def get_default(self):
        return self.resolve(self.default)

    def _validate_default(self, context):
        if self.default is None:
            return

        try:
            # NOTE: this is the subclass's version of 'validate'
            self.validate(self.default, context)
        except (ValueError, TypeError) as ex:
            msg = _('Invalid default %(default)s: %(exc)s'
                    ) % dict(default=self.default, exc=ex)
            raise exc.ESchema(message=msg)

    def validate_constraints(self, value, schema=None, context=None):
        try:
            for constraint in self.constraints:
                constraint.validate(value, schema=schema, context=context)
        except ValueError as ex:
            raise exc.ESchema(message=six.text_type(ex))

    def _validate_version(self, key, version):
        if self.min_version and self.min_version > version:
            msg = _('%(key)s (min_version=%(min)s) is not supported by '
                    'spec version %(version)s.'
                    ) % {'key': key, 'min': self.min_version,
                         'version': version}
            raise exc.ESchema(message=msg)
        if self.max_version:
            if version > self.max_version:
                msg = _('%(key)s (max_version=%(max)s) is not supported '
                        'by spec version %(version)s.'
                        ) % {'version': version, 'max': self.max_version,
                             'key': key}
                raise exc.ESchema(message=msg)
            else:
                msg = _('Warning: %(key)s will be deprecated after version '
                        '%(version)s!') % {'key': key,
                                           'version': self.max_version}
                LOG.warning(msg)

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


class PropertySchema(SchemaBase):
    """Class for validating profile and policy specifications."""

    KEYS = (
        TYPE, DESCRIPTION, DEFAULT, REQUIRED, SCHEMA, UPDATABLE,
        CONSTRAINTS, MIN_VERSION, MAX_VERSION,
    ) = (
        'type', 'description', 'default', 'required', 'schema', 'updatable',
        'constraints', 'min_version', 'max_version',
    )

    def __init__(self, description=None, default=None, required=False,
                 schema=None, updatable=False, constraints=None,
                 min_version=None, max_version=None):
        super(PropertySchema, self).__init__(description=description,
                                             default=default,
                                             required=required, schema=schema,
                                             constraints=constraints,
                                             min_version=min_version,
                                             max_version=max_version)
        self.updatable = updatable

    def __getitem__(self, key):
        # NOTE: UPDATABLE is only applicable to some specs which may be
        #       eligible for an update operation later
        if key == self.UPDATABLE:
            return self.updatable

        return super(PropertySchema, self).__getitem__(key)


class Boolean(PropertySchema):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.BOOLEAN
        return super(Boolean, self).__getitem__(key)

    def to_schema_type(self, value):
        try:
            return strutils.bool_from_string(str(value), strict=True)
        except ValueError:
            msg = _("The value '%s' is not a valid Boolean") % value
            raise exc.ESchema(message=msg)

    def resolve(self, value):
        return self.to_schema_type(value)

    def validate(self, value, context=None):
        if isinstance(value, bool):
            return

        self.resolve(value)


class Integer(PropertySchema):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.INTEGER
        return super(Integer, self).__getitem__(key)

    def to_schema_type(self, value):
        if value is None:
            return None

        if isinstance(value, six.integer_types):
            return value

        try:
            num = int(value)
        except ValueError:
            msg = _("The value '%s' is not a valid Integer") % value
            raise exc.ESchema(message=msg)

        return num

    def resolve(self, value):
        return self.to_schema_type(value)

    def validate(self, value, context=None):
        if not isinstance(value, six.integer_types):
            value = self.resolve(value)

        self.validate_constraints(value, schema=self, context=context)


class String(PropertySchema):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.STRING
        return super(String, self).__getitem__(key)

    def to_schema_type(self, value):
        try:
            if isinstance(value, six.string_types):
                return value
            return str(value) if value is not None else None
        except Exception:
            raise

    def resolve(self, value):
        return self.to_schema_type(value)

    def validate(self, value, context=None):
        if not isinstance(value, six.string_types):
            msg = _("The value '%s' is not a valid string.") % value
            raise exc.ESchema(message=msg)

        self.resolve(value)
        self.validate_constraints(value, schema=self, context=context)


class Number(PropertySchema):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.NUMBER
        return super(Number, self).__getitem__(key)

    def to_schema_type(self, value):
        if isinstance(value, numbers.Number):
            return value

        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                msg = _("The value '%s' is not a valid number.") % value
                raise exc.ESchema(message=msg)

    def resolve(self, value):
        return self.to_schema_type(value)

    def validate(self, value, context=None):
        if not isinstance(value, numbers.Number):
            value = self.resolve(value)

        self.validate_constraints(value, schema=self, context=context)


class List(PropertySchema):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.LIST
        return super(List, self).__getitem__(key)

    def _get_children(self, values, context=None):
        res = []
        for i in range(len(values)):
            res.append(self.schema[i].resolve(values[i]))
        return res

    def resolve(self, value, context=None):
        if not isinstance(value, collections.Sequence):
            raise TypeError(_('"%s" is not a List') % value)

        return [v for v in self._get_children(value, context=context)]

    def validate(self, value, context=None):
        # if not isinstance(value, collections.Mapping):
        if not isinstance(value, collections.Sequence):
            msg = _("'%s' is not a List") % value
            raise exc.ESchema(message=msg)

        for v in value:
            self.schema['*'].validate(v, context=context)


class Map(PropertySchema):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.MAP
        return super(Map, self).__getitem__(key)

    def _get_children(self, values, context=None):
        # There are cases where the Map is not specified to the very
        # detailed levels, we treat them as valid specs as well.
        if self.schema is None:
            return values

        sub_schema = self.schema
        if sub_schema is not None:
            # sub_schema should be a dict here.
            subspec = Spec(sub_schema, dict(values))
            subspec.validate()

            return ((k, subspec[k]) for k in sub_schema)
        else:
            return values

    def get_default(self):
        if self.default is None:
            return {}

        if not isinstance(self.default, collections.Mapping):
            msg = _("'%s' is not a Map") % self.default
            raise exc.ESchema(message=msg)

        return self.default

    def resolve(self, value, context=None):
        if isinstance(value, six.string_types):
            try:
                value = jsonutils.loads(value)
            except (TypeError, ValueError):
                msg = _("'%s' is not a Map") % value
                raise exc.ESchema(message=msg)

        if not isinstance(value, collections.Mapping):
            msg = _("'%s' is not a Map") % value
            raise exc.ESchema(message=msg)

        return dict(self._get_children(value.items(), context))

    def validate(self, value, context=None):
        if not isinstance(value, collections.Mapping):
            msg = _("'%s' is not a Map") % value
            raise exc.ESchema(message=msg)

        for key, child in self.schema.items():
            item_value = value.get(key)
            child.validate(item_value, context)


class StringParam(SchemaBase):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.STRING
        return super(StringParam, self).__getitem__(key)

    def validate(self, value):
        if not isinstance(value, six.string_types):
            raise TypeError("value is not a string")

        self.validate_constraints(value)


class IntegerParam(SchemaBase):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.INTEGER
        return super(IntegerParam, self).__getitem__(key)

    def validate(self, value):
        try:
            int(value)
        except ValueError:
            msg = _("The value '%s' is not a valid Integer") % value
            raise ValueError(msg)

        self.validate_constraints(value)


class Operation(SchemaBase):
    """Class for specifying operations on profiles."""

    KEYS = (
        DESCRIPTION, PARAMETERS,
    ) = (
        'description', 'parameters',
    )

    def __getitem__(self, key):
        if key == self.DESCRIPTION:
            return self.description or "Undocumented"
        elif key == self.PARAMETERS:
            if self.schema is None:
                return {}
            return dict((n, dict(s)) for n, s in self.schema.items())

    def validate(self, data, version=None):
        for k in data:
            if k not in self.schema:
                msg = _("Unrecognizable parameter '%s'") % k
                raise exc.ESchema(message=msg)

        for (k, s) in self.schema.items():
            try:
                if k in data:
                    s.validate(data[k])
                elif s.required:
                    msg = _("Required parameter '%s' not provided") % k
                    raise exc.ESchema(message=msg)

                if version:
                    s._validate_version(k, version)
            except (TypeError, ValueError) as ex:
                raise exc.ESchema(message=six.text_type(ex))


class Spec(collections.Mapping):
    """A class that contains all spec items."""

    def __init__(self, schema, data, version=None):
        self._schema = schema
        self._data = data
        self._version = version

    def validate(self):
        """Validate the schema."""

        for (k, s) in self._schema.items():
            try:
                # Validate through resolve
                self.resolve_value(k)
                # Validate schema for version
                if self._version:
                    self._schema[k]._validate_version(k, self._version)
            except (TypeError, ValueError) as err:
                raise exc.ESchema(message=six.text_type(err))

        for key in self._data:
            if key not in self._schema:
                msg = _("Unrecognizable spec item '%s'") % key
                raise exc.ESchema(message=msg)

    def resolve_value(self, key):
        if key not in self:
            raise exc.ESchema(message="Invalid spec item: %s" % key)

        schema_item = self._schema[key]
        if key in self._data:
            raw_value = self._data[key]
            return schema_item.resolve(raw_value)
        elif schema_item.has_default():
            return schema_item.get_default()
        elif schema_item.required:
            msg = _("Required spec item '%s' not provided") % key
            raise exc.ESchema(message=msg)

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
        raise exc.ESchema(message=msg)

    if 'type' not in spec:
        msg = _("The 'type' key is missing from the provided spec map.")
        raise exc.ESchema(message=msg)

    if 'version' not in spec:
        msg = _("The 'version' key is missing from the provided spec map.")
        raise exc.ESchema(message=msg)

    return (spec['type'], six.text_type(spec['version']))
