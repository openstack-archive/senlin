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

from senlin.common import exception
from senlin.objects import cluster_policy as cpo


class ClusterPolicy(object):
    '''Object representing a binding between a cluster and a policy.

    This object also records the runtime data of a policy, if any.
    '''
    def __init__(self, cluster_id, policy_id, **kwargs):
        self.id = kwargs.get('id', None)

        self.cluster_id = cluster_id
        self.policy_id = policy_id
        self.enabled = kwargs.get('enabled')
        self.data = kwargs.get('data', {})
        self.priority = kwargs.get('priority')
        self.last_op = kwargs.get('last_op', None)

        # derived data from binding, put here for convenience
        self.cluster_name = kwargs.get('cluster_name', '')
        self.policy_name = kwargs.get('policy_name', '')
        self.policy_type = kwargs.get('policy_type', '')

    def store(self, context):
        '''Store the binding record into database table.'''
        values = {
            'enabled': self.enabled,
            'data': self.data,
            'last_op': self.last_op,
            'priority': self.priority
        }

        if self.id:
            cpo.ClusterPolicy.update(context, self.cluster_id, self.policy_id,
                                     values)
        else:
            binding = cpo.ClusterPolicy.create(context, self.cluster_id,
                                               self.policy_id, values)
            self.cluster_name = binding.cluster.name
            self.policy_name = binding.policy.name
            self.policy_type = binding.policy.type
            self.id = binding.id

        return self.id

    @classmethod
    def _from_object(cls, context, obj):
        """Construct a cluster policy binding from database object.

        :param context: the context used for DB operations;
        :param obj: a cluster-policy binding object that contains all fields;
        """
        kwargs = {
            'id': obj.id,
            'enabled': obj.enabled,
            'data': obj.data,
            'last_op': obj.last_op,
            'priority': obj.priority,

            # derived data
            'cluster_name': obj.cluster.name,
            'policy_name': obj.policy.name,
            'policy_type': obj.policy.type,
        }

        return cls(obj.cluster_id, obj.policy_id, context=context, **kwargs)

    @classmethod
    def load(cls, context, cluster_id, policy_id):
        '''Retrieve a cluster-policy binding from database.'''

        binding = cpo.ClusterPolicy.get(context, cluster_id, policy_id)
        if binding is None:
            raise exception.PolicyNotAttached(policy=policy_id,
                                              cluster=cluster_id)

        return cls._from_object(context, binding)

    def to_dict(self):
        binding_dict = {
            'id': self.id,
            'cluster_id': self.cluster_id,
            'policy_id': self.policy_id,
            'enabled': self.enabled,
            'data': self.data,
            'last_op': self.last_op,
            # below are derived data for user's convenience
            'cluster_name': self.cluster_name,
            'policy_name': self.policy_name,
            'policy_type': self.policy_type,
        }
        return binding_dict
