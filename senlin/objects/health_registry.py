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

"""Health registry object."""

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class HealthRegistry(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin health registry object."""

    fields = {
        'id': fields.UUIDField(),
        'cluster_id': fields.UUIDField(),
        'check_type': fields.StringField(),
        'interval': fields.IntegerField(nullable=True),
        'params': fields.JsonField(nullable=True),
        'engine_id': fields.UUIDField(),
        'enabled': fields.BooleanField(),
    }

    @classmethod
    def create(cls, context, cluster_id, check_type, interval, params,
               engine_id, enabled=True):
        obj = db_api.registry_create(context, cluster_id, check_type,
                                     interval, params, engine_id,
                                     enabled=enabled)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def update(cls, context, cluster_id, values):
        db_api.registry_update(context, cluster_id, values)

    @classmethod
    def claim(cls, context, engine_id):
        objs = db_api.registry_claim(context, engine_id)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def delete(cls, context, cluster_id):
        db_api.registry_delete(context, cluster_id)

    @classmethod
    def get(cls, context, cluster_id):
        obj = db_api.registry_get(context, cluster_id)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_engine(cls, context, engine_id, cluster_id):
        params = {
            "cluster_id": cluster_id,
            "engine_id": engine_id,
        }
        obj = db_api.registry_get_by_param(context, params)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def disable_registry(cls, context, cluster_id):
        cls.update(context, cluster_id, {'enabled': False})

    @classmethod
    def enable_registry(cls, context, cluster_id):
        cls.update(context, cluster_id, {"enabled": True})
