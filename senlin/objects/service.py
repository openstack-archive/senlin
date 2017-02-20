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

"""Service object."""

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Service(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin service object."""

    fields = {
        'id': fields.UUIDField(),
        'host': fields.StringField(),
        'binary': fields.StringField(),
        'topic': fields.StringField(),
        'disabled': fields.BooleanField(),
        'disabled_reason': fields.StringField(nullable=True),
        'created_at': fields.DateTimeField(),
        'updated_at': fields.DateTimeField(),
    }

    @classmethod
    def create(cls, context, service_id, host=None, binary=None, topic=None):
        obj = db_api.service_create(service_id, host=host, binary=binary,
                                    topic=topic)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def get(cls, context, service_id):
        obj = db_api.service_get(service_id)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context):
        objs = db_api.service_get_all()
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def update(cls, context, obj_id, values=None):
        obj = db_api.service_update(obj_id, values=values)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def delete(cls, obj_id):
        db_api.service_delete(obj_id)

    @classmethod
    def gc_by_engine(cls, engine_id):
        db_api.gc_by_engine(engine_id)
