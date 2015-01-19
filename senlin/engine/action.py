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

from oslo_config import cfg

from senlin.common import exception
from senlin.common.i18n import _
from senlin.db import api as db_api
from senlin.engine import dispatcher
from senlin.engine import node as nodes
from senlin.engine import scheduler
from senlin.openstack.common import log as logging
from senlin.policies import base as policies

LOG = logging.getLogger(__name__)


class Action(object):
    '''
    An action can be performed on a cluster or a node of a cluster.
    '''
    RETURNS = (
        RES_OK, RES_ERROR, RES_RETRY, RES_CANCEL, RES_TIMEOUT,
    ) = (
        'OK', 'ERROR', 'RETRY', 'CANCEL', 'TIMEOUT',
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
        CLUSTER_ADD_NODES, CLUSTER_DEL_NODES,
        CLUSTER_SCALE_UP, CLUSTER_SCALE_DOWN,
        CLUSTER_ATTACH_POLICY, CLUSTER_DETACH_POLICY,
    ) = (
        'CLUSTER_CREATE', 'CLUSTER_DELETE', 'CLUSTER_UPDATE',
        'CLUSTER_ADD_NODES', 'CLUSTER_DEL_NODES',
        'CLUSTER_SCALE_UP', 'CLUSTER_SCALE_DOWN',
        'CLUSTER_ATTACH_POLICY', 'CLUSTER_DETACH_POLICY',
    )

    def __init__(self, context, action, **kwargs):
        super(ClusterAction, self).__init__(context, action, **kwargs)

    def do_create(self, cluster):
        # Try to lock cluster first
        worker_id = db_api.cluster_lock_create(cluster.id, self.id)
        if worker_id != self.id:
            # This cluster has been locked by other action?
            # This should never happen here, raise an execption.
            LOG.error(
                'Cluster has been locked by %s before creating.' % worker_id)
            raise exception.Error('Cluster is locked by action %s and action \
                %s at the same time during creation' % (self.id, worker_id))

        # Got the lock, start to work
        res = cluster.do_create()
        if res is False:
            cluster.set_status(cluster.ERROR, 'Cluster creating failed')
            db_api.cluster_lock_release(cluster.id, self.id)
            return self.RES_ERROR

        action_list = []
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
            action_list.append(action)
            action.set_status(self.READY)

            # add new action to waiting/dependency list
            db_api.action_add_dependency(action, self)

        # Notify dispatcher
        for action in action_list:
            dispatcher.notify(self.context,
                              dispatcher.Dispatcher.NEW_ACTION,
                              None,
                              action_id=action.id)

        # Wait for cluster creating complete
        # TODO: need db support
        while self.get_status() != self.READY:
            if scheduler.action_cancelled(self):
                # During this period, if cancel request come,
                # cancel this cluster creating immediately, then
                # release the cluster lock and return.
                LOG.debug('Cluster creating action %s cancelled' % self.id)
                cluster.set_status(cluster.ERROR, 'Cluster creating cancel')
                db_api.cluster_lock_release(cluster.id, self.id)
                return self.RES_CANCEL
            elif scheduler.action_timeout(self):
                # Action timeout, return
                LOG.debug('Cluster creating action %s timeout' % self.id)
                cluster.set_status(cluster.ERROR, 'Cluster creating timeout')
                db_api.cluster_lock_release(cluster.id, self.id)
                return self.RES_TIMEOUT

            # Continue waiting (with reschedule)
            scheduler.reschedule(self, sleep=0)

        # Cluster create finished, update its status
        # to active and release the lock.
        cluster.set_status(cluster.ACTIVE, 'Cluster creating completed')
        db_api.cluster_lock_release(cluster.id, self.id)

        return self.RES_OK

    def do_update(self, cluster, new_profile_id):
        # Try to lock cluster first
        worker_id = db_api.cluster_lock_create(cluster.id, self.id)
        if worker_id != self.id:
            # This cluster has been locked by other action.
            # We can't update this cluster, cancel this action.
            LOG.debug('Cluster has been locked by action %s' % worker_id)
            return self.RES_CANCEL

        old_profile_id = cluster.profile_id
        # Note: we need clean the node count of cluster each time
        # cluster.do_update is invoked; Then this count could be added
        # gradually each time a node update action finished. This helps
        # us to track the progress of cluster updating. 
        # (TODO) update this comment
        res = cluster.do_update(self.context, profile_id=new_profile_id)
        if not res:
            cluster.set_status(cluster.ACTIVE,
                               'Cluster updating was not executed')
            db_api.cluster_lock_release(cluster.id, self.id)
            return self.RES_ERROR

        # Create NodeActions for all nodes
        action_list = []
        node_list = cluster.get_nodes()
        for node_id in node_list:
            kwargs = {
                'name': 'node-update-%s' % node_id,
                'context': self.context,
                'target': node_id,
                'cause': 'Cluster update',
                'inputs': {
                    'new_profile_id': new_profile_id,
                }
            }
            action = Action(self.context, 'NODE_UPDATE', **kwargs)
            action_list.append(action)
            action.set_status(self.READY)

            # add new action to waiting/dependency list
            # TODO: need db_api support
            db_api.action_add_dependency(action, self)

        # Notify dispatcher
        for action in action_list:
            dispatcher.notify(self.context,
                              dispatcher.Dispatcher.NEW_ACTION,
                              None,
                              action_id=action.id)

        # Wait for cluster updating complete
        # TODO: need db support
        while self.get_status() != self.READY:
            if scheduler.action_cancelled(self):
                # During this period, if cancel request come,
                # cancel this cluster updating, including all
                # possible in-progress node update actions.
                LOG.debug('Cluster updating action %s cancelled' % self.id)
                self._cancel_update(cluster, old_profile_id)
                return self.RES_CANCEL
            elif scheduler.action_timeout(self):
                # Action timeout, return
                LOG.debug('Cluster updating action %s timeout' % self.id)
                cluster.set_status(cluster.ERROR, 'cluster updating timeout')
                db_api.cluster_lock_release(cluster.id, self.id)
                return self.RES_TIMEOUT

            # Continue waiting (with sleep)
            scheduler.reschedule(self, sleep=0)

        # Cluster updating finished, set its status
        # to active and release lock
        cluster.set_status(cluster.ACTIVE, 'Cluster updating completed')
        db_api.cluster_lock_release(cluster.id, self.id)

        return self.RES_OK

    def _cancel_update(self, cluster, old_profile_id):
        node_list = cluster.get_nodes()
        for node_id in node_list:
            # We try to search node related action in DB
            # TODO: we need a new db_api interface here
            node_action = db_api.action_get_by_target(node_id)
            if not node_action:
                # Node action doesn't exist which means this
                # action has been executed successfully, we
                # don't do anything to it
                continue
            elif db_api.action_lock_check(self.context, node_action.id):
                # If node action exist and is now in progress,
                # try to cancel it.
                scheduler.cancel_action(self.context, node_action.id)
            else:
                # Node action exist and not been locked,
                # try to lock it and remove it from DB.

                # Just use action_id as the owner_id when lock action
                action = db_api.action_start_work_on(self.context,
                                                     node_action.id,
                                                     node_action.id)
                if action:
                    # Get lock successfully, delete this action
                    db_api.action_delete(action.id)
                else:
                    # Action is locked by other worker, cancel it
                    scheduler.cancel_action(self.context, action.id)

            # Restore node obj
            node = db_api.node_get(self.context, node_id)
            node.do_update(self.context, profile_id=old_profile_id)

        # We don't wait for node action cancel finishing
        # TODO: may need more discussion

        # Restore cluster based on old profile
        res = cluster.do_update(self.context, profile_id=old_profile_id)

        cluster.set_status(cluster.UPDATE_CANCELLED)
        db_api.cluster_lock_release(cluster.id, self.id)

        return res

    def do_delete(self, cluster):
        # Set cluster status to DELETING
        cluster.set_status(cluster.DELETING)
        # Try to lock the cluster
        worker_id = db_api.cluster_lock_create(cluster.id, self.id)
        if worker_id != self.id:
            # Lock cluster failed, other action of this cluster
            # is in progress, try to cancel it.
            scheduler.cancel_action(self.context, worker_id)

            # Sleep until this action get the lock or timeout
            while db_api.cluster_lock_create(cluster.id, self.id) != self.id:
                if scheduler.action_timeout(self):
                    # Action timeout, set cluster status to ERROR and return
                    LOG.debug('Cluster deleting action %s timeout' % self.id)
                    cluster.set_status(cluster.ERROR, 
                        'Cluster wait for deleting timeout')
                    return self.RES_TIMEOUT
                # Sleep for a while
                scheduler.reschedule(self, sleep=0)

        action_list = []
        node_list = cluster.get_nodes()
        for node_id in node_list:
            kwargs = {
                'name': 'node-delete-%s' % node_id,
                'context': self.context,
                'target': node_id,
                'cause': 'Cluster delete',
            }
            action = Action(self.context, 'NODE_DELETE', **kwargs)
            action_list.append(action)
            action.set_status(self.READY)

            # add new action to waiting/dependency list
            db_api.action_add_dependency(action, self)

        # Notify dispatcher
        for action in action_list:
            dispatcher.notify(self.context,
                              dispatcher.Dispatcher.NEW_ACTION,
                              None,
                              action_id=action.id)

        # Wait for cluster creating complete
        # TODO: need db supportting dependency based status management
        while self.get_status() != self.READY:
            if scheduler.action_cancelled(self):
                # During this period, if cancel request come,
                # cancel this cluster deleting immediately, then
                # release the cluster lock and return.
                LOG.debug('Cluster deleting action %s cancelled' % self.id)
                cluster.set_status(cluster.ERROR,
                                   'Cluster deleting cancelled')
                db_api.cluster_lock_release(cluster.id, self.id)
                return self.RES_CANCEL
            elif scheduler.action_timeout(self):
                # Action timeout, set cluster status to ERROR and return
                LOG.debug('Cluster deleting action %s timeout' % self.id)
                cluster.set_status(cluster.ERROR, 
                                  'Cluster deleting timeout')
                db_api.cluster_lock_release(cluster.id, self.id)
                return self.RES_TIMEOUT

            # Continue waiting (with sleep)
            scheduler.reschedule(self, sleep=0)

        # Cluster is deleted successfully, set its
        # status to DELETE and release the lock.
        cluster.do_delete(self.context)
        db_api.cluster_lock_release(cluster.id, self.id)

        return self.RES_OK

    def do_add_nodes(self, cluster):
        return self.RES_OK

    def do_del_nodes(self, cluster):
        return self.RES_OK

    def do_scale_up(self, cluster):
        return self.RES_OK

    def do_scale_down(self, cluster):
        return self.RES_OK

    def do_attach_policy(self, cluster):
        policy_id = self.inputs.get('policy_id', None)
        if policy_id is None:
            raise exception.PolicyNotSpecified()

        policy = policies.load(self.context, policy_id)
        # Check if policy has already been attached
        all = db_api.cluster_get_policies(self.context, cluster.id)
        for existing in all:
            # Policy already attached
            if existing.id == policy_id:
                return self.RES_OK

            if existing.type == policy.type:
                raise exception.PolicyExists(policy_type=policy.type)

        values = {
            'cooldown': self.inputs.get('cooldown', policy.cooldown),
            'level': self.inputs.get('level', policy.level),
            'enabled': self.inputs.get('enabled', True),
        }

        db_api.cluster_attach_policy(self.context, cluster.id, policy_id,
                                     values)

        cluster.rt.policies.append(policy)
        return self.RES_OK

    def do_detach_policy(self, cluster):
        return self.RES_OK

    def execute(self, **kwargs):
        res = False
        cluster = db_api.cluster_get(self.context, self.target)
        if not cluster:
            return self.RES_ERROR

        if self.action == self.CLUSTER_CREATE:
            res = self.do_create(cluster)
        elif self.action == self.CLUSTER_UPDATE:
            new_profile_id = self.inputs.get('new_profile_id')
            res = self.do_update(cluster, new_profile_id)
        elif self.action == self.CLUSTER_DELETE:
            res = self.do_delete(cluster)
        elif self.action == self.CLUSTER_ADD_NODES:
            res = self.do_add_nodes(cluster)
        elif self.action == self.CLUSTER_DEL_NODES:
            res = self.do_del_nodes(cluster)
        elif self.action == self.CLUSTER_SCALE_UP:
            res = self.do_scale_up(cluster)
        elif self.action == self.CLUSTER_SCALE_DOWN:
            res = self.do_scale_down(cluster)
        elif self.action == self.CLUSTER_ATTACH_POLICY:
            res = self.do_attach_policy(cluster)
        elif self.action == self.CLUSTER_DETACH_POLICY:
            res = self.do_detach_policy(cluster)

        return res

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

    def execute(self, **kwargs):
        res = False
        node = nodes.load(self.context, self.target)
        if not node:
            msg = _('Node with id (%s) is not found') % self.target
            raise exception.NotFound(msg)

        # TODO(Qiming): Add node status changes
        if self.action == self.NODE_CREATE:
            res = node.do_create()
        elif self.action == self.NODE_DELETE:
            res = node.do_delete()
        elif self.action == self.NODE_UPDATE:
            new_profile_id = self.inputs.get('new_profile_id')
            res = node.do_update(new_profile_id)
        elif self.action == self.NODE_JOIN_CLUSTER:
            new_cluster_id = self.inputs.get('cluster_id', None)
            if not new_cluster_id:
                raise exception.ClusterNotSpecified()
            res = node.do_join(new_cluster_id)
        elif self.action == self.NODE_LEAVE_CLUSTER:
            res = node.do_leave()

        return self.RES_OK if res else self.RES_ERROR

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
