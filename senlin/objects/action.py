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

from senlin.db import api as db_api
from senlin.objects import base
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
    def mark_failed(cls, context, action_id, timestamp, reason=None):
        return db_api.action_mark_failed(context, action_id, timestamp, reason)

    @classmethod
    def mark_cancelled(cls, context, action_id, timestamp):
        return db_api.action_mark_cancelled(context, action_id, timestamp)

    @classmethod
    def acquire(cls, context, action_id, owner, timestamp):
        return db_api.action_acquire(context, action_id, owner, timestamp)

    @classmethod
    def acquire_1st_ready(cls, context, owner, timestamp):
        return db_api.action_acquire_1st_ready(context, owner, timestamp)

    @classmethod
    def abandon(cls, context, action_id):
        return db_api.action_abandon(context, action_id)

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
