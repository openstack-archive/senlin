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

import inspect

import six

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
        'action': fields.StringField(nullable=False),
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
                   self.event_type.to_notification_field(),
                   self.publisher.publisher_id,
                   self.payload.obj_to_primitive())


@base.SenlinObjectRegistry.register_notification
class ExceptionPayload(NotificationObject):

    VERSION = '1.0'

    fields = {
        'module': fields.StringField(),
        'function': fields.StringField(),
        'exception': fields.StringField(),
        'message': fields.StringField(),
    }

    @classmethod
    def from_exception(cls, exc):
        if exc is None:
            return None
        trace = inspect.trace()[-1]
        module = inspect.getmodule(trace[0])
        module_name = module.__name__ if module else 'unknown'
        return cls(function=trace[3], module=module_name,
                   exception=exc.__class__.__name__,
                   message=six.text_type(exc))


@base.SenlinObjectRegistry.register_notification
class ClusterPayload(NotificationObject):

    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'profile_id': fields.UUIDField(),
        'init_at': fields.DateTimeField(),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'min_size': fields.IntegerField(),
        'max_size': fields.IntegerField(),
        'desired_capacity': fields.IntegerField(),
        'timeout': fields.IntegerField(),
        'status': fields.StringField(),
        'status_reason': fields.StringField(),
        'metadata': fields.JsonField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
        'dependents': fields.JsonField(nullable=True),
    }

    @classmethod
    def from_cluster(cls, cluster):
        values = {}
        for field in cls.fields:
            values[field] = getattr(cluster, field)
        obj = cls(**values)
        obj.obj_reset_changes(recursive=False)
        return obj


@base.SenlinObjectRegistry.register_notification
class NodePayload(NotificationObject):

    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'profile_id': fields.UUIDField(),
        'cluster_id': fields.StringField(),
        'physical_id': fields.StringField(nullable=True),
        'index': fields.IntegerField(),
        'role': fields.StringField(nullable=True),
        'init_at': fields.DateTimeField(),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'status': fields.StringField(),
        'status_reason': fields.StringField(),
        'metadata': fields.JsonField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
        'dependents': fields.JsonField(nullable=True),
    }

    @classmethod
    def from_node(cls, node):
        values = {}
        for field in cls.fields:
            values[field] = getattr(node, field)
        obj = cls(**values)
        obj.obj_reset_changes(recursive=False)
        return obj


@base.SenlinObjectRegistry.register_notification
class ActionPayload(NotificationObject):

    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'created_at': fields.DateTimeField(nullable=True),
        'target': fields.UUIDField(),
        'action': fields.StringField(),
        'start_time': fields.FloatField(),
        'end_time': fields.FloatField(nullable=True),
        'timeout': fields.IntegerField(nullable=True),
        'status': fields.StringField(),
        'status_reason': fields.StringField(),
        'inputs': fields.JsonField(nullable=True),
        'outputs': fields.JsonField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
    }

    @classmethod
    def from_action(cls, action):
        values = {}
        for field in cls.fields:
            values[field] = getattr(action, field)
        obj = cls(**values)
        obj.obj_reset_changes(recursive=False)
        return obj


@base.SenlinObjectRegistry.register_notification
class ClusterActionPayload(NotificationObject):

    VERSION = '1.0'

    fields = {
        'cluster': fields.ObjectField('ClusterPayload'),
        'action': fields.ObjectField('ActionPayload'),
        'exception': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, cluster, action, **kwargs):
        ex = kwargs.pop('exception', None)
        super(ClusterActionPayload, self).__init__(
            cluster=ClusterPayload.from_cluster(cluster),
            action=ActionPayload.from_action(action),
            exception=ex,
            **kwargs)


@base.SenlinObjectRegistry.register_notification
class NodeActionPayload(NotificationObject):

    VERSION = '1.0'

    fields = {
        'node': fields.ObjectField('NodePayload'),
        'action': fields.ObjectField('ActionPayload'),
        'exception': fields.ObjectField('ExceptionPayload', nullable=True),
    }

    def __init__(self, node, action, **kwargs):
        ex = kwargs.pop('exception', None)
        super(NodeActionPayload, self).__init__(
            node=NodePayload.from_node(node),
            action=ActionPayload.from_action(action),
            exception=ex,
            **kwargs)


@base.SenlinObjectRegistry.register_notification
class ClusterActionNotification(NotificationBase):

    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('ClusterActionPayload')
    }


@base.SenlinObjectRegistry.register_notification
class NodeActionNotification(NotificationBase):

    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('NodeActionPayload')
    }
