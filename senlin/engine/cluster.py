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

import datetime

from senlin.common.i18n import _
from senlin.common.i18n import _LW
from senlin.db import api as db_api
from senlin.engine import event as events
from senlin.engine import node as nodes
from senlin.openstack.common import periodic_task
from senlin.profiles import base as profiles


class Cluster(periodic_task.PeriodicTasks):
    '''
    A cluster is a set of homogeneous objects of the same profile.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    statuses = (
        INIT, CREATING, ACTIVE, ERROR, DELETING, DELETED,
        UPDATING, UPDATE_CANCELLED,
    ) = (
        'INIT', 'CREATING', 'ACTIVE', 'ERROR', 'DELETING', 'DELETED',
        'UPDATING', 'UPDATE_CANCELLED',
    )

    def __init__(self, name, profile_id, size=0, **kwargs):
        '''
        Intialize a cluster object.
        The cluster defaults to have 0 nodes with no profile assigned.
        '''
        self.id = kwargs.get('id', None)
        self.name = name
        self.profile_id = profile_id

        # Initialize the fields using kwargs passed in
        self.user = kwargs.get('user', '')
        self.project = kwargs.get('project', '')
        self.domain = kwargs.get('domain', '')
        self.parent = kwargs.get('parent', '')

        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        # size is only the 'desired capacity', which many not be the real
        # size of the cluster at a moment.
        self.size = size
        self.next_index = kwargs.get('next_index', 0)
        self.timeout = kwargs.get('timeout', 0)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.tags = kwargs.get('tags', {})

        # rt is a dict for runtime data
        # TODO(Qiming): nodes have to be reloaded when membership changes
        self.rt = {}

    @classmethod
    def _from_db_record(cls, record):
        '''
        Construct a cluster object from database record.
        :param context: the context used for DB operations;
        :param record: a DB cluster object that will receive all fields;
        '''
        kwargs = {
            'id': record.id,
            'user': record.user,
            'project': record.project,
            'domain': record.domain,
            'parent': record.parent,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
            'next_index': record.next_index,
            'timeout': record.timeout,
            'status': record.status,
            'status_reason': record.status_reason,
            'data': record.data,
            'tags': record.tags,
        }
        return cls(record.name, record.profile_id, record.size, **kwargs)

    def _load_runtime_data(self, context):
        self.rt = {
            'profile': profiles.Profile.load(context, self.profile_id),
            'nodes': nodes.Node.load_all(context, cluster_id=self.id),
            'policies': [],
        }

    @classmethod
    def load(cls, context, cluster_id, show_deleted=False):
        '''
        Retrieve a cluster from database.
        '''
        record = db_api.cluster_get(context, cluster_id,
                                    show_deleted=show_deleted)
        cluster = cls._from_db_record(record)
        cluster._load_runtime_data(context)
        return cluster

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, tenant_safe=True,
                 show_deleted=False, show_nested=False):
        '''
        Retrieve all clusters from database.
        '''
        records = db_api.cluster_get_all(context, limit, marker, sort_keys,
                                         sort_dir, filters, tenant_safe,
                                         show_deleted, show_nested)

        for record in records:
            cluster = cls._from_db_record(record)
            cluster.load_runtime_data(context)
            yield cluster

    def store(self, context):
        '''
        Store the cluster in database and return its ID.
        If the ID already exists, we do an update.
        '''
        values = {
            'name': self.name,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'parent': self.parent,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
            'size': self.size,
            'next_index': self.next_index,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'tags': self.tags,
            'data': self.data,
        }

        if self.id:
            db_api.cluster_update(context, self.id, values)
            # TODO(Qiming): create event/log
        else:
            cluster = db_api.cluster_create(context, values)
            # TODO(Qiming): create event/log
            self.id = cluster.id

        return self.id

    def to_dict(self):
        info = {
            'id': self.id,
            'name': self.name,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'parent': self.parent,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
            'size': self.size,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'tags': self.tags,
            'data': self.data,
            'nodes': [node.id for node in self.rt['nodes']],
            'profile_name': self.rt['profile'].name,
        }
        return info

    def set_status(self, context, status, reason=None):
        '''
        Set status of the cluster.
        '''
        values = {}
        now = datetime.datetime.utcnow()
        if status == self.ACTIVE:
            if self.status == self.INIT:
                values['created_time'] = now
            else:
                values['updated_time'] = now
        elif status == self.DELETED:
            values['deleted_time'] = now

        values['status'] = status
        if reason:
            values['status_reason'] = reason
        db_api.cluster_update(context, self.id, values)
        # log status to log file
        # generate event record

    def do_create(self, context, **kwargs):
        '''
        Invoked at the beginning of cluster creating
        progress to set cluster status to CREATING.
        '''
        self.set_status(context, self.CREATING)
        return True

    def do_delete(self, context, **kwargs):
        '''
        Invoked at the end of entire cluster deleting
        progress to set cluster status to DELETED.
        '''
        self.set_status(self.DELETED)

    def do_update(self, context, new_profile_id, **kwargs):
        '''
        Invoked at the beginning of cluster updating progress
        to check profile and set cluster status to UPDATING.
        '''
        self.set_status(self.UPDATING)
        # Profile type checking is done here because the do_update logic can
        # be triggered from API or Webhook
        if self.profile_id == new_profile_id:
            events.warning(_LW('Cluster refuses to update to the same profile'
                               '(%s)' % (new_profile_id)))
            return False

        # Check if profile types match
        old_profile = db_api.get_profile(context, self.profile_id)
        new_profile = db_api.get_profile(context, new_profile_id)
        if old_profile.type != new_profile.type:
            events.warning(_LW('Cluster cannot be updated to a different '
                               'profile type (%(oldt)s->%(newt)s)'),
                           {'oldt': old_profile.type,
                            'newt': new_profile.type})
            return False
        return True

    def get_next_index(self):
        # TODO(Qiming): Get next_index from db and increment it in db
        curr = self._next_index
        self._next_index = self._next_index + 1
        return curr

    def get_nodes(self):
        # This method will return each node with their associated profiles.
        # Members may have different versions of the same profile type.
        return self.rt.nodes

    def get_policies(self):
        # policies are stored in database when policy association is created
        # this method retrieves the attached policies from database
        return self.rt.policies

    def add_nodes(self, node_ids):
        pass

    def del_nodes(self, node_ids):
        '''
        Remove nodes from current cluster.
        '''
        deleted = []
        for node_id in node_ids:
            node = db_api.node_get(node_id)
            if node.leave(self):
                deleted.append(node_id)
        return deleted

    def attach_policy(self, policy_id):
        '''
        Attach specified policy instance to this cluster.
        '''
        # TODO(Qiming): check conflicts with existing policies
        self.policies.append(policy_id)

    def detach_policy(self, policy_id):
        # TODO(Qiming): check if actions of specified policies are ongoing
        self.policies.remove(policy_id)

    @classmethod
    def create(cls, name, size=0, profile=None, **kwargs):
        cluster = cls(name, size, profile, kwargs)
        cluster.do_create()
        # TODO(Qiming): store this to database
        # log events?
        return cluster.id

    @classmethod
    def delete(cls, cluster_id):
        cluster = db_api.get_cluster(cluster_id)
        # TODO(Qiming): check if actions are working on and can be canceled
        # destroy nodes

        db_api.delete_cluster(cluster.id)
        return True

    @classmethod
    def update(cls, cluster_id, profile):
        # cluster = db_api.get_cluster(cluster_id)
        # TODO(Qiming): Implement this
        return True

    @periodic_task.periodic_task
    def heathy_check(self):
        # TODO(Anyone):
        # 1. check if a HA policy is attached, return if not
        # 2. iterate the nodes in the cluster, invoke their
        #    profile do_check() to check their heathy
        # 3. if failure nodes found, enforce the HA policy
        pass

    def periodic_tasks(self, context, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)
