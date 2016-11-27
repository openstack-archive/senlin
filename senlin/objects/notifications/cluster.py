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

from senlin.objects import base as senlin_base
from senlin.objects import fields
from senlin.objects.notifications import base


@senlin_base.SenlinObjectRegistry.register_notification
class ClusterPayload(base.NotificationObject):

    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'profile_id': fields.UUIDField(),
        'parent': fields.UUIDField(nullable=True),
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
            if cluster.obj_attr_is_set(field):
                values[field] = getattr(cluster, field)
        obj = cls(**values)
        obj.obj_reset_changes(recursive=False)
        return obj


@senlin_base.SenlinObjectRegistry.register_notification
class ActionPayload(base.NotificationObject):

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
            if action.obj_attr_is_set(field):
                values[field] = getattr(action, field)
        obj = cls(**values)
        obj.obj_reset_changes(recursive=False)
        return obj


@senlin_base.SenlinObjectRegistry.register_notification
class ClusterActionPayload(base.NotificationObject):

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


@senlin_base.SenlinObjectRegistry.register_notification
class ClusterActionNotification(base.NotificationBase):

    VERSION = '1.0'

    fields = {
        'payload': fields.ObjectField('ClusterActionPayload')
    }
