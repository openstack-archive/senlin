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
import six

# Field alias for code readability
BooleanField = fields.BooleanField
StringField = fields.StringField
IntegerField = fields.IntegerField
FloatField = fields.FloatField
UUIDField = fields.UUIDField
DateTimeField = fields.DateTimeField
ListOfStringsField = fields.ListOfStringsField
ObjectField = fields.ObjectField


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
