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
from oslo_serialization import jsonutils
from oslo_utils import timeutils
import six

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common import utils
from senlin.objects import node as no
from senlin.profiles import base as pb

LOG = logging.getLogger(__name__)


class Node(object):
    """A node is an object that can belong to at most one single cluster.

    All operations are performed without further checking because the
    checkings are supposed to be done before/after/during an action is
    executed.
    """

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

        self.status = kwargs.get('status', consts.NS_INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.metadata = kwargs.get('metadata', {})
        self.dependents = kwargs.get('dependents', {})
        self.rt = {}

        if context is not None:
            if self.user == '':
                self.user = context.user_id
            if self.project == '':
                self.project = context.project_id
            if self.domain == '':
                self.domain = context.domain_id
            self._load_runtime_data(context)

    def _load_runtime_data(self, context):
        profile = None
        try:
            profile = pb.Profile.load(context, profile_id=self.profile_id,
                                      project_safe=False)
        except exc.ResourceNotFound:
            LOG.debug('Profile not found: %s', self.profile_id)

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
            'dependents': self.dependents,
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
        @param obj: a node object that contains all fields;
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
            'dependents': obj.dependents,
        }

        return cls(obj.name, obj.profile_id, obj.cluster_id,
                   context=context, **kwargs)

    @classmethod
    def load(cls, context, node_id=None, db_node=None, project_safe=True):
        '''Retrieve a node from database.'''
        if db_node is None:
            db_node = no.Node.get(context, node_id, project_safe=project_safe)
            if db_node is None:
                raise exc.ResourceNotFound(type='node', id=node_id)

        return cls._from_object(context, db_node)

    @classmethod
    def load_all(cls, context, cluster_id=None, limit=None, marker=None,
                 sort=None, filters=None, project_safe=True):
        '''Retrieve all nodes of from database.'''
        objs = no.Node.get_all(context, cluster_id=cluster_id,
                               filters=filters, sort=sort,
                               limit=limit, marker=marker,
                               project_safe=project_safe)

        for obj in objs:
            node = cls._from_object(context, obj)
            yield node

    def set_status(self, context, status, reason=None, **params):
        """Set status of the node.

        :param context: The request context.
        :param status: New status for the node.
        :param reason: The reason that leads the node to its current status.
        :param kwargs params: Other properties that need an update.
        :returns: ``None``.
        """
        values = {}
        now = timeutils.utcnow(True)
        if status == consts.NS_ACTIVE and self.status == consts.NS_CREATING:
            self.created_at = values['created_at'] = now
        if status not in [consts.NS_CREATING, consts.NS_UPDATING,
                          consts.NS_RECOVERING, consts.NS_OPERATING]:
            self.updated_at = values['updated_at'] = now

        self.status = status
        values['status'] = status
        if reason:
            self.status_reason = reason
            values['status_reason'] = reason
        for p, v in params.items():
            setattr(self, p, v)
            values[p] = v
        no.Node.update(context, self.id, values)

    def get_details(self, context):
        if not self.physical_id:
            return {}
        return pb.Profile.get_details(context, self)

    def do_create(self, context):
        if self.status != consts.NS_INIT:
            LOG.error('Node is in status "%s"', self.status)
            return False

        self.set_status(context, consts.NS_CREATING, 'Creation in progress')
        try:
            physical_id = pb.Profile.create_object(context, self)
        except exc.EResourceCreation as ex:
            physical_id = ex.resource_id
            self.set_status(context, consts.NS_ERROR, six.text_type(ex),
                            physical_id=physical_id)
            return False

        self.set_status(context, consts.NS_ACTIVE, 'Creation succeeded',
                        physical_id=physical_id)
        return True

    def do_delete(self, context):
        self.set_status(context, consts.NS_DELETING, 'Deletion in progress')
        try:
            # The following operation always return True unless exception
            # is thrown
            pb.Profile.delete_object(context, self)
        except exc.EResourceDeletion as ex:
            self.set_status(context, consts.NS_ERROR, six.text_type(ex))
            return False

        no.Node.delete(context, self.id)
        return True

    def do_update(self, context, params):
        """Update a node's property.

        This function is supposed to be invoked from a NODE_UPDATE action.
        :param dict params: parameters in a dictionary that may contain keys
                            like 'new_profile_id', 'name', 'role', 'metadata'.
        """
        if not self.physical_id:
            return False

        self.set_status(context, consts.NS_UPDATING, 'Update in progress')

        new_profile_id = params.pop('new_profile_id', None)
        res = True
        if new_profile_id:
            try:
                res = pb.Profile.update_object(context, self, new_profile_id,
                                               **params)
            except exc.EResourceUpdate as ex:
                self.set_status(context, consts.NS_ERROR, six.text_type(ex))
                return False

        # update was not successful
        if not res:
            return False

        props = dict([(k, v) for k, v in params.items()
                      if k in ('name', 'role', 'metadata')])
        if new_profile_id:
            props['profile_id'] = new_profile_id
            self.rt['profile'] = pb.Profile.load(context,
                                                 profile_id=new_profile_id)

        self.set_status(context, consts.NS_ACTIVE, 'Update succeeded', **props)

        return True

    def do_join(self, context, cluster_id):
        if self.cluster_id == cluster_id:
            return True

        timestamp = timeutils.utcnow(True)
        db_node = no.Node.migrate(context, self.id, cluster_id, timestamp)
        self.cluster_id = cluster_id
        self.updated_at = timestamp
        self.index = db_node.index

        res = pb.Profile.join_cluster(context, self, cluster_id)
        if res:
            return True

        # rollback
        db_node = no.Node.migrate(context, self.id, None, timestamp)
        self.cluster_id = ''
        self.updated_at = timestamp
        self.index = -1

        return False

    def do_leave(self, context):
        if self.cluster_id == '':
            return True

        res = pb.Profile.leave_cluster(context, self)
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

        try:
            res = pb.Profile.check_object(context, self)
        except exc.EServerNotFound as ex:
            self.set_status(context, consts.NS_ERROR, six.text_type(ex),
                            physical_id=None)
            return True
        except exc.EResourceOperation as ex:
            self.set_status(context, consts.NS_ERROR, six.text_type(ex))
            return False

        # Physical object is ACTIVE but for some reason the node status in
        # senlin was WARNING. We only update the status_reason
        if res:
            if self.status == consts.NS_WARNING:
                msg = ("Check: Physical object is ACTIVE but the node status "
                       "was WARNING. %s") % self.status_reason
                self.set_status(context, consts.NS_WARNING, msg)
                return True

            self.set_status(context, consts.NS_ACTIVE,
                            "Check: Node is ACTIVE.")
        else:
            self.set_status(context, consts.NS_ERROR,
                            "Check: Node is not ACTIVE.")

        return True

    def do_recover(self, context, action):
        """recover a node.

        This function is supposed to be invoked from a NODE_RECOVER action.
        :param context: The request context of the action.
        :param dict options: A map containing the recovery actions (with
            parameters if any) and fencing settings.
        """
        if not self.physical_id:
            return False

        options = action.inputs
        if options.get('check', False):
            res = False
            try:
                res = pb.Profile.check_object(context, self)
            except exc.EResourceOperation:
                pass

            if res:
                self.set_status(context, consts.NS_ACTIVE,
                                reason="Recover: Node is ACTIVE.")
                return True

        self.set_status(context, consts.NS_RECOVERING,
                        reason='Recovery in progress')

        try:
            physical_id = pb.Profile.recover_object(context, self, **options)
        except exc.EResourceOperation as ex:
            self.set_status(context, consts.NS_ERROR, reason=six.text_type(ex))
            return False

        if not physical_id:
            self.set_status(context, consts.NS_ERROR, reason='Recovery failed')
            return False

        params = {}
        if self.physical_id != physical_id:
            self.data['recovery'] = consts.RECOVER_RECREATE
            params['data'] = self.data
            params['physical_id'] = physical_id
        self.set_status(context, consts.NS_ACTIVE,
                        reason='Recovery succeeded', **params)

        return True

    def do_operation(self, context, **inputs):
        """Perform an operation on a node.

        :param context: The request context.
        :param dict inputs: The operation and parameters if any.
        :returns: A boolean indicating whether the operation was a success.
        """
        if not self.physical_id:
            return False

        op = inputs['operation']
        params = inputs.get('params', {})
        self.set_status(context, consts.NS_OPERATING,
                        reason="Operation '%s' in progress" % op)

        try:
            profile = self.rt['profile']
            method = getattr(profile, 'handle_' + op)
            method(self, **params)
        except exc.EResourceOperation as ex:
            self.set_status(context, consts.NS_ERROR, reason=six.text_type(ex))
            return False

        self.set_status(context, consts.NS_ACTIVE,
                        reason="Operation '%s' succeeded" % op)
        return True

    def run_workflow(self, **options):
        if not self.physical_id:
            return False

        workflow_name = options.pop('workflow_name')
        inputs = options.pop('inputs')
        definition = inputs.pop('definition', None)
        params = {
            'cluster_id': self.cluster_id,
            'node_id': self.physical_id,
        }
        params.update(inputs)

        try:
            profile = self.rt['profile']
            wfc = profile.workflow(self)
            workflow = wfc.workflow_find(workflow_name)
            if workflow is None:
                wfc.workflow_create(definition, scope="private")
            else:
                definition = workflow.definition
            inputs_str = jsonutils.dumps(params)
            wfc.execution_create(workflow_name, str(inputs_str))
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='executing', type='workflow',
                                         id=workflow_name,
                                         message=six.text_type(ex))
        return True
