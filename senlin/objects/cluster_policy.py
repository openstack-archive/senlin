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

from oslo_utils import timeutils

from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import cluster as cluster_obj
from senlin.objects import fields
from senlin.objects import policy as policy_obj


@base.SenlinObjectRegistry.register
class ClusterPolicy(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin cluster-policy binding object."""

    fields = {
        'id': fields.UUIDField(),
        'cluster_id': fields.UUIDField(),
        'policy_id': fields.UUIDField(),
        'cluster': fields.ObjectField('Cluster', nullable=True),
        'policy': fields.ObjectField('Policy', nullable=True),
        'enabled': fields.BooleanField(),
        'priority': fields.IntegerField(),
        'data': fields.JsonField(nullable=True),
        'last_op': fields.DateTimeField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, binding, db_obj):
        if db_obj is None:
            return None
        for field in binding.fields:
            if field == 'cluster':
                c = cluster_obj.Cluster.get(context, db_obj['cluster_id'])
                binding['cluster'] = c
            elif field == 'policy':
                p = policy_obj.Policy.get(context, db_obj['policy_id'])
                binding['policy'] = p
            else:
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
        objs = db_api.cluster_policy_get_by_type(context, cluster_id,
                                                 policy_type, filters=filters)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def get_all(cls, context, cluster_id, **kwargs):
        objs = db_api.cluster_policy_get_all(context, cluster_id, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def update(cls, context, cluster_id, policy_id, values):
        db_api.cluster_policy_update(context, cluster_id, policy_id, values)

    @classmethod
    def delete(cls, context, cluster_id, policy_id):
        db_api.cluster_policy_detach(context, cluster_id, policy_id)

    def cooldown_inprogress(self, cooldown):
        last_op = self.last_op
        if last_op and not timeutils.is_older_than(last_op, cooldown):
            return True

        return False

    def to_dict(self):
        binding_dict = {
            'id': self.id,
            'cluster_id': self.cluster.id,
            'policy_id': self.policy.id,
            'enabled': self.enabled,
            'data': self.data,
            'last_op': self.last_op,
            'priority': self.priority,
            # below are derived data for user's convenience
            'cluster_name': self.cluster.name,
            'policy_name': self.policy.name,
            'policy_type': self.policy.type,
        }
        return binding_dict
