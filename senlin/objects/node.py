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

"""Node object."""

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Node(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin node object."""

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'profile_id': fields.UUIDField(),
        # This field is treated as string because we may store '' into it
        'cluster_id': fields.StringField(),
        'physical_id': fields.UUIDField(nullable=True),
        'index': fields.IntegerField(),
        'role': fields.StringField(nullable=True),
        'init_at': fields.DateTimeField(),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'status': fields.StringField(),
        'status_reason': fields.StringField(nullable=True),
        'metadata': fields.JsonField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
    }

    @classmethod
    def create(cls, context, values):
        obj = db_api.node_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def get(cls, context, node_id, **kwargs):
        obj = db_api.node_get(context, node_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.node_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.node_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        objs = db_api.node_get_all(context, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def get_all_by_cluster(cls, context, cluster_id, **kwargs):
        objs = db_api.node_get_all_by_cluster(context, cluster_id, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def count_by_cluster(cls, context, cluster_id, **kwargs):
        return db_api.node_count_by_cluster(context, cluster_id, **kwargs)

    @classmethod
    def update(cls, context, obj_id, values):
        db_api.node_update(context, obj_id, values)

    @classmethod
    def migrate(cls, context, obj_id, to_cluster, timestamp, role=None):
        return db_api.node_migrate(context, obj_id, to_cluster, timestamp,
                                   role=role)

    @classmethod
    def delete(cls, context, obj_id):
        db_api.node_delete(context, obj_id)
