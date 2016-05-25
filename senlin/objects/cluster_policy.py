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

"""Cluster-policy binding object."""

from oslo_versionedobjects import base
from oslo_versionedobjects import fields

from senlin.db import api as db_api
from senlin.objects import base as senlin_base


class ClusterPolicy(senlin_base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin cluster-policy binding object."""

    fields = {
        'id': fields.UUIDField(),
        'cluster_id': fields.UUIDField(),
        'policy_id': fields.UUIDField(),
        'cluster': fields.ObjectField('Cluster'),
        'policy': fields.ObjectField('Policy'),
        'enabled': fields.BooleanField(),
        'priority': fields.IntegerField(),
        'data': fields.DictOfStringField(),
        'last_op': fields.DateTimeField(),
    }

    @staticmethod
    def _from_db_object(context, binding, db_obj):
        for field in binding.fields:
            binding[field] = db_obj[field]

        binding._context = context
        binding.obj_reset_changes()

        return binding

    @classmethod
    def create(cls, context, cluster_id, policy_id, values):
        obj = db_api.cluster_policy_attach(context, cluster_id, policy_id,
                                           values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def get(cls, context, cluster_id, policy_id):
        obj = db_api.cluster_policy_get(context, cluster_id, policy_id)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_type(cls, context, cluster_id, policy_type, filters=None):
        obj = db_api.cluster_policy_get_by_type(context, cluster_id,
                                                policy_type, filters=filters)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, cluster_id, **kwargs):
        return db_api.cluster_policy_get_all(context, cluster_id, **kwargs)

    @classmethod
    def update(cls, context, cluster_id, policy_id, values):
        db_api.cluster_policy_update(context, cluster_id, policy_id, values)

    @classmethod
    def delete(cls, context, cluster_id, policy_id):
        db_api.cluster_policy_detach(context, cluster_id, policy_id)
