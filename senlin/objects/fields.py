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

from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_versionedobjects import fields
import re
import six

from senlin.common.i18n import _

CONF = cfg.CONF

# Field alias for code readability
BooleanField = fields.BooleanField
FlexibleBooleanField = fields.FlexibleBooleanField
StringField = fields.StringField
IntegerField = fields.IntegerField
FloatField = fields.FloatField
UUIDField = fields.UUIDField
DateTimeField = fields.DateTimeField
ListOfStringsField = fields.ListOfStringsField
ListOfEnumField = fields.ListOfEnumField


# TODO(Qiming): remove this when oslo patch is released
# https://review.openstack.org/#/c/360095
class NonNegativeInteger(fields.FieldType):

    @staticmethod
    def coerce(obj, attr, value):
        v = int(value)
        if v < 0:
            err = _("Value must be >= 0 for field '%s'.") % attr
            raise ValueError(err)
        return v

    def get_schema(self):
        return {
            'type': ['integer', 'string'],
            'minimum': 0
        }


# TODO(Qiming): remove this when oslo patch is released
# i.e. global requirements bump to 1.17.0
class Object(fields.Object):

    def get_schema(self):
        from oslo_versionedobjects import base as obj_base
        obj_classes = obj_base.VersionedObjectRegistry.obj_classes()
        if self._obj_name in obj_classes:
            cls = obj_classes[self._obj_name][0]
            namespace_key = cls._obj_primitive_key('namespace')
            name_key = cls._obj_primitive_key('name')
            version_key = cls._obj_primitive_key('version')
            data_key = cls._obj_primitive_key('data')
            changes_key = cls._obj_primitive_key('changes')
            field_schemas = {key: field.get_schema()
                             for key, field in cls.fields.items()}
            required_fields = [key for key, field in sorted(cls.fields.items())
                               if not field.nullable]

            schema = {
                'type': 'object',
                'properties': {
                    namespace_key: {
                        'type': 'string',
                    },
                    name_key: {
                        'type': 'string',
                    },
                    version_key: {
                        'type': 'string',
                    },
                    changes_key: {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                        }
                    },
                    data_key: {
                        'type': 'object',
                        'description': 'fields of %s' % self._obj_name,
                        'properties': field_schemas,
                        'required': required_fields,
                    },
                },
                'required': [namespace_key, name_key, version_key, data_key],
            }

            return schema
        else:
            return {}


class ObjectField(fields.AutoTypedField):
    def __init__(self, objtype, subclasses=False, **kwargs):
        self.AUTO_TYPE = Object(objtype, subclasses)
        self.objname = objtype
        super(ObjectField, self).__init__(**kwargs)


class Json(fields.FieldType):
    def coerce(self, obj, attr, value):
        if isinstance(value, six.string_types):
            try:
                return jsonutils.loads(value)
            except Exception:
                raise ValueError
        return value

    def from_primitive(self, obj, attr, value):
        return self.coerce(obj, attr, value)

    def to_primitive(self, obj, attr, value):
        return jsonutils.dumps(value)

    def stringify(self, value):
        if isinstance(value, six.string_types):
            try:
                return jsonutils.loads(value)
            except ValueError:
                raise
        return str(value)

    def get_schema(self):
        return {'type': ['object']}


class JsonField(fields.AutoTypedField):
    AUTO_TYPE = Json()


class ListField(fields.AutoTypedField):
    AUTO_TYPE = fields.List(fields.FieldType())


class NotificationPriority(fields.Enum):

    ALL = (
        AUDIT, CRITICAL, DEBUG, INFO, ERROR, SAMPLE, WARN,
    ) = (
        'audit', 'critical', 'debug', 'info', 'error', 'sample', 'warn',
    )

    def __init__(self):
        super(NotificationPriority, self).__init__(
            valid_values=NotificationPriority.ALL)


class NotificationPhase(fields.Enum):

    ALL = (
        START, END, ERROR,
    ) = (
        'start', 'end', 'error',
    )

    def __init__(self):
        super(NotificationPhase, self).__init__(
            valid_values=NotificationPhase.ALL)


class NotificationAction(fields.Enum):

    ALL = (
        UPDATE,
    ) = (
        'update',
    )

    def __init__(self):
        super(NotificationAction, self).__init__(
            valid_values=NotificationAction.ALL)


class NotificationPriorityField(fields.BaseEnumField):
    AUTO_TYPE = NotificationPriority()


class NotificationPhaseField(fields.BaseEnumField):
    AUTO_TYPE = NotificationPhase()


