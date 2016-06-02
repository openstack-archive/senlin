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

"""Action dependency object."""

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Dependency(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin action dependency object."""

    fields = {
        'id': fields.UUIDField(),
        'depended': fields.UUIDField(),
        'dependent': fields.UUIDField(),
    }

    @classmethod
    def create(cls, context, depended, dependent):
        return db_api.dependency_add(context, depended, dependent)

    @classmethod
    def get_depended(cls, context, action_id):
        return db_api.dependency_get_depended(context, action_id)

    @classmethod
    def get_dependents(cls, context, action_id):
        return db_api.dependency_get_dependents(context, action_id)
