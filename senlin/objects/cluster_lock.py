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

"""Cluster lock object."""

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class ClusterLock(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin cluster lock object."""

    fields = {
        'cluster_id': fields.UUIDField(),
        'action_ids': fields.ListOfStringsField(),
        'semaphore': fields.IntegerField(),
    }

    @classmethod
    def acquire(cls, cluster_id, action_id, scope):
        return db_api.cluster_lock_acquire(cluster_id, action_id, scope)

    @classmethod
    def release(cls, cluster_id, action_id, scope):
        return db_api.cluster_lock_release(cluster_id, action_id, scope)

    @classmethod
    def steal(cls, cluster_id, action_id):
        return db_api.cluster_lock_steal(cluster_id, action_id)
