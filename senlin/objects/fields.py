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
from oslo_versionedobjects import fields
import re
import six

from senlin.common.i18n import _

# Field alias for code readability
BooleanField = fields.BooleanField
StringField = fields.StringField
IntegerField = fields.IntegerField
FloatField = fields.FloatField
UUIDField = fields.UUIDField
DateTimeField = fields.DateTimeField
ListOfStringsField = fields.ListOfStringsField


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
                err = _("The value for the %(attr)s: %(value)s contains "
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


class NameField(fields.AutoTypedField):

    AUTO_TYPE = Name()
