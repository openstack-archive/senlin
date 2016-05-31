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
from senlin.objects import node as no
from senlin.profiles import base as profile_base

LOG = logging.getLogger(__name__)


class Node(object):
    """A node is an object that can belong to at most one single cluster.

    All operations are performed without further checking because the
    checkings are supposed to be done before/after/during an action is
    excuted.
    """

    statuses = (
        INIT, ACTIVE, ERROR, WARNING, CREATING, UPDATING, DELETING,
        RECOVERING
    ) = (
        'INIT', 'ACTIVE', 'ERROR', 'WARNING', 'CREATING', 'UPDATING',
        'DELETING', 'RECOVERING'
    )

    def __init__(self, name, profile_id, cluster_id=None, context=None,
                 **kwargs):
        self.id = kwargs.get('id', None)
        if name:
            self.name = name
        else:
            self.name = 'node-' + utils.random_name(8)

        # This is a safe guard to ensure that we have orphan node's cluster
        # correctly set to an empty string
        if cluster_id is None:
            cluster_id = ''

        self.physical_id = kwargs.get('physical_id', None)
        self.profile_id = profile_id
        self.user = kwargs.get('user', '')
        self.project = kwargs.get('project', '')
        self.domain = kwargs.get('domain', '')
        self.cluster_id = cluster_id
        self.index = kwargs.get('index', -1)
        self.role = kwargs.get('role', '')

        self.init_at = kwargs.get('init_at', None)
        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)

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
        profile = None
        try:
            profile = profile_base.Profile.load(context,
                                                profile_id=self.profile_id,
                                                project_safe=False)
        except exception.ProfileNotFound:
            LOG.debug(_('Profile not found: %s'), self.profile_id)

        self.rt = {'profile': profile}

    def store(self, context):
        """Store the node into database table.

        The invocation of object API could be a node_create or a node_update,
        depending on whether node has an ID assigned.

        @param context: Request context for node creation.
        @return: UUID of node created.
        """
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
            'init_at': self.init_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'status_reason': self.status_reason,
            'meta_data': self.metadata,
            'data': self.data,
        }

        if self.id:
            no.Node.update(context, self.id, values)
        else:
            init_at = timeutils.utcnow(True)
            self.init_at = init_at
            values['init_at'] = init_at
            node = no.Node.create(context, values)
            self.id = node.id

        self._load_runtime_data(context)
        return self.id

    @classmethod
    def _from_object(cls, context, obj):
        """Construct a node from node object.

        @param context: the context used for DB operations;
        @param node: a node object that contains all fields;
        """
        kwargs = {
            'id': obj.id,
            'physical_id': obj.physical_id,
            'user': obj.user,
            'project': obj.project,
            'domain': obj.domain,
            'index': obj.index,
            'role': obj.role,
            'init_at': obj.init_at,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'status': obj.status,
            'status_reason': obj.status_reason,
            'data': obj.data,
            'metadata': obj.metadata,
        }

        return cls(obj.name, obj.profile_id, obj.cluster_id,
                   context=context, **kwargs)

    @classmethod
    def load(cls, context, node_id=None, db_node=None, project_safe=True):
        '''Retrieve a node from database.'''
        if db_node is None:
            db_node = no.Node.get(context, node_id, project_safe=project_safe)
            if db_node is None:
                raise exception.NodeNotFound(node=node_id)

        return cls._from_object(context, db_node)

    @classmethod
    def load_all(cls, context, cluster_id=None, limit=None, marker=None,
                 sort=None, filters=None, project_safe=True):
        '''Retrieve all nodes of from database.'''
        objs = no.Node.get_all(context, cluster_id=cluster_id,
                               filters=filters, sort=sort,
                               limit=limit, marker=marker,
                               project_safe=project_safe)

        return [cls._from_object(context, obj) for obj in objs]

    def to_dict(self):
        if self.rt['profile']:
            profile_name = self.rt['profile'].name
        else:
            profile_name = 'Unknown'
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
            'init_at': utils.format_time(self.init_at),
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
            'status': self.status,
            'status_reason': self.status_reason,
            'data': self.data,
            'metadata': self.metadata,
            'profile_name': profile_name,
        }
        return node_dict

    def set_status(self, context, status, reason=None):
        '''Set status of the node.'''

        values = {}
        now = timeutils.utcnow(True)
        if status == self.ACTIVE and self.status == self.CREATING:
            self.created_at = values['created_at'] = now
        elif status == self.ACTIVE and self.status == self.UPDATING:
            self.updated_at = values['updated_at'] = now

        self.status = status
        values['status'] = status
        if reason:
            self.status_reason = reason
            values['status_reason'] = reason
        no.Node.update(context, self.id, values)

    def get_details(self, context):
        if not self.physical_id:
            return {}
        return profile_base.Profile.get_details(context, self)

    def _handle_exception(self, context, action, status, exception):
        msg = six.text_type(exception)
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
        try:
            physical_id = profile_base.Profile.create_object(context, self)
        except exception.InternalError as ex:
            LOG.exception(_('Failed in creating server: %s'),
                          six.text_type(ex))
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
            no.Node.delete(context, self.id)
            return True

        # TODO(Qiming): check if actions are working on it and can be canceled
        self.set_status(context, self.DELETING, reason='Deletion in progress')
        try:
            res = profile_base.Profile.delete_object(context, self)
        except exception.ResourceStatusError as ex:
            self._handle_exception(context, 'delete', self.ERROR, ex)
            res = False

        if res:
            no.Node.delete(context, self.id)
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
        res = True
        if new_profile_id:
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
        res = profile_base.Profile.join_cluster(context, self, cluster_id)
        if res:
            timestamp = timeutils.utcnow(True)
            db_node = no.Node.migrate(context, self.id, cluster_id, timestamp)
            self.cluster_id = cluster_id
            self.updated_at = timestamp
            self.index = db_node.index
            return True
        else:
            return False

    def do_leave(self, context):
        if self.cluster_id == '':
            return True

        res = profile_base.Profile.leave_cluster(context, self)
        if res:
            timestamp = timeutils.utcnow(True)
            no.Node.migrate(context, self.id, None, timestamp)
            self.cluster_id = ''
            self.updated_at = timestamp
            self.index = -1
            return True
        else:
            return False

    def do_check(self, context):
        if not self.physical_id:
            return False

        res = profile_base.Profile.check_object(context, self)

        if not res:
            self.status = 'ERROR'
            self.status_reason = _('Physical node is not ACTIVE!')
            self.store(context)

        return res

    def do_recover(self, context, **options):
        """recover a node.

        This function is supposed to be invoked from a NODE_RECOVER action.
        """
        if not self.physical_id:
            return False

        self.set_status(context, self.RECOVERING,
                        reason=_('Recover in progress'))

        try:
            physical_id = profile_base.Profile.recover_object(context, self,
                                                              **options)
        except exception.ResourceStatusError as ex:
            self._handle_exception(context, 'recover', self.ERROR, ex)
            return False

        if not physical_id:
            self.set_status(context, self.ERROR, reason=_('Recover failed'))
            return False

        self.set_status(context, self.ACTIVE, reason=_('Recover succeeded'))
        if self.physical_id != physical_id:
            self.physical_id = physical_id
            self.store(context)

        return True
