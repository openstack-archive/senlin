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
from oslo_utils import strutils
from oslo_utils import uuidutils
from oslo_versionedobjects import fields
import re
import six

from senlin.common import consts
from senlin.common.i18n import _

CONF = cfg.CONF

# Field alias for code readability
# BooleanField = fields.BooleanField
FlexibleBooleanField = fields.FlexibleBooleanField
StringField = fields.StringField
IntegerField = fields.IntegerField
FloatField = fields.FloatField
UUIDField = fields.UUIDField
DateTimeField = fields.DateTimeField
DictOfStringsField = fields.DictOfStringsField
ListOfStringsField = fields.ListOfStringsField
ListOfEnumField = fields.ListOfEnumField


class Boolean(fields.FieldType):
    # NOTE: The following definition is much more stricter than the oslo
    #       version. Also note that the treatment of default values here:
    #       we are using the user specified default value when invoking
    #       the 'bool_from_string' until function.

    def __init__(self, default=False):
        super(Boolean, self).__init__()
        self._default = default

    def coerce(self, obj, attr, value):
        return strutils.bool_from_string(value, strict=True,
                                         default=self._default)

    def get_schema(self):
        return {'type': ['boolean']}


class NonNegativeInteger(fields.FieldType):
    # NOTE: This definition is kept because we want the error message from
    #       'int' conversion to be user friendly.
    @staticmethod
    def coerce(obj, attr, value):
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise ValueError(_("The value for %(attr)s must be an integer: "
                               "'%(value)s'.") %
                             {'attr': attr, 'value': value})
        if v < 0:
            err = _("Value must be >= 0 for field '%s'.") % attr
            raise ValueError(err)
        return v

    def get_schema(self):
        return {
            'type': ['integer', 'string'],
            'minimum': 0
        }


# Senlin has a stricter field checking for object fields.
class Object(fields.Object):

    def get_schema(self):
        schema = super(Object, self).get_schema()
        # we are not checking whether self._obj_name is registered, an
        # exception will be raised anyway if it is not registered.
        data_key = 'senlin_object.data'
        schema['properties'][data_key]['additionalProperties'] = False
        return schema


class UUID(fields.FieldType):

    _PATTERN = (r'^[a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]'
                r'{4}-?[a-fA-F0-9]{12}$')

    @staticmethod
    def coerce(obj, attr, value):
        if not uuidutils.is_uuid_like(value):
            msg = _("The value for %(attr)s is not a valid UUID: '%(value)s'."
                    ) % {'attr': attr, 'value': value}
            raise ValueError(msg)

        return str(value)

    def get_schema(self):
        return {'type': ['string'], 'pattern': self._PATTERN}


class Json(fields.FieldType):
    def coerce(self, obj, attr, value):
        if isinstance(value, six.string_types):
            try:
                return jsonutils.loads(value)
            except ValueError:
                msg = _("The value (%s) is not a valid JSON.") % value
                raise ValueError(msg)
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


class NotificationPriority(fields.Enum):

    # The priorities here are derived from oslo_messaging.notify.notifier
    ALL = consts.NOTIFICATION_PRIORITIES

    def __init__(self):
        super(NotificationPriority, self).__init__(self.ALL)


