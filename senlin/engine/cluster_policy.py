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

from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import exception
from senlin.db import api as db_api

LOG = logging.getLogger(__name__)


class ClusterPolicy(object):
    '''Object representing a binding between a cluster and a policy.

    This object also records the runtime data of a policy, if any.
    '''
    def __init__(self, cluster_id, policy_id, **kwargs):
        self.id = kwargs.get('id', None)

        self.cluster_id = cluster_id
        self.policy_id = policy_id
        self.priority = kwargs.get('priority')
        self.cooldown = kwargs.get('cooldown')
        self.level = kwargs.get('level')
        self.enabled = kwargs.get('enabled')
        self.data = kwargs.get('data', {})
        self.last_op = kwargs.get('last_op', None)

        # derived data from binding, put here for convenience
        self.cluster_name = kwargs.get('cluster_name', '')
        self.policy_name = kwargs.get('policy_name', '')
        self.policy_type = kwargs.get('policy_type', '')

    def store(self, context):
        '''Store the binding record into database table.'''
        values = {
            'priority': self.priority,
            'cooldown': self.cooldown,
            'level': self.level,
            'enabled': self.enabled,
            'data': self.data,
            'last_op': self.last_op,
        }

        if self.id:
            db_api.cluster_policy_update(context, self.cluster_id,
                                         self.policy_id, values)
        else:
            binding = db_api.cluster_policy_attach(context, self.cluster_id,
                                                   self.policy_id, values)
            self.cluster_name = binding.cluster.name
            self.policy_name = binding.policy.name
            self.policy_type = binding.policy.type
            self.id = binding.id

        return self.id

    @classmethod
    def _from_db_record(cls, context, record):
        '''Construct a node object from database record.

        :param context: the context used for DB operations;
        :param record: a DB node object that contains all fields;
        '''
        kwargs = {
            'id': record.id,
            'priority': record.priority,
            'cooldown': record.cooldown,
            'level': record.level,
            'enabled': record.enabled,
            'data': record.data,
            'last_op': record.last_op,

            # derived data
            'cluster_name': record.cluster.name,
            'policy_name': record.policy.name,
            'policy_type': record.policy.type,
        }

        return cls(record.cluster_id, record.policy_id, context=context,
                   **kwargs)

    @classmethod
    def load(cls, context, cluster_id, policy_id):
        '''Retrieve a cluster-policy binding from database.'''

        binding = db_api.cluster_policy_get(context, cluster_id, policy_id)
        if binding is None:
            raise exception.PolicyNotAttached(policy=policy_id,
                                              cluster=cluster_id)

        return cls._from_db_record(context, binding)

    @classmethod
    def load_all(cls, context, cluster_id, filters=None,
                 sort_keys=None, sort_dir=None):
        '''Retrieve all policies attached to a specific cluster.'''
        bindings = db_api.cluster_policy_get_all(context, cluster_id,
                                                 filters=filters,
                                                 sort_keys=sort_keys,
                                                 sort_dir=sort_dir)

        return [cls._from_db_record(context, b) for b in bindings]

    def cooldown_inprogress(self):
        if self.cooldown and self.last_op:
            if timeutils.is_older_than(self.last_op, self.cooldown):
                return True

        return False

    def record_last_op(self, context):
        self.last_op = timeutils.utcnow()
        self.store(context)

    def to_dict(self):
        binding_dict = {
            'id': self.id,
            'cluster_id': self.cluster_id,
            'policy_id': self.policy_id,
            'cooldown': self.cooldown,
            'priority': self.priority,
            'level': self.level,
            'enabled': self.enabled,
            'data': self.data,
            'last_op': self.last_op,
            # below are derived data for user's convenience
            'cluster_name': self.cluster_name,
            'policy_name': self.policy_name,
            'policy_type': self.policy_type,
        }
        return binding_dict
