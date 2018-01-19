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

"""Action object."""

from oslo_utils import uuidutils

from senlin.common import exception
from senlin.common import utils
from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import dependency as dobj
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Action(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin action object."""

    fields = {
        'id': fields.UUIDField(),
        'created_at': fields.DateTimeField(),
        'updated_at': fields.DateTimeField(nullable=True),
        'name': fields.StringField(),
        'context': fields.JsonField(),
        'target': fields.UUIDField(),
        'action': fields.StringField(),
        'cause': fields.StringField(),
        'owner': fields.UUIDField(nullable=True),
        'interval': fields.IntegerField(nullable=True),
        'start_time': fields.FloatField(nullable=True),
        'end_time': fields.FloatField(nullable=True),
        'timeout': fields.IntegerField(nullable=True),
        'status': fields.StringField(),
        'status_reason': fields.StringField(nullable=True),
        'control': fields.StringField(nullable=True),
        'inputs': fields.JsonField(nullable=True),
        'outputs': fields.JsonField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
    }

    @classmethod
    def create(cls, context, values):
        obj = db_api.action_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def find(cls, context, identity, **kwargs):
        """Find an action with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of an action.
        :param dict kwargs: Other query parameters.
        :return: A DB object of action or an exception `ResourceNotFound` if
                 no matching action is found.
        """
        if uuidutils.is_uuid_like(identity):
            action = cls.get(context, identity, **kwargs)
            if not action:
                action = cls.get_by_name(context, identity, **kwargs)
        else:
            action = cls.get_by_name(context, identity, **kwargs)
            if not action:
                action = cls.get_by_short_id(context, identity, **kwargs)

        if not action:
            raise exception.ResourceNotFound(type='action', id=identity)

        return action

    @classmethod
    def get(cls, context, action_id, **kwargs):
        obj = db_api.action_get(context, action_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.action_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.action_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        objs = db_api.action_get_all(context, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def get_all_by_owner(cls, context, owner):
        objs = db_api.action_get_all_by_owner(context, owner)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def check_status(cls, context, action_id, timestamp):
        return db_api.action_check_status(context, action_id, timestamp)

    @classmethod
    def mark_succeeded(cls, context, action_id, timestamp):
        return db_api.action_mark_succeeded(context, action_id, timestamp)

    @classmethod
    def mark_ready(cls, context, action_id, timestamp):
        return db_api.action_mark_ready(context, action_id, timestamp)

    @classmethod
    def mark_failed(cls, context, action_id, timestamp, reason=None):
        return db_api.action_mark_failed(context, action_id, timestamp, reason)

    @classmethod
    def mark_cancelled(cls, context, action_id, timestamp):
        return db_api.action_mark_cancelled(context, action_id, timestamp)

    @classmethod
    def acquire(cls, context, action_id, owner, timestamp):
        return db_api.action_acquire(context, action_id, owner, timestamp)

    @classmethod
    def acquire_random_ready(cls, context, owner, timestamp):
        return db_api.action_acquire_random_ready(context, owner, timestamp)

    @classmethod
    def acquire_first_ready(cls, context, owner, timestamp):
        return db_api.action_acquire_first_ready(context, owner, timestamp)

    @classmethod
    def abandon(cls, context, action_id, values=None):
        return db_api.action_abandon(context, action_id, values)

    @classmethod
    def signal(cls, context, action_id, value):
        return db_api.action_signal(context, action_id, value)

    @classmethod
    def signal_query(cls, context, action_id):
        return db_api.action_signal_query(context, action_id)

    @classmethod
    def lock_check(cls, context, action_id, owner=None):
        return db_api.action_lock_check(context, action_id, owner)

    @classmethod
    def update(cls, context, action_id, values):
        return db_api.action_update(context, action_id, values)

    @classmethod
    def delete(cls, context, action_id):
        db_api.action_delete(context, action_id)

    @classmethod
    def delete_by_target(cls, context, target, action=None,
                         action_excluded=None, status=None):
        """Delete an action with the target and other given params.

        :param target: The ID of the target cluster/node
        :param action: A list of actions to be included.
        :param action_excluded: A list of actions to be excluded.
        :param status: A list of statuses to be delete filtered.
        :return: None.
        """
        return db_api.action_delete_by_target(context, target, action=action,
                                              action_excluded=action_excluded,
                                              status=status)

    def to_dict(self):
        if self.id:
            dep_on = dobj.Dependency.get_depended(self.context, self.id)
            dep_by = dobj.Dependency.get_dependents(self.context, self.id)
        else:
            dep_on = []
            dep_by = []
        action_dict = {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'target': self.target,
            'cause': self.cause,
            'owner': self.owner,
            'interval': self.interval,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'depends_on': dep_on,
            'depended_by': dep_by,
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at),
            'data': self.data,
            'user': self.user,
            'project': self.project,
        }
        return action_dict
