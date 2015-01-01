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

import copy
import datetime

from oslo.config import cfg

from senlin.common import exception
from senlin.db import api as db_api
from senlin.engine import environment
from senlin.engine import node as nodes
from senlin.engine import scheduler


class Action(object):
    '''
    An action can be performed on a cluster or a node of a cluster.
    '''
    RETURNS = (
        RES_OK, RES_ERROR, RES_RETRY,
    ) = (
        'OK', 'ERROR', 'RETRY',
    )

    # Action status definitions:
    #  INIT:      Not ready to be executed because fields are being modified,
    #             or dependency with other actions are being analyzed.
    #  READY:     Initialized and ready to be executed by a worker.
    #  RUNNING:   Being executed by a worker thread.
    #  SUCCEEDED: Completed with success.
    #  FAILED:    Completed with failure.
    #  CANCELLED: Action cancelled because worker thread was cancelled.
    STATUSES = (
        INIT, WAITING, READY, RUNNING,
        SUCCEEDED, FAILED, CANCELED
    ) = (
        'INIT', 'WAITING', 'READY', 'RUNNING',
        'SUCCEEDED', 'FAILED', 'CANCELLED',
    )

    def __new__(cls, context, action, **kwargs):
        if (cls != Action):
            return super(Action, cls).__new__(cls)

        target_type = action.split('_')[0]
        if target_type == 'CLUSTER':
            ActionClass = ClusterAction
        elif target_type == 'NODE':
            ActionClass = NodeAction
        elif target_type == 'POLICY':
            ActionClass = PolicyAction
        else:
            ActionClass = CustomAction

        return super(Action, cls).__new__(ActionClass)

    def __init__(self, context, action, **kwargs):
        # context will be persisted into database so that any worker thread
        # can pick the action up and execute it on behalf of the initiator
        if action not in self.ACTIONS:
            raise exception.ActionNotSupported(
                action=action, object=_('target %s') % self.target)

        self.context = copy.deepcopy(context)

        self.description = kwargs.get('description', '')

        # Target is the ID of a cluster, a node, a profile
        self.target = kwargs.get('target', None)
        if self.target is None:
            raise exception.ActionMissingTarget(action=action)

        self.action = action

        # Why this action is fired, it can be a UUID of another action
        self.cause = kwargs.get('cause', '')

        # Owner can be an UUID format ID for the worker that is currently
        # working on the action.  It also serves as a lock.
        self.owner = kwargs.get('owner', None)

        # An action may need to be executed repeatitively, interval is the
        # time in seconds between two consequtive execution.
        # A value of -1 indicates that this action is only to be executed once
        self.interval = kwargs.get('interval', -1)

        # Start time can be an absolute time or a time relative to another
        # action. E.g.
        #   - '2014-12-18 08:41:39.908569'
        #   - 'AFTER: 57292917-af90-4c45-9457-34777d939d4d'
        #   - 'WHEN: 0265f93b-b1d7-421f-b5ad-cb83de2f559d'
        self.start_time = kwargs.get('start_time', None)
        self.end_time = kwargs.get('end_time', None)

        # Timeout is a placeholder in case some actions may linger too long
        self.timeout = kwargs.get('timeout', cfg.CONF.default_action_timeout)

        # Return code, useful when action is not automatically deleted
        # after execution
        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', '')

        # All parameters are passed in using keyword arguments which is
        # a dictionary stored as JSON in DB
        self.inputs = kwargs.get('inputs', {})
        self.outputs = kwargs.get('outputs', {})

        # Dependency with other actions
        self.depends_on = kwargs.get('depends_on', [])
        self.depended_by = kwargs.get('depended_by', [])

    def store(self):
        '''
        Store the action record into database table.
        '''
        values = {
            'name': self.name,
            'context': self.context,
            'target': self.target,
            'action': self.action,
            'cause': self.cause,
            'owner': self.owner,
            'interval': self.interval,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'depends_on': self.depends_on,
            'depended_by': self.depended_by,
            'deleted_time': self.deleted_time,
        }

        action = db_api.action_create(self.context, self.id, values)
        self.id = action.id
        return self.id

    @classmethod
    def from_db_record(cls, context, record):
        '''
        Construct a action object from database record.
        :param context: the context used for DB operations;
        :param record: a DB action object that contains all fields.
        '''
        kwargs = {
            'id': record.id,
            'name': record.name,
            'context': record.context,
            'target': record.target,
            'cause': record.cause,
            'owner': record.owner,
            'interval': record.interval,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'timeout': record.timeout,
            'status': record.status,
            'status_reason': record.status_reason,
            'inputs': record.inputs,
            'outputs': record.outputs,
            'depends_on': record.depends_on,
            'depended_by': record.depended_by,
            'deleted_time': record.deleted_time,
        }

        return cls(context, record.action, **kwargs)

    @classmethod
    def load(cls, context, action_id):
        '''
        Retrieve an action from database.
        '''
        action = db_api.action_get(context, action_id)
        if action is None:
            msg = _('No action with id "%s" exists') % action_id
            raise exception.NotFound(msg)

        return cls.from_db_record(context, action)

    def execute(self, **kwargs):
        '''
        Execute the action.
        In theory, the action encapsulates all information needed for
        execution.  'kwargs' may specify additional parameters.
        :param kwargs: additional parameters that may override the default
                       properties stored in the action record.
        '''
        return NotImplemented

    def cancel(self):
        return NotImplemented

    def set_status(self, status):
        '''
        Set action status.
        This is not merely about a db record update.
        '''
        if status == self.SUCCEEDED:
            db_api.action_mark_succeeded(self.context, self.id)
        elif status == self.FAILED:
            db_api.action_mark_failed(self.context, self.id)
        elif status == self.CANCELLED:
            db_api.action_mark_cancelled(self.context, self.id)

        self.status = status

    def get_status(self):
        action = db_api.action_get(self.context, self.id)
        self.status = action.status
        return action.status


