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

import six

from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common import utils
from senlin.db import api as db_api
from senlin.engine import event as event_mod
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)


class Node(object):
    '''A node is an object that can belong to at most one single cluster.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    statuses = (
        INIT, ACTIVE, ERROR, DELETED, WARNING,
        CREATING, UPDATING, DELETING,
    ) = (
        'INIT', 'ACTIVE', 'ERROR', 'DELETED', 'WARNING',
        'CREATING', 'UPDATING', 'DELETING',
    )

    def __init__(self, name, profile_id, cluster_id, context=None, **kwargs):
        self.id = kwargs.get('id', None)
        if name:
            self.name = name
        else:
            self.name = 'node-' + utils.random_name(8)

        self.physical_id = kwargs.get('physical_id', '')
        self.profile_id = profile_id
        self.user = kwargs.get('user', '')
        self.project = kwargs.get('project', '')
        self.domain = kwargs.get('domain', '')
        self.cluster_id = cluster_id
        self.index = kwargs.get('index', -1)
        self.role = kwargs.get('role', '')

        self.init_time = kwargs.get('init_time', None)
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.metadata = kwargs.get('metadata', {})
        self.rt = {}

        if context is not None:
            if self.user == '':
                self.user = context.user
            if self.project == '':
                self.project = context.project
            if self.domain == '':
                self.domain = context.domain
            self._load_runtime_data(context)

    def _load_runtime_data(self, context):
        self.rt = {
            # TODO(Yanyan Hu): Use permission to control access privilege
            # of profile.
            'profile': profile_base.Profile.load(context, self.profile_id,
                                                 project_safe=False),
        }

    def store(self, context):
        '''Store the node record into database table.

        The invocation of DB API could be a node_create or a node_update,
        depending on whether node has an ID assigned.
        '''

        values = {
            'name': self.name,
            'physical_id': self.physical_id,
            'cluster_id': self.cluster_id,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'index': self.index,
            'role': self.role,
            'init_time': self.init_time,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
            'status': self.status,
            'status_reason': self.status_reason,
            'meta_data': self.metadata,
            'data': self.data,
        }

        if self.id:
            db_api.node_update(context, self.id, values)
            event_mod.info(context, self, 'update')
        else:
            init_time = timeutils.utcnow()
            self.init_time = init_time
            values['init_time'] = init_time
            node = db_api.node_create(context, values)
            event_mod.info(context, self, 'create')
            self.id = node.id

        self._load_runtime_data(context)
        return self.id

    @classmethod
    def _from_db_record(cls, context, record):
        '''Construct a node object from database record.

        :param context: the context used for DB operations;
        :param record: a DB node object that contains all fields;
        '''
        kwargs = {
            'id': record.id,
            'physical_id': record.physical_id,
            'user': record.user,
            'project': record.project,
            'domain': record.domain,
            'index': record.index,
            'role': record.role,
            'init_time': record.init_time,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
            'status': record.status,
            'status_reason': record.status_reason,
            'data': record.data,
            'metadata': record.meta_data,
        }

        return cls(record.name, record.profile_id, record.cluster_id,
                   context=context, **kwargs)

    @classmethod
    def load(cls, context, node_id=None, node=None, show_deleted=False,
             project_safe=True):
        '''Retrieve a node from database.'''
        if node is None:
            node = db_api.node_get(context, node_id,
                                   show_deleted=show_deleted,
                                   project_safe=project_safe)
            if node is None:
                raise exception.NodeNotFound(node=node_id)

        return cls._from_db_record(context, node)

    @classmethod
    def load_all(cls, context, cluster_id=None, show_deleted=False,
                 limit=None, marker=None, sort_keys=None, sort_dir=None,
                 filters=None, project_safe=True):
        '''Retrieve all nodes of from database.'''

        records = db_api.node_get_all(context, cluster_id=cluster_id,
                                      show_deleted=show_deleted,
                                      limit=limit, marker=marker,
                                      sort_keys=sort_keys, sort_dir=sort_dir,
                                      filters=filters,
                                      project_safe=project_safe)

        return [cls._from_db_record(context, record) for record in records]

    def to_dict(self):
        def _fmt_time(value):
            return value and value.isoformat()

        node_dict = {
            'id': self.id,
            'name': self.name,
            'cluster_id': self.cluster_id,
            'physical_id': self.physical_id,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'index': self.index,
            'role': self.role,
            'init_time': _fmt_time(self.init_time),
            'created_time': _fmt_time(self.created_time),
            'updated_time': _fmt_time(self.updated_time),
            'deleted_time': _fmt_time(self.deleted_time),
            'status': self.status,
            'status_reason': self.status_reason,
            'data': self.data,
            'metadata': self.metadata,
            'profile_name': self.rt['profile'].name,
        }
        return node_dict

    def set_status(self, context, status, reason=None):
        '''Set status of the node.'''

        values = {}
        now = timeutils.utcnow()
        if status == self.ACTIVE and self.status == self.CREATING:
            self.created_time = values['created_time'] = now
        elif status == self.ACTIVE and self.status == self.UPDATING:
            self.updated_time = values['updated_time'] = now
        elif status == self.DELETED:
            self.deleted_time = values['deleted_time'] = now

        self.status = status
        values['status'] = status
        if reason:
            self.status_reason = reason
            values['status_reason'] = reason
        db_api.node_update(context, self.id, values)

    def get_details(self, context):
        if self.physical_id is None or self.physical_id == '':
            return {}
        return profile_base.Profile.get_details(context, self)

    def _handle_exception(self, context, action, status, exception):
        msg = six.text_type(exception)
        event_mod.warning(context, self, action, status, msg)
        self.physical_id = exception.kwargs.get('resource_id', None)
        if self.physical_id:
            reason = _('Profile failed in %(action)s resource (%(id)s) due '
                       'to: %(msg)s') % {'action': action[:-1] + 'ing',
                                         'id': self.physical_id, 'msg': msg}
        else:
            # Exception happens before physical node creatin started.
            reason = _('Profile failed in creating node due to: %(msg)s') % {
                'msg': msg}
        self.set_status(context, self.ERROR, reason)
        self.store(context)

    def do_create(self, context):
        if self.status != self.INIT:
            LOG.error(_LE('Node is in status "%s"'), self.status)
            return False
        self.set_status(context, self.CREATING, reason='Creation in progress')
        event_mod.info(context, self, 'create')
        try:
            physical_id = profile_base.Profile.create_object(context, self)
        except exception.InternalError as ex:
            self._handle_exception(context, 'create', self.ERROR, ex)
            return False
        if not physical_id:
            return False

        status_reason = 'Creation succeeded'
        self.set_status(context, self.ACTIVE, status_reason)
        self.physical_id = physical_id
        self.store(context)
        return True

    def do_delete(self, context):
        if not self.physical_id:
            db_api.node_delete(context, self.id)
            return True

        # TODO(Qiming): check if actions are working on it and can be canceled
        self.set_status(context, self.DELETING, reason='Deletion in progress')
        event_mod.info(context, self, 'delete')
        try:
            res = profile_base.Profile.delete_object(context, self)
        except exception.ResourceStatusError as ex:
            self._handle_exception(context, 'delete', self.ERROR, ex)
            res = False

        if res:
            db_api.node_delete(context, self.id)
            return True
        else:
            self.set_status(context, self.ERROR, reason='Deletion failed')
            return False

    def do_update(self, context, params):
        """Update a node's property.

        This function is supposed to be invoked from a NODE_UPDATE action.
        :param dict params: parameters in a dictionary that may contain keys
                            like 'new_profile_id', 'name', 'role', 'metadata'.
        """
        if not self.physical_id:
            return False

        self.set_status(context, self.UPDATING,
                        reason='Update in progress')

        new_profile_id = params.pop('new_profile_id', None)
        try:
            res = profile_base.Profile.update_object(
                context, self, new_profile_id, **params)
        except exception.ResourceStatusError as ex:
            self._handle_exception(context, 'update', self.ERROR, ex)
            res = False

        if res:
            if 'name' in params:
                self.name = params['name']
            if 'role' in params:
                self.role = params['role']
            if 'metadata' in params:
                self.metadata = params['metadata']

            if new_profile_id:
                self.profile_id = new_profile_id
            self.store(context)

            self.set_status(context, self.ACTIVE, reason='Update succeeded')

        return res

    def do_join(self, context, cluster_id):
        if self.cluster_id == cluster_id:
            return True
        timestamp = timeutils.utcnow()
        db_node = db_api.node_migrate(context, self.id, cluster_id,
                                      timestamp)
        self.cluster_id = cluster_id
        self.updated_time = timestamp
        self.index = db_node.index

        profile_base.Profile.join_cluster(context, self, cluster_id)
        return True

    def do_leave(self, context):
        if self.cluster_id is None:
            return True

        timestamp = timeutils.utcnow()
        db_api.node_migrate(context, self.id, None, timestamp)
        self.cluster_id = None
        self.updated_time = timestamp
        self.index = -1

        profile_base.Profile.leave_cluster(context, self)
        return True
