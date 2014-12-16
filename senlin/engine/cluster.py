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
from datetime import datetime

from senlin.db import api as db_api
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
        'INIT', 'ACTIVE', 'ERROR', 'DELETED', 'UPDATING',
    )

    def __init__(self, name, size=0, profile=None, **kwargs):
        '''
        Intialize a cluster object.
        The cluster defaults to have 0 nodes with no profile assigned.
        '''
        self.name = name
        self.size = size
        self.profile = profile
        self.uuid = str(uuid.uuid4())
        self.nodes = {}
        self.policies = {}
        self.domain = kwargs.get('domain')
        self.project = kwargs.get('project')
        self.user = kwargs.get('user')
        self.parent = kwargs.get('parent') 
        self.status = self.None
        self.created_time = None
        self._next_index = 0
        self.tags = {}

        # persist object into database very early because:
        # 1. object creation may be a time consuming task
        # 2. user may want to cancel the action when cluster creation
        #    is still in progress
        db_api.create_cluster(self)

    def _set_status(self, status):
        # log status to log file
        # generate event record

    def do_create(self, **kwargs):
        '''
        A routine to be called from an action by a thread.
        '''
        # TODO: Fork-join
        for m in range[self.size]:
           action = MemberAction(cluster_id, profile, 'CREATE', **kwargs) 
           # start a thread asynchnously
           handle = scheduler.runAction(action) 
           scheduler.wait(handle)

        self._set_status(self.ACTIVE)

    def do_delete(self, **kwargs):
        self.status = self.DELETED

    def do_update(self, **kwargs):
        self.status = self.UPDATING

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

    @classmethod
    def create(cls, name, size=0, profile=None, **kwargs):
        cluster = cls(name, size, profile, kwargs)
        cluster.do_create()
        # TODO: store this to database
        # TODO: log events?
        return cluster.uuid

    @classmethod
    def delete(cls, cluster_id):
        cluster = db_api.get_cluster(cluster_id)

        # TODO: check if actions are working on and can be canceled
        # TODO: destroy nodes 

        db_api.delete_cluster(cluster_id)
        return True

    @classmethod
    def update(cls, cluster_id, profile):
        cluster = db_api.get_cluster(cluster_id)

        # TODO: Implement this
        # 1. check if profile is of the same type
        # 2. fork UPDATE action for this cluster
        
        return True
