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
import random

from senlin.common import exception
from senlin.common.i18n import _
from senlin.db import api as db_api
from senlin.engine import dispatcher
from senlin.engine import node as nodes
from senlin.engine import scheduler
from senlin.engine.actions.base import Action
from senlin.openstack.common import log as logging
from senlin.policies import base as policies

LOG = logging.getLogger(__name__)


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
        action_id = db_api.cluster_lock_create(cluster.id, self.id)
        if action_id != self.id:
            # This cluster has been locked by other action?
            # This should never happen here, raise an execption.
            LOG.error(_('Cluster has been locked by %s before creation.'),
                      action_id)
            msg = _('Cluster is already locked by action %(old)s, action '
                    '%(new)s failed grabbing the lock') % {
                        'old': action_id, 'new': self.id}
            raise exception.Error(msg)

        res = cluster.do_create()
        if not res:
            cluster.set_status(cluster.ERROR, 'Cluster creation failed')
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
            action.store(self.context)

            action_list.append(action.id)

            db_api.action_add_dependency(action.id, self.id)
            action.set_status(self.READY)

        # Notify dispatcher
        for action_id in action_list:
            dispatcher.notify(self.context,
                              dispatcher.Dispatcher.NEW_ACTION,
                              None,
                              action_id=action_id)

        # Wait for cluster creating complete
        # TODO(anyone): need db support
        while self.get_status() != self.READY:
            if scheduler.action_cancelled(self):
                # During this period, if cancel request come,
                # cancel this cluster creating immediately, then
                # release the cluster lock and return.
                LOG.debug('Cluster creation action %s cancelled' % self.id)
                cluster.set_status(cluster.ERROR, 'Cluster creation cancelled')
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

        cluster.set_status(cluster.ACTIVE, 'Cluster creation completed')
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
        # TODO(anyone): update this comment
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
            # TODO(anyone): need db_api support
            db_api.action_add_dependency(action, self)

        # Notify dispatcher
        for action in action_list:
            dispatcher.notify(self.context,
                              dispatcher.Dispatcher.NEW_ACTION,
                              None,
                              action_id=action.id)

        # Wait for cluster updating complete
        # TODO(anyone): need db support
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
            # TODO(anyone): we need a new db_api interface here
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
        # TODO(anyone): may need more discussion

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
                                       'Cluster deletion timed out waiting')
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
        # TODO(anyone): need db supportting dependency based status management
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
                LOG.debug('Cluster deleting action %s timed out' % self.id)
                cluster.set_status(cluster.ERROR,
                                   'Cluster deletion timed out')
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
        # Try to lock the cluster
        action_id = db_api.cluster_lock_create(cluster.id, self.id)
        if action_id != self.id:
            # Lock cluster failed, other action of this cluster
            # is in progress, give up this scaling down operation.
            return self.RES_RETRY

        # Go through all policies before scaling down.
        policy_target = ('BEFORE', self.action)
        result = self.policy_check(self.context, cluster.id, policy_target)
        if not result:
            # Policy check failed, release lock and return ERROR
            db_api.cluster_lock_release(cluster.id, self.id)
            return self.RES_ERROR

        count = result.get('count', 0)
        if count == 0:
            return self.RES_ERROR

        candidates = result.get('candidates', [])
        if len(candidates) == 0:
            # No candidates for scaling down op which means no DeletionPolicy
            # is attached to cluster, we just choose random nodes to
            # delete based on scaling policy result.
            nodes = db_api.node_get_all_by_cluster(self.context,
                                                   self.cluster_id)
            # TODO(anyone): add some warning here
            if count > len(nodes):
                count = len(nodes)

            i = count
            while i > 0:
                rand = random.randrange(i)
                candidates.append(nodes[rand].id)
                nodes.remove(nodes[rand])
                i = i - 1

        action_list = []
        for node_id in candidates:
            kwargs = {
                'name': 'node-delete-%s' % node_id,
                'context': self.context,
                'target': node_id,
                'cause': 'Cluster scale down',
            }
            action = Action(self.context, 'NODE_DELETE', **kwargs)
            action.store(self.context)

            action_list.append(action.id)
            db_api.action_add_dependency(action, self)
            action.set_status(self.READY)

        # Notify dispatcher
        for action_id in action_list:
            dispatcher.notify(self.context,
                              dispatcher.Dispatcher.NEW_ACTION,
                              None,
                              action_id=action_id)

        # Wait for cluster creating complete. If timeout,
        # set cluster status to error.
        # Note: we don't allow to cancel scaling operations.
        while self.get_status() != self.READY:
            if scheduler.action_timeout(self):
                # Action timeout, set cluster status to ERROR and return
                LOG.debug('Cluster scale_down action %s timeout' % self.id)
                cluster.set_status(cluster.ERROR,
                                   'Cluster scaling down timeout')
                db_api.cluster_lock_release(cluster.id, self.id)
                return self.RES_TIMEOUT

            # Continue waiting (with sleep)
            scheduler.reschedule(self, sleep=0)

        cluster.delete_nodes(candidates)

        # Go through policies again to handle some post_ops e.g. LB
        policy_target = ('AFTER', self.action)
        result = self.policy_check(self.context, cluster.id, policy_target)
        if not result:
            db_api.cluster_lock_release(cluster.id, self.id)
            return self.RES_ERROR

        # set cluster status to OK and release the lock.
        db_api.cluster_lock_release(cluster.id, self.id)

        return self.RES_OK

    def do_attach_policy(self, cluster):
        policy_id = self.inputs.get('policy_id', None)
        if not policy_id:
            raise exception.PolicyNotSpecified()

        policy = policies.Policy.load(self.context, policy_id)
        # Check if policy has already been attached
        all = db_api.cluster_get_policies(self.context, cluster.id)
        for existing in all:
            # Policy already attached
            if existing.policy_id == policy_id:
                return self.RES_OK

            # Detect policy type conflicts
            curr = policies.Policy.load(self.context, existing.policy_id)
            if curr.type == policy.type:
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
