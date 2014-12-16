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

import uuid
from senlin.engine import Node

class Cluster(object):
    '''
    A cluster is a set of homogeneous objects of the same profile.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    statuses = (
        ACTIVE, ERROR, DELETED, UPDATING,
    ) = (
        'ACTIVE', 'ERROR', 'DELETED', 'UPDATING',
    )

    def __init__(self, name, size, profile_type, **kwargs):
        self.name = name
        self.size = size
        self.profile_type = profile_type
        self.uuid = str(uuid.uuid4())
        self.nodes = {}
        self.policies = {}
        self.domain = kwargs.get('domain')
        self.project = kwargs.get('project')
        self.user = kwargs.get('user')
        self.parent = None
        self.status = self.ACTIVE
        self.status_reason = 'Initialized'
        self._next_index = 0
        self.tags = {}

    @classmethod
    def create(cls, name, size, profile_type, **kwargs):
        cluster = cls(name, size, profile_type, kwargs)
        # TODO: store this to database
        # TODO: log events?
        return cluster.uuid

    @classmethod
    def delete(cls, cluster_id):
        cluster = db_api.get_cluster(cluster_id)

        # TODO: check if actions are working on and can be canceled
        # TODO: destroy nodes 

        db_api.delete_cluster(cluster_id)
        del cluster
        return True

    def next_index(self):
        curr = self._next_index
        self._next_index = self._next_index + 1
        return curr

    def get_nodes(self):
        # This method will return each node with their associated profiles.
        # Members may have different versions of the same profile type.
        return {} 

    def get_policies(self):
        # policies are stored in database when policy association is created
        # this method retrieves the attached policies from database
        return {}

    def add_nodes(self, node_ids):
        pass

    def del_nodes(self, node_ids):
        for node in node_ids:
            res = Node.destroy(node)
        return True

    def attach_policy(self, policy_id):
        '''
        Attach specified policy instance to this cluster.
        '''
        # TODO: check conflicts with existing policies
        self.policies.append(policy_id)

    def detach_policy(self, policy_id):
        # TODO: check if actions of specified policies are ongoing
        self.policies.remove(policy_id)
