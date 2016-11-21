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


@base.SenlinObjectRegistry.register
class EventType(base.SenlinObject):
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


class NotificationPayloadBase(base.SenlinObject):
    """Base class for the payload of versioned notifications."""
    # schema is a dict that defines how to populate the payload fields, where
    # each key-value pair has the following format:
    #
    # <payload_field>: (<data_source>, <data_source_field>)
    #
    # The <payload_field> is the name where the data will be stored in the
    # payload object, this field has to be defined as a field of the payload.
    # The <data_source> field shall refer to name of the parameter passed as
    # kwarg to the payload's populate_schema() call and this object will be
    # used as the source of the data.
    # The 'schema' needs to be applied with the populate_schema() call before
    # the notification can be emitted.
    # The value of the payload.<payload_field> field will be set by the
    # <data_source>.<data_source_field> field. The <data_source> will not be
    # part of the payload object internal or external representation.
    # Payload fields that are not set by the schema can be filled in the same
    # way as in any versioned object.
    schema = {}
    VERSION = '1.0'

    def __init__(self, *args, **kwargs):
        super(NotificationPayloadBase, self).__init__(*args, **kwargs)
        self.populated = not self.schema

    def populate_schema(self, **kwargs):
        """Populate the object based on the schema and the source objects

        :param kwargs: A dict contains the source object at the key defined in
                       the schema
        """
        for key, (obj, field) in self.schema.items():
            source = kwargs[obj]
            if source.obj_attr_is_set(field):
                setattr(self, key, getattr(source, field))
        self.populated = True


@base.SenlinObjectRegistry.register
class NotificationPublisher(base.SenlinObject):
    VERSION = '1.0'

    fields = {
        'host': fields.StringField(nullable=False),
        'binary': fields.StringField(nullable=False),
    }

    @classmethod
    def from_service_obj(cls, service):
        return cls(host=service.host, binary=service.binary)


class NotificationBase(base.SenlinObject):
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
        notify(context, event_type=event_type, payload=payload)

    def emit(self, context):
        """Send the notification."""
        assert self.payload.populated

        # Note(gibi): notification payload will be a newly populated object
        # therefore every field of it will look changed so this does not carry
        # any extra information so we drop this from the payload.
        self.payload.obj_reset_changes(recursive=False)

        self._emit(context,
                   event_type=self.event_type.to_notification_field(),
                   publisher_id='%s:%s' %
                                (self.publisher.binary,
                                 self.publisher.host),
                   payload=self.payload.obj_to_primitive())


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
