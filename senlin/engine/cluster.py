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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import exception
from senlin.common.i18n import _LE
from senlin.db import api as db_api
from senlin.engine import event as event_mod
from senlin.engine import node as node_mod
from senlin.policies import base as policy_base
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Cluster(object):
    '''A cluster is a set of homogeneous objects of the same profile.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    STATUSES = (
        INIT, ACTIVE, DELETED, CREATING, UPDATING, DELETING,
        CRITICAL, ERROR, WARNING,
    ) = (
        'INIT', 'ACTIVE', 'DELETED', 'CREATING', 'UPDATING', 'DELETING',
        'CRITICAL', 'ERROR', 'WARNING',
    )

    def __init__(self, name, desired_capacity, profile_id,
                 context=None, **kwargs):
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

        self.min_size = kwargs.get('min_size', 0)
        self.max_size = kwargs.get('max_size', -1)
        self.desired_capacity = desired_capacity
        self.next_index = kwargs.get('next_index', 1)
        self.timeout = kwargs.get('timeout', cfg.CONF.default_action_timeout)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.metadata = kwargs.get('metadata', {})

        # rt is a dict for runtime data
        # TODO(Qiming): nodes have to be reloaded when membership changes
        self.rt = {
            'profile': None,
            'nodes': [],
            'policies': []
        }

        if context is not None:
            self._load_runtime_data(context)

    def _load_runtime_data(self, context):
        if self.id is None or self.deleted_time is not None:
            return

        policies = []
        bindings = db_api.cluster_policy_get_all(context, self.id)
        for b in bindings:
            # Detect policy type conflicts
            policy = policy_base.Policy.load(context, b.policy_id)
            policies.append(policy)

        self.rt = {
            # TODO(Yanyan Hu): Use permission to control access privilege
            # of profile.
            'profile': profile_base.Profile.load(context, self.profile_id,
                                                 project_safe=False),
            'nodes': node_mod.Node.load_all(context, cluster_id=self.id),
            'policies': policies
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
            'min_size': self.min_size,
            'max_size': self.max_size,
            'desired_capacity': self.desired_capacity,
            'next_index': self.next_index,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'meta_data': self.metadata,
            'data': self.data,
        }

        timestamp = timeutils.utcnow()
        if self.id:
            values['updated_time'] = timestamp
            db_api.cluster_update(context, self.id, values)
            event_mod.info(context, self, 'update')
        else:
            self.init_time = timestamp
            values['init_time'] = timestamp
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
            'min_size': record.min_size,
            'max_size': record.max_size,
            'next_index': record.next_index,
            'timeout': record.timeout,
            'status': record.status,
            'status_reason': record.status_reason,
            'data': record.data,
            'metadata': record.meta_data,
        }

        return cls(record.name, record.desired_capacity, record.profile_id,
                   context=context, **kwargs)

    @classmethod
    def load(cls, context, cluster_id=None, cluster=None, show_deleted=False,
             project_safe=True):
        '''Retrieve a cluster from database.'''
        if cluster is None:
            cluster = db_api.cluster_get(context, cluster_id,
                                         show_deleted=show_deleted,
                                         project_safe=project_safe)
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
        def _fmt_time(value):
            return value and value.isoformat()

        info = {
            'id': self.id,
            'name': self.name,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'parent': self.parent,
            'init_time': _fmt_time(self.init_time),
            'created_time': _fmt_time(self.created_time),
            'updated_time': _fmt_time(self.updated_time),
            'deleted_time': _fmt_time(self.deleted_time),
            'min_size': self.min_size,
            'max_size': self.max_size,
            'desired_capacity': self.desired_capacity,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'metadata': self.metadata,
            'data': self.data,
            'nodes': [node.id for node in self.rt['nodes']],
            'policies': [policy.id for policy in self.rt['policies']],
        }
        if self.rt['profile']:
            info['profile_name'] = self.rt['profile'].name
        else:
            info['profile_name'] = None

        return info

    def set_status(self, context, status, reason=None, **kwargs):
        """Set status of the cluster.

        :param context: A DB session for accessing the backend database.
        :param status: A string providing the new status of the cluster.
        :param reason: A string containing the reason for the status change.
                       It can be omitted when invoking this method.
        :param dict kwargs: Other optional attributes to be updated.
        :returns: Nothing.
        """

        values = {}
        now = timeutils.utcnow()
        if status == self.ACTIVE and self.status == self.CREATING:
            self.created_time = now
            values['created_time'] = now
        elif status == self.DELETED:
            self.deleted_time = now
            values['deleted_time'] = now
        elif status == self.ACTIVE and self.status == self.UPDATING:
            self.updated_time = now
            values['updated_time'] = now

        self.status = status
        values['status'] = status
        if reason:
            self.status_reason = reason
            values['status_reason'] = reason

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
                values[k] = v

        # There is a possibility that the profile id is changed
        if 'profile_id' in values:
            self.rt['profile'] = profile_base.Profile.load(context,
                                                           self.profile_id)
        db_api.cluster_update(context, self.id, values)
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
        self.set_status(context, self.DELETED, reason='Deletion succeeded')
        return True

    def do_update(self, context, **kwargs):
        '''Additional logic at the beginning of cluster updating progress.

        This method is intended to be called only from an action.
        '''
        self.set_status(context, self.UPDATING, reason='Update in progress')
        return True

    @property
    def nodes(self):
        return self.rt['nodes']

    def add_node(self, node):
        """Append specified node to the cluster cache.

        :param node: The node to become a new member of the cluster.
        """
        self.rt['nodes'].append(node)

    def remove_node(self, node_id):
        """Remove node with specified ID from cache.

        :param node_id: ID of the node to be removed from cache.
        """
        for node in self.rt['nodes']:
            if node.id == node_id:
                self.rt['nodes'].remove(node)

    @property
    def policies(self):
        return self.rt['policies']

    def add_policy(self, policy):
        '''Attach specified policy instance to this cluster.'''
        self.rt['policies'].append(policy)

    def remove_policy(self, policy):
        for p in self.rt['policies']:
            if (p.id == policy.id):
                self.rt['policies'].remove(p)
