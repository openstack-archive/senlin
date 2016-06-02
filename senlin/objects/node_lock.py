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

"""Node lock object."""

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class NodeLock(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin node lock object."""

    fields = {
        'node_id': fields.UUIDField(),
        'action_id': fields.UUIDField(),
    }

    @classmethod
    def acquire(cls, node_id, action_id):
        return db_api.node_lock_acquire(node_id, action_id)

    @classmethod
    def release(cls, node_id, action_id):
        return db_api.node_lock_release(node_id, action_id)

    @classmethod
    def steal(cls, node_id, action_id):
        return db_api.node_lock_steal(node_id, action_id)
