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

"""Credential object."""

from oslo_versionedobjects import base
from oslo_versionedobjects import fields

from senlin.db import api as db_api
from senlin.objects import base as senlin_base


class Credential(senlin_base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin credential object."""

    fields = {
        'user': fields.StringField(),
        'project': fields.StringField(),
        'cred': fields.DictOfStringsField(),
        'data': fields.DictOfStringsField(),
    }

    @staticmethod
    def _from_db_object(context, credential, db_obj):
        for field in credential.fields:
            credential[field] = db_obj[field]

        credential._context = context
        credential.obj_reset_changes()

        return credential

    @classmethod
    def create(cls, context, values):
        obj = db_api.cred_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def get(cls, context, user, project):
        obj = db_api.cred_get(context, user, project)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def update(cls, context, user, project, values):
        obj = db_api.cred_update(context, user, project, values)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def delete(cls, context, user, project):
        return db_api.cred_delete(context, user, project)

    @classmethod
    def update_or_create(cls, context, values):
        obj = db_api.cred_create_update(context, values)
        return cls._from_db_object(context, cls(), obj)
