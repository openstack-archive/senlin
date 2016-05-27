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

"""Cluster object."""

from oslo_versionedobjects import base
from oslo_versionedobjects import fields

from senlin.db import api as db_api
from senlin.objects import base as senlin_base


class Cluster(senlin_base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin cluster object."""

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'profile_id': fields.UUIDField(),
        'parent': fields.UUIDField(nullable=True),
        'init_at': fields.DateTimeField(nullable=True),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'min_size': fields.IntegerField(nullable=True),
        'max_size': fields.IntegerField(nullable=True),
        'desired_capacity': fields.IntegerField(nullable=True),
        'next_index': fields.IntegerField(),
        'timeout': fields.IntegerField(),
        'status': fields.StringField(),
        'status_reason': fields.StringField(),
        'metadata': fields.DictOfStringsField(),
        'data': fields.DictOfStringsField(),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, cluster, db_obj):
        if db_obj is None:
            return None

        for field in cluster.fields:
            if field == 'metadata':
                cluster['metadata'] = db_obj['meta_data']
            else:
                cluster[field] = db_obj[field]

        cluster._context = context
        cluster.obj_reset_changes()

        return cluster

    @classmethod
    def create(cls, context, values):
        obj = db_api.cluster_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def get(cls, context, cluster_id, **kwargs):
        obj = db_api.cluster_get(context, cluster_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.cluster_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.cluster_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        return db_api.cluster_get_all(context, **kwargs)

    @classmethod
    def next_index(cls, context, cluster_id):
        return db_api.cluster_next_index(context, cluster_id)

    @classmethod
    def count_all(cls, context, **kwargs):
        return db_api.cluster_count_all(context, **kwargs)

    @classmethod
    def update(cls, context, obj_id, values):
        db_api.cluster_update(context, obj_id, values)

    @classmethod
    def delete(cls, context, obj_id):
        db_api.cluster_delete(context, obj_id)