class NotificationActionField(fields.BaseEnumField):
    AUTO_TYPE = NotificationAction()


# TODO(Qiming): remove this when oslo patch is released
# https://review.openstack.org/#/c/360095
class NonNegativeIntegerField(fields.AutoTypedField):

    AUTO_TYPE = NonNegativeInteger()


class Name(fields.String):

    def __init__(self, min_len=1, max_len=255):
        super(Name, self).__init__()
        self.min_len = min_len
        self.max_len = max_len

    def coerce(self, obj, attr, value):
        err = None
        if len(value) < self.min_len:
            err = _("The value for the %(attr)s field must be at least "
                    "%(count)d characters long."
                    ) % {'attr': attr, 'count': self.min_len}
        elif len(value) > self.max_len:
            err = _("The value for the %(attr)s field must be less than "
                    "%(count)d characters long."
                    ) % {'attr': attr, 'count': self.max_len}
        else:
            # NOTE: This is pretty restrictive. We can relax it later when
            # there are requests to do so
            regex = re.compile('^[a-zA-Z\d\.\_\~-]*$', re.IGNORECASE)
            if not regex.search(value):
                err = _("The value for the '%(attr)s' (%(value)s) contains "
                        "illegal characters."
                        ) % {'attr': attr, 'value': value}

        if err:
            raise ValueError(err)

        return super(Name, self).coerce(obj, attr, value)

    def get_schema(self):
        return {
            'type': ['string'],
            'minLength': self.min_len,
            'maxLength': self.max_len
        }


class Capacity(fields.Integer):

    def __init__(self, minimum=0, maximum=None):
        super(Capacity, self).__init__()
        CONF.import_opt("max_nodes_per_cluster", "senlin.common.config")

        if minimum > CONF.max_nodes_per_cluster:
            err = _("The value of 'minimum' cannot be greater than the global "
                    "constraint (%(m)d).") % {'m': CONF.max_nodes_per_cluster}
            raise ValueError(err)
        self.minimum = minimum

        if maximum is not None:
            if maximum < minimum:
                err = _("The value of 'maximum' must be greater than or equal "
                        "to that of the 'minimum' specified.")
                raise ValueError(err)

            if maximum > CONF.max_nodes_per_cluster:
                err = _("The value of 'maximum' cannot be greater than the "
                        "global constraint (%(m)d)."
                        ) % {'m': CONF.max_nodes_per_cluster}
                raise ValueError(err)

            self.maximum = maximum
        else:
            self.maximum = CONF.max_nodes_per_cluster

    def coerce(self, obj, attr, value):
        value = super(Capacity, self).coerce(obj, attr, value)

        err = None
        if value < self.minimum:
            err = _("The value for the %(a)s field must be greater than or "
                    "equal to %(n)d.") % {'a': attr, 'n': self.minimum}
        elif value > self.maximum:
            err = _("The value for the %(a)s field must be less than or equal "
                    "to %(n)d.") % {'a': attr, 'n': self.maximum}
        if err:
            raise ValueError(err)

        return value

    def get_schema(self):
        return {
            'type': ['integer', 'string'],
            'minimum': self.minimum,
            'maximum': self.maximum,
            'pattern': '^[0-9]*$',
        }


class Sort(fields.String):

    def __init__(self, valid_keys):
        super(Sort, self).__init__()
        self.valid_keys = valid_keys

    def coerce(self, obj, attr, value):
        for s in value.split(','):
            s_key, _sep, s_dir = s.partition(':')
            err = None
            if not s_key:
                err = _("missing sort key for '%s'.") % attr
                raise ValueError(err)

            if s_key not in self.valid_keys:
                err = _("unsupported sort key '%(value)s' for '%(attr)s'."
                        ) % {'attr': attr, 'value': s_key}

            if s_dir and s_dir not in ('asc', 'desc'):
                err = _("unsupported sort dir '%(value)s' for '%(attr)s'."
                        ) % {'attr': attr, 'value': s_dir}

            if err:
                raise ValueError(err)

        return super(Sort, self).coerce(obj, attr, value)

    def get_schema(self):
        return {
            'type': ['string'],
        }


class NameField(fields.AutoTypedField):

    AUTO_TYPE = Name()


class CapacityField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, nullable=True, default=None, minimum=0, maximum=None):
        self.AUTO_TYPE = Capacity(minimum=minimum, maximum=maximum)
        super(CapacityField, self).__init__(nullable=nullable, default=default)


class SortField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, valid_keys, nullable=True, default=None):
        self.AUTO_TYPE = Sort(valid_keys)
        super(SortField, self).__init__(nullable=nullable, default=default)