class NotificationPhase(fields.Enum):

    ALL = consts.NOTIFICATION_PHASES

    def __init__(self):
        super(NotificationPhase, self).__init__(self.ALL)


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
            regex = re.compile(u'^[a-zA-Z\u4e00-\u9fa5\d\.\_\~-]*$',
                               re.IGNORECASE)
            if not regex.search(value):
                err = _("The value for the '%(attr)s' (%(value)s) contains "
                        "illegal characters. It must contain only "
                        "alphanumeric or \"_-.~\" characters and must start "
                        "with letter."
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
        try:
            v = int(value)
        except Exception:
            raise ValueError(_("The value for %(attr)s must be an integer: "
                               "'%(value)s'.") %
                             {'attr': attr, 'value': value})
        if v < self.minimum:
            raise ValueError(_("The value for the %(a)s field must be greater "
                               "than or equal to %(n)d.") %
                             {'a': attr, 'n': self.minimum})
        elif v > self.maximum:
            raise ValueError(_("The value for the %(a)s field must be less "
                               "than or equal to %(n)d.") %
                             {'a': attr, 'n': self.maximum})
        return super(Capacity, self).coerce(obj, attr, v)

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
                err = _("Missing sort key for '%s'.") % attr
                raise ValueError(err)

            if s_key not in self.valid_keys:
                err = _("Unsupported sort key '%(value)s' for '%(attr)s'."
                        ) % {'attr': attr, 'value': s_key}

            if s_dir and s_dir not in ('asc', 'desc'):
                err = _("Unsupported sort dir '%(value)s' for '%(attr)s'."
                        ) % {'attr': attr, 'value': s_dir}

            if err:
                raise ValueError(err)

        return super(Sort, self).coerce(obj, attr, value)

    def get_schema(self):
        return {
            'type': ['string'],
        }


class IdentityList(fields.List):

    def __init__(self, element_type, min_items=0, unique=True, nullable=False,
                 **kwargs):
        super(IdentityList, self).__init__(element_type, **kwargs)
        self.min_items = min_items
        self.unique_items = unique
        self.nullable = nullable

    def coerce(self, obj, attr, value):
        res = super(IdentityList, self).coerce(obj, attr, value)
        if len(res) < self.min_items:
            raise ValueError(_("Value for '%(attr)s' must have at least "
                               "%(num)s item(s).") %
                             {'attr': attr, 'num': self.min_items})
        if len(set(res)) != len(res) and self.unique_items:
            raise ValueError(_("Items for '%(attr)s' must be unique") %
                             {'attr': attr})
        return res

    def get_schema(self):
        schema = super(IdentityList, self).get_schema()
        if self.nullable:
            schema['type'].append('null')
        schema['minItems'] = self.min_items
        schema['uniqueItems'] = self.unique_items
        return schema


class BaseEnum(fields.FieldType):
    # NOTE: We are not basing Enum on String because String is not working
    # correctly when handling None value.
    def __init__(self, nullable=False):
        valid_values = list(self.__class__.ALL)
        if not valid_values:
            raise ValueError(_("No list of valid values provided for enum."))

        for value in valid_values:
            if not isinstance(value, six.string_types):
                raise ValueError(_("Enum field only support string values."))

        self._valid_values = list(valid_values)
        self._nullable = nullable
        super(BaseEnum, self).__init__()

    def coerce(self, obj, attr, value):
        value = six.text_type(value)
        if value not in self._valid_values:
            raise ValueError(_("Value '%(value)s' is not acceptable for "
                               "field '%(attr)s'.") %
                             {'value': value, 'attr': attr})
        return value

    def stringify(self, value):
        if value is None:
            return None
        return '\'%s\'' % value


class AdjustmentType(BaseEnum):

    ALL = consts.ADJUSTMENT_TYPES

    def get_schema(self):
        return {'type': ['string'],
                'enum': self._valid_values}


class ClusterActionName(BaseEnum):

    ALL = consts.CLUSTER_ACTION_NAMES

    def get_schema(self):
        return {'type': ['string'],
                'enum': self._valid_values}


class ClusterStatus(BaseEnum):

    ALL = consts.CLUSTER_STATUSES


class NodeStatus(BaseEnum):

    ALL = consts.NODE_STATUSES


class ActionStatus(BaseEnum):

    ALL = consts.ACTION_STATUSES


class ReceiverType(BaseEnum):

    ALL = consts.RECEIVER_TYPES

    def get_schema(self):
        return {'type': ['string'],
                'enum': self._valid_values}


class UniqueDict(fields.Dict):

    def coerce(self, obj, attr, value):
        res = super(UniqueDict, self).coerce(obj, attr, value)
        new_nodes = res.values()
        if len(new_nodes) != len(set(new_nodes)):
            raise ValueError(_("Map contains duplicated values"))
        return res


# TODO(Qiming): remove this when oslo patch is released
# https://review.openstack.org/#/c/360095
class NonNegativeIntegerField(fields.AutoTypedField):

    AUTO_TYPE = NonNegativeInteger()


class BooleanField(fields.AutoTypedField):

    AUTO_TYPE = Boolean()


# An override to the oslo.versionedobjects version so that we are using
# our own Object definition.
class ObjectField(fields.AutoTypedField):

    def __init__(self, objtype, subclasses=False, **kwargs):
        self.AUTO_TYPE = Object(objtype, subclasses)
        self.objname = objtype
        super(ObjectField, self).__init__(**kwargs)


class JsonField(fields.AutoTypedField):
    AUTO_TYPE = Json()


class ListField(fields.AutoTypedField):
    AUTO_TYPE = fields.List(fields.FieldType())


class NotificationPriorityField(fields.BaseEnumField):
    AUTO_TYPE = NotificationPriority()


class NotificationPhaseField(fields.BaseEnumField):
    AUTO_TYPE = NotificationPhase()


class NameField(fields.AutoTypedField):

    AUTO_TYPE = Name()


class UUIDField(fields.AutoTypedField):

    AUTO_TYPE = UUID()


class CapacityField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, nullable=False, default=None, minimum=0, maximum=None):
        self.AUTO_TYPE = Capacity(minimum=minimum, maximum=maximum)
        super(CapacityField, self).__init__(nullable=nullable, default=default)


class SortField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, valid_keys, nullable=False, default=None):
        self.AUTO_TYPE = Sort(valid_keys)
        super(SortField, self).__init__(nullable=nullable, default=default)


class IdentityListField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, min_items=0, unique=True, nullable=False, default=None):
        if default is None:
            default = []
        self.AUTO_TYPE = IdentityList(fields.String(), min_items=min_items,
                                      unique=unique)
        super(IdentityListField, self).__init__(nullable=nullable,
                                                default=default)


class AdjustmentTypeField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, **kwargs):
        nullable = kwargs.get('nullable', False)
        self.AUTO_TYPE = AdjustmentType(nullable=nullable)
        super(AdjustmentTypeField, self).__init__(**kwargs)


class ClusterActionNameField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, **kwargs):
        nullable = kwargs.get('nullable', False)
        self.AUTO_TYPE = ClusterActionName(nullable=nullable)
        super(ClusterActionNameField, self).__init__(**kwargs)


class ClusterStatusField(fields.AutoTypedField):

    AUTO_TYPE = ClusterStatus


class NodeStatusField(fields.AutoTypedField):

    AUTO_TYPE = NodeStatus


class ActionStatusField(fields.AutoTypedField):

    AUTO_TYPE = ActionStatus


class ReceiverTypeField(fields.AutoTypedField):

    AUTO_TYPE = None

    def __init__(self, **kwargs):
        nullable = kwargs.get('nullable', False)
        self.AUTO_TYPE = ReceiverType(nullable=nullable)
        super(ReceiverTypeField, self).__init__(**kwargs)


class NodeReplaceMapField(fields.AutoTypedField):

    AUTO_TYPE = UniqueDict(fields.String())