class ClusterAction(Action):
    '''
    An action performed on a cluster.
    '''
    ACTIONS = (
        CLUSTER_CREATE, CLUSTER_DELETE, CLUSTER_UPDATE,
        CLUSTER_ADD_NODES, CLUSTER_DEL_NODES, CLUSTER_RESIZE,
        CLUSTER_ATTACH_POLICY, CLUSTER_DETACH_POLICY,
    ) = (
        'CLUSTER_CREATE', 'CLUSTER_DELETE', 'CLUSTER_UPDATE',
        'CLUSTER_ADD_NODES', 'CLUSTER_DEL_NODES', 'CLUSTER_RESIZE',
        'CLUSTER_ATTACH_POLICY', 'CLUSTER_DETACH_POLICY',
    )

    def __init__(self, context, action, **kwargs):
        super(ClusterAction, self).__init__(context, action, **kwargs)

    def do_cluster_create(self, cluster):
        # TODO(Yanyan): Check if cluster lock is needed
        res = cluster.do_create()
        if res is False:
            return self.RES_ERROR

        for m in range(cluster.size):
            name = 'node-%003d' % m
            node = nodes.Node(name, cluster.profile_id, cluster.id)
            node.store()
            kwargs = {
                'name': 'node-create-%003d' % m,
                'context': self.context,
                'target': node.id,
                'cause': 'Cluster creation',
            }

            action = Action(self.context, 'NODE_CREATE', **kwargs)
            action.set_status(self.READY)

        scheduler.notify()

    def do_update(self, cluster):
        # TODO(Yanyan): Check if cluster lock is needed
        cluster.set_status(self.UPDATING)
        node_list = cluster.get_nodes()
        for node_id in node_list:
            kwargs = {
                'name': 'node-update-%s' % node_id,
                'context': self.context,
                'target': node_id,
                'cause': 'Cluster update',
            }
            action = Action(self.context, 'NODE_UPDATE', **kwargs)
            action.set_status(self.READY)

        scheduler.notify()
        # TODO(Yanyan): release lock
        cluster.set_status(self.ACTIVE)

        return self.RES_OK

    def do_delete(self, cluster):
        # TODO(Yanyan): Check if cluster lock is needed
        node_list = cluster.get_nodes()
        for node_id in node_list:
            kwargs = {
                'name': 'node-delete-%s' % node_id,
                'context': self.context,
                'target': node_id,
                'cause': 'Cluster update',
            }
            action = Action(self.context, 'NODE_UPDATE', **kwargs)
            action.set_status(self.READY)

        scheduler.notify()

        return self.RES_OK

    def do_add_nodes(self, cluster):
        return self.RES_OK

    def do_del_nodes(self, cluster):
        return self.RES_OK

    def do_resize(self, cluster):
        return self.RES_OK

    def do_attach_policy(self, cluster):
        return self.RES_OK

    def do_detach_policy(self, cluster):
        return self.RES_OK

    def execute(self, **kwargs):
        cluster = db_api.cluster_get(self.context, self.target)
        if not cluster:
            return self.RES_ERROR

        if self.action == self.CLUSTER_CREATE:
            return self.do_create(cluster)
        elif self.action == self.CLUSTER_UPDATE:
            return self.do_update(cluster)
        elif self.action == self.CLUSTER_DELETE:
            return self.do_delete(cluster)
        elif self.action == self.CLUSTER_ADD_NODES:
            return self.do_add_nodes(cluster)
        elif self.action == self.CLUSTER_DEL_NODES:
            return self.do_del_nodes(cluster)
        elif self.action == self.CLUSTER_RESIZE:
            return self.do_resize(cluster)
        elif self.action == self.CLUSTER_ATTACH_POLICY:
            return self.do_attach_policy(cluster)
        elif self.action == self.CLUSTER_DETACH_POLICY:
            return self.do_detach_policy(cluster)

        return self.RES_OK

    def cancel(self):
        return self.RES_OK


