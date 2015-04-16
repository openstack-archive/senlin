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

from oslo_config import cfg
from oslo_log import log as logging

from senlin.common import exception
from senlin.common.i18n import _LE
from senlin.common.i18n import _LW
from senlin.db import api as db_api
from senlin.engine import event as event_mod
from senlin.engine import node as node_mod
from senlin.openstack.common import periodic_task
from senlin.profiles import base as profiles_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Cluster(periodic_task.PeriodicTasks):
    '''A cluster is a set of homogeneous objects of the same profile.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    STATUSES = (
        INIT, CREATING, ACTIVE, ERROR, CRITICAL, DELETING, DELETED, WARNING,
        UPDATING, UPDATE_CANCELLED,
    ) = (
        'INIT', 'CREATING', 'ACTIVE', 'ERROR', 'CRITICAL', 'DELETING',
        'DELETED', 'WARNING', 'UPDATING', 'UPDATE_CANCELLED',
    )

    def __init__(self, name, profile_id, size=0, context=None, **kwargs):
        '''Intialize a cluster object.

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

        self.init_time = kwargs.get('init_time', None)
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        # size is only the 'desired capacity', which many not be the real
        # size of the cluster at a moment.
        self.size = size
        self.next_index = kwargs.get('next_index', 1)
        self.timeout = kwargs.get('timeout', cfg.CONF.default_action_timeout)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.tags = kwargs.get('tags', {})

        # heathy checking
        self.detect_enabled = False
        self.detect_interval = 1  # times of global periodic task interval.
        self.detect_counter = 0

        # rt is a dict for runtime data
        # TODO(Qiming): nodes have to be reloaded when membership changes
        self.rt = {}

        if context is not None:
            self._load_runtime_data(context)

    def _load_runtime_data(self, context):
        self.rt = {
            'profile': profiles_base.Profile.load(context, self.profile_id),
            'nodes': node_mod.Node.load_all(context, cluster_id=self.id),
            'policies': [],
        }

    def store(self, context):
        '''Store the cluster in database and return its ID.

        If the ID already exists, we do an update.
        '''

        values = {
            'name': self.name,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'parent': self.parent,
            'init_time': self.init_time,
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
            event_mod.info(context, self, 'update')
        else:
            values['init_time'] = datetime.datetime.utcnow()
            cluster = db_api.cluster_create(context, values)
            self.id = cluster.id
            event_mod.info(context, self, 'create')

        self._load_runtime_data(context)
        return self.id

    @classmethod
    def _from_db_record(cls, context, record):
        '''Construct a cluster object from database record.

        :param context: the context used for DB operations;
        :param record: a DB cluster object that will receive all fields;
        '''
        kwargs = {
            'id': record.id,
            'user': record.user,
            'project': record.project,
            'domain': record.domain,
            'parent': record.parent,
            'init_time': record.init_time,
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

        return cls(record.name, record.profile_id, record.size,
                   context=context, **kwargs)

    @classmethod
    def load(cls, context, cluster_id=None, cluster=None, show_deleted=False):
        '''Retrieve a cluster from database.'''
        if cluster is None:
            cluster = db_api.cluster_get(context, cluster_id,
                                         show_deleted=show_deleted)
            if cluster is None:
                raise exception.ClusterNotFound(cluster=cluster_id)

        return cls._from_db_record(context, cluster)

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, project_safe=True,
                 show_deleted=False, show_nested=False):
        '''Retrieve all clusters from database.'''

        records = db_api.cluster_get_all(context, limit=limit, marker=marker,
                                         sort_keys=sort_keys,
                                         sort_dir=sort_dir,
                                         filters=filters,
                                         project_safe=project_safe,
                                         show_deleted=show_deleted,
                                         show_nested=show_nested)

        for record in records:
            cluster = cls._from_db_record(context, record)
            yield cluster

    def to_dict(self):
        info = {
            'id': self.id,
            'name': self.name,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'parent': self.parent,
            'init_time': self.init_time,
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
            'policies': [policy.id for policy in self.rt['policies']],
            'profile_name': self.rt['profile'].name,
        }
        return info

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def set_status(self, context, status, reason=None):
        '''Set status of the cluster.'''

        values = {}
        now = datetime.datetime.utcnow()
        if status == self.ACTIVE and self.status == self.CREATING:
            values['created_time'] = now
        elif status == self.DELETED:
            values['deleted_time'] = now
        elif status == self.ACTIVE and self.status == self.UPDATING:
            values['updated_time'] = now

        self.status = status
        values['status'] = status
        if reason:
            values['status_reason'] = reason

        db_api.cluster_update(context, self.id, values)
        # TODO(anyone): generate event record
        return

    def do_create(self, context, **kwargs):
        '''Additional logic at the beginning of cluster creation process.

        Set cluster status to CREATING.
        '''
        if self.status != self.INIT:
            LOG.error(_LE('Cluster is in status "%s"'), self.status)
            return False

        self.set_status(context, self.CREATING, reason='Creation in progress')
        return True

    def do_delete(self, context, **kwargs):
        '''Additional logic at the end of cluster deletion process.

        Set cluster status to DELETED.
        '''
        # self.set_status(context, self.DELETED)
        db_api.cluster_delete(context, self.id)
        return True

    def do_update(self, context, new_profile_id, **kwargs):
        '''Additional logic at the beginning of cluster updating progress.

        Check profile and set cluster status to UPDATING.
        '''
        # Profile type checking is done here because the do_update logic can
        # be triggered from API or Webhook
        if not new_profile_id:
            raise exception.ProfileNotSpecified()

        if new_profile_id == self.profile_id:
            return True

        new_profile = db_api.get_profile(context, new_profile_id)
        if not new_profile:
            event_mod.warning(context, self, 'update',
                              _LW('Cluster cannot be updated to a profile '
                                  'that does not exists'))
            return False

        # Check if profile types match
        old_profile = db_api.get_profile(context, self.profile_id)
        if old_profile.type != new_profile.type:
            event_mod.warning(context, self, 'update',
                              _LW('Cluster cannot be updated to a different '
                                  'profile type (%(oldt)s->%(newt)s)') % {
                                      'oldt': old_profile.type,
                                      'newt': new_profile.type})
            return False

        self.set_status(self.UPDATING)
        return True

    def get_nodes(self):
        '''Get all nodes for this cluster.'''
        return self.rt.get('nodes', [])

    def get_policies(self):
        '''Get all policies associated with the cluster.'''
        return self.rt.get('policies', [])

    def add_nodes(self, node_ids):
        return

    def del_nodes(self, node_ids):
        '''Remove nodes from current cluster.'''

        deleted = []
        for node_id in node_ids:
            node = db_api.node_get(node_id)
            if node and node.leave(self):
                deleted.append(node_id)
        return deleted

    def add_policy(self, policy):
        '''Attach specified policy instance to this cluster.'''

        # TODO(Qiming): check conflicts with existing policies
        self.rt['policies'].append(policy)

    def remove_policy(self, policy):
        # TODO(Qiming): check if actions of specified policies are ongoing
        for p in self.rt['policies']:
            if(p.id == policy.id):
                self.rt['policies'].remove(policy)

    def heathy_check_enable(self):
        self.detect_enabled = True

    def heathy_check_disable(self):
        self.detect_enabled = False

    def heathy_check_set_interval(self, policy_interval):
        detection_interval = (policy_interval +
                              CONF.periodic_interval_max)

        self.detection_inteval = (detection_interval /
                                  CONF.periodic_interval_max)

    @periodic_task.periodic_task
    def heathy_check(self):
        if(not self.detect_enabled):
            return

        if(self.detect_counter < self.detect_interval):
            self.detect_counter += 1
            return
        self.detect_counter = 0

        fails = 0
        for nd in self.rt['nodes']:
            if(nd.rt.profile.do_check(nd)):
                continue

            fails += 1

        # TODO(Anyone):
        # How to enforce the HA policy?
        pass

    def periodic_tasks(self, context, raise_on_error=False):
        '''Tasks to be run at a periodic interval.'''

        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)
