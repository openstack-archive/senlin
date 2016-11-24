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

from senlin.common import messaging
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register_if(False)
class NotificationObject(base.SenlinObject):
    """Base class for all notification related versioned objects."""
    VERSION = '1.0'

    def __init__(self, **kwargs):
        # The notification objects are created on the fly so every field is
        # shown as changed. We reset the object after creation to avoid
        # sending such meaningless information.
        super(NotificationObject, self).__init__(**kwargs)
        self.obj_reset_changes(recursive=False)


@base.SenlinObjectRegistry.register_notification
class EventType(NotificationObject):
    VERSION = '1.0'

    fields = {
        'object': fields.StringField(nullable=False),
        'action': fields.NotificationActionField(nullable=False),
        'phase': fields.NotificationPhaseField(nullable=True),
    }

    def to_notification_field(self):
        """Serialize the object to the wire format."""
        s = '%s.%s' % (self.object, self.action)
        if self.obj_attr_is_set('phase'):
            s += '.%s' % self.phase
        return s


@base.SenlinObjectRegistry.register_notification
class NotificationPublisher(NotificationObject):
    VERSION = '1.0'

    fields = {
        'host': fields.StringField(),
        'binary': fields.StringField(),
    }

    @classmethod
    def from_service(cls, service):
        return cls(host=service.host, binary=service.binary)

    @property
    def publisher_id(self):
        return '%s:%s' % (self.binary, self.host)


@base.SenlinObjectRegistry.register_if(False)
class NotificationBase(NotificationObject):
    """Base class for versioned notifications.

    Every subclass shall define a 'payload' field.
    """
    VERSION = '1.0'

    fields = {
        'priority': fields.NotificationPriorityField(),
        'event_type': fields.ObjectField('EventType'),
        'publisher': fields.ObjectField('NotificationPublisher'),
    }

    def _emit(self, context, event_type, publisher_id, payload):
        notifier = messaging.get_notifier(publisher_id)
        notify = getattr(notifier, self.priority)
        notify(context, event_type, payload)

    def emit(self, context):
        """Send the notification."""
        self.payload.obj_reset_changes(recursive=False)
        self._emit(context,
                   event_type=self.event_type.to_notification_field(),
                   publisher_id=self.publisher.publisher_id,
                   payload=self.payload.obj_to_primitive())


# TODO(Qiming): revisit this and see if we should remove it
def notification_sample(sample):
    """Class decorator for documentation generation.

    This decorator is used to attach the notification sample information
    to the notification object for documentation generation purposes.

    :param sample: the path of the sample json file relative to the
                   doc/notification_samples/ directory in the nova repository
                   root.
    """
    def wrap(cls):
        cls.sample = sample
        return cls
    return wrap
