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
from senlin.engine import node
from senlin.rpc import api as rpc_api


class Cluster(object):
    '''
    A cluster is a set of homogeneous objects of the same profile.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    statuses = (
        INIT, ACTIVE, ERROR, DELETED, UPDATING,
    ) = (
        'INIT', 'ACTIVE', 'ERROR', 'DELETED', 'UPDATING',
    )

    def __init__(self, name, profile, size=0, **kwargs):
        '''
        Intialize a cluster object.
        The cluster defaults to have 0 nodes with no profile assigned.
        '''
        self.name = name
        self.profile_id = profile_id

        self.user = kwargs.get('user')
        self.project = kwargs.get('project')
        self.domain = kwargs.get('domain')

        self.parent = kwargs.get('parent') 

        self.created_time = None
        self.updated_time = None
        self.deleted_time = None

        self.next_index = 0
        self.timeout = 0

        self.status = ''
        self.status_reason = ''
        self.tags = {}

        # persist object into database very early because:
        # 1. object creation may be a time consuming task
        # 2. user may want to cancel the action when cluster creation
        #    is still in progress
        db_api.create_cluster(self)

        # rt is a dict for runtime data
        self.rt = {
            size = size,
            nodes = {},
            policies = {}
        }

    def _set_status(self, context, status):
        pass
        #event.info(context, self.id, status, 
        # log status to log file
        # generate event record

    def do_create(self, context, **kwargs):
        '''
        A routine to be called from an action by a thread.
        '''
        for m in range[self.size]:
           action = MemberAction(cluster_id, profile, 'CREATE', **kwargs) 
           # start a thread asynchnously
           handle = scheduler.runAction(action) 
           scheduler.wait(handle)

        self._set_status(self.ACTIVE)

    def do_delete(self, **kwargs):
        self.status = self.DELETED

    def do_update(self, **kwargs):
        # Profile type checking is done here because the do_update logic can 
        # be triggered from API or Webhook
        # TODO: check if profile is of the same type
        profile = kwargs.get('profile')
        if self.profile == profile:
            event.warning(_LW('Cluster refuses to update to the same profile'
                              '(%s)' % (profile)))
            return self.FAILED

        self._set_status(self.UPDATING)

        for m in range[self.size]:
           action = MemberAction(cluster_id, profile, 'CREATE', **kwargs) 
           # start a thread asynchronously
           handle = scheduler.runAction(action) 
           scheduler.wait(handle)

        self._set_status(self.ACTIVE)

    def get_next_index(self):
        # TODO: Get next_index from db and increment it in db
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
        return cluster.id

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
       
        return True

    @classmethod
    def load(cls, context, cluster_id=None, cluster=None, show_deleted=True):
        '''Retrieve a Cluster from the database.'''
        if cluster is None:
            cluster = db_api.cluster_get(context, cluster_id,
                                         show_deleted=show_deleted)

        if cluster is None:
            message = _('No cluster exists with id "%s"') % str(cluster_id)
            raise exception.NotFound(message)

        return cls._from_db(context, cluster)

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, tenant_safe=True,
                 show_deleted=False, show_nested=False):
        clusters = db_api.cluster_get_all(context, limit, sort_keys, marker,
                                          sort_dir, filters, tenant_safe,
                                          show_deleted, show_nested) or []
        for cluster in clusters:
            yield cls._from_db(context, cluster)

    @classmethod
    def _from_db(cls, context, cluster):
        # TODO: calculate current size based on nodes
        size = self.size
        return cls(context, cluster.name, cluster.profile, size,
                   id=cluster.id, status=cluster.status,
                   status_reason=cluster_status_reason,
                   parent=cluster.parent,
                   project=cluster.project,
                   created_time=cluster.created_time,
                   updated_time=cluster.updated_time,
                   deleted_time=cluster.deleted_time,
                   domain = cluster.domain,
                   timeout = cluster.timeout,
                   user=cluster.user)

    def to_dict(self):
        info = {
            rpc_api.CLUSTER_NAME: self.name,
            rpc_api.CLUSTER_PROFILE: self.profile,
            rpc_api.CLUSTER_SIZE: self.size,
            rpc_api.CLUSTER_UUID: self.id,
            rpc_api.CLUSTER_PARENT: self.parent,
            rpc_api.CLUSTER_DOMAIN: self.domain,
            rpc_api.CLUSTER_PROJECT: self.project,
            rpc_api.CLUSTER_USER: self.user,
            rpc_api.CLUSTER_CREATED_TIME: self.created_time,
            rpc_api.CLUSTER_UPDATED_TIME: self.updated_time,
            rpc_api.CLUSTER_DELETED_TIME: self.deleted_time,
            rpc_api.CLUSTER_STATUS: self.status,
            rpc_api.CLUSTER_STATUS_REASON: self.status_reason,
            rpc_api.CLUSTER_TIMEOUT: self.timeout,
        }
   
        return info