class NodeAction(Action):
    '''
    An action performed on a cluster member.
    '''
    ACTIONS = (
        NODE_CREATE, NODE_DELETE, NODE_UPDATE,
        NODE_JOIN_CLUSTER, NODE_LEAVE_CLUSTER,
    ) = (
        'NODE_CREATE', 'NODE_DELETE', 'NODE_UPDATE',
        'NODE_JOIN_CLUSTER', 'NODE_LEAVE_CLUSTER',
    )

    def __init__(self, context, action, **kwargs):
        super(NodeAction, self).__init__(context, action, **kwargs)

        # get cluster of this node
        # get policies associated with the cluster

    def _get_profile_cls(self, context, profile_id):
        profile = db_api.profile_get(context, profile_id)
        cls = environment.global_env().get_profile(profile.type)
        if not cls:
            raise exception.ProfileNotFound(profile=profile.name)
        return cls

    def do_create(self, node):
        cls = self._get_profile_cls(self.context, node.profile_id)
        node = cls.create_object(node.name, node.profile_id)
        if not node:
            return self.RES_ERROR

        return self.RES_OK

    def do_update(self, node):
        new_profile_id = self.inputs.get('new_profile', None)
        if not new_profile_id:
            raise exception.ProfileNotSpecified()

        if new_profile_id == node.profile_id:
            return self.RES_OK

        if not node.physical_id:
            return self.RES_ERROR

        cls = self._get_profile_cls(self.context, node.profile_id)
        node = cls.update_object(node.physical_id, new_profile_id)
        if not node:
            return self.RES_ERROR

        return self.RES_OK

    def do_delete(self, node):
        if not node.physical_id:
            return self.RES_OK

        cls = self._get_profile_cls(self.context, node.profile_id)
        node = cls.delete_object(node.physical_id)
        if not node:
            return self.RES_ERROR

        return self.RES_OK

    def do_join(self, node):
        new_cluster_id = self.inputs.get('cluster_id', None)
        if not new_cluster_id:
            raise exception.ClusterNotSpecified()

        # TODO(Qiming): complete this
        return self.RES_OK

    def do_leave(self, node):
        # cluster_id = node.cluster_id
        # TODO(Qiming): complete this

        return self.RES_OK

    def execute(self, **kwargs):
        node = db_api.node_get(self.context, self.target)
        if not node:
            msg = _('Node with id (%s) is not found') % self.target
            raise exception.NotFound(msg)

        if self.action == self.NODE_CREATE:
            return self.do_create(node)
        elif self.action == self.NODE_DELETE:
            return self.do_delete(node)
        elif self.action == self.NODE_UPDATE:
            return self.do_update(node)
        elif self.action == self.NODE_JOIN_CLUSTER:
            return self.do_join(node)
        elif self.action == self.NODE_LEAVE_CLUSTER:
            return self.do_leave(node)
        else:
            return self.RES_ERROR

        return self.RES_OK

    def cancel(self):
        return self.RES_OK


class PolicyAction(Action):
    '''
    An action performed on a cluster policy.

    Note that these can be treated as cluster operations instead of operations
    on a policy itself.
    '''

    ACTIONS = (
        POLICY_ENABLE, POLICY_DISABLE, POLICY_UPDATE,
    ) = (
        'POLICY_ENABLE', 'POLICY_DISABLE', 'POLICY_UPDATE',
    )

    def __init__(self, context, action, **kwargs):
        super(PolicyAction, self).__init__(context, action, **kwargs)
        self.cluster_id = kwargs.get('cluster_id', None)
        if self.cluster_id is None:
            raise exception.ActionMissingTarget(action)

        self.policy_id = kwargs.get('policy_id', None)
        if self.policy_id is None:
            raise exception.ActionMissingPolicy(action)

        # get policy associaton using the cluster id and policy id

    def execute(self, **kwargs):
        if self.action not in self.ACTIONS:
            return self.RES_ERROR

        self.store(start_time=datetime.datetime.utcnow(),
                   status=self.RUNNING)

        cluster_id = kwargs.get('cluster_id')
        policy_id = kwargs.get('policy_id')

        # an ENABLE/DISABLE action only changes the database table
        if self.action == self.POLICY_ENABLE:
            db_api.cluster_enable_policy(cluster_id, policy_id)
        elif self.action == self.POLICY_DISABLE:
            db_api.cluster_disable_policy(cluster_id, policy_id)
        else:  # self.action == self.UPDATE:
            # There is not direct way to update a policy because the policy
            # might be shared with another cluster, instead, we clone a new
            # policy and replace the cluster-policy entry.
            pass

            # TODO(Qiming): Add DB API complete this.

        self.store(end_time=datetime.datetime.utcnow(),
                   status=self.SUCCEEDED)

        return self.RES_OK

    def cancel(self):
        self.store(end_time=datetime.datetime.utcnow(),
                   status=self.CANCELLED)
        return self.RES_OK


class CustomAction(Action):
    ACTIONS = (
        ACTION_EXECUTE,
    ) = (
        'ACTION_EXECUTE',
    )

    def __init__(self, context, action, **kwargs):
        super(CustomAction, self).__init__(context, action, **kwargs)

    def execute(self, **kwargs):
        return self.RES_OK

    def cancel(self):
        return self.RES_OK
