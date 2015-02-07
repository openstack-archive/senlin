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

import random

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.db import api as db_api
from senlin.engine.actions import base
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import node as node_mod
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.openstack.common import log as logging
from senlin.policies import base as policy_mod

LOG = logging.getLogger(__name__)


class ClusterAction(base.Action):
    '''An action performed on a cluster.'''

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

    def _wait_for_dependents(self):
        self.get_status()
        reason = ''
        while self.status != self.READY:
            if self.status == self.FAILED:
                reason = _('%(action)s [%(id)s] failed due to dependent '
                           'action failure') % {'action': self.action,
                                                'id': self.id}
                LOG.debug(reason)
                return self.RES_ERROR, reason

            if self.is_cancelled():
                # During this period, if cancel request come, cancel this
                # cluster operation immediately, then release the cluster
                # lock and return.
                reason = _('%(action)s %(id)s cancelled') % {
                    'action': self.action, 'id': self.id}
                LOG.debug(reason)
                return self.RES_CANCEL, reason

            if self.is_timeout():
                # Action timeout, return
                reason = _('%(action)s %(id)s timeout') % {
                    'action': self.action, 'id': self.id}
                LOG.debug(reason)
                return self.RES_TIMEOUT

            # Continue waiting (with reschedule)
            scheduler.reschedule(self, 1)
            self.get_status()

        return self.RES_OK, 'All dependents ended with success'

    def do_create(self, cluster, policy_data):
        reason = 'Cluster creation succeeded'
        res = cluster.do_create(self.context)

        if not res:
            reason = 'Cluster creation failed.'
            cluster.set_status(cluster.ERROR, reason)
            return self.RES_ERROR, reason

        for m in range(cluster.size):
            name = 'node-%s-%003d' % (cluster.id[:8], m + 1)
            node = node_mod.Node(name, cluster.profile_id, cluster.id,
                                 context=self.context)
            node.store(self.context)
            kwargs = {
                'name': 'node_create_%s' % node.id[:8],
                'target': node.id,
                'cause': base.CAUSE_DERIVED,
            }

            action = base.Action(self.context, 'NODE_CREATE', **kwargs)
            action.store(self.context)

            # Build dependency and make the new action ready
            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(self.READY)

            dispatcher.notify(self.context, dispatcher.Dispatcher.NEW_ACTION,
                              None, action_id=action.id)

        # Wait for cluster creating complete
        result = self.RES_OK
        if cluster.size > 0:
            result, reason = self._wait_for_dependents()

        if result == self.RES_OK:
            cluster.set_status(self.context, cluster.ACTIVE, reason)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_FAILED]:
            cluster.set_status(self.context, cluster.ERROR, reason)
        else:
            # RETRY or FAILED?
            pass

        return result, reason

    def do_update(self, cluster, policy_data):
        reason = 'Cluster update succeeded'
        new_profile_id = self.inputs.get('new_profile_id')
        res = cluster.do_update(self.context, profile_id=new_profile_id)
        if not res:
            reason = 'Cluster object cannot be updated.'
            # Reset status to active
            cluster.set_status(cluster.ACTIVE, reason)
            return self.RES_ERROR

        # Create NodeActions for all nodes
        node_list = cluster.get_nodes()
        for node_id in node_list:
            kwargs = {
                'name': 'node_update_%s' % node_id[:8],
                'target': node_id,
                'cause': base.CAUSE_DERIVED,
                'inputs': {
                    'new_profile_id': new_profile_id,
                }
            }
            action = base.Action(self.context, 'NODE_UPDATE', **kwargs)
            action.store(self.context)

            db_api.action_add_dependency(action, self)
            action.set_status(self.READY)
            dispatcher.notify(self.context, dispatcher.Dispatcher.NEW_ACTION,
                              None, action_id=action.id)

        # Wait for cluster updating complete
        result = self.RES_OK
        if cluster.size > 0:
            result, reason = self._wait_for_dependents()

        if result == self.RES_OK:
            cluster.set_status(self.context, cluster.ACTIVE, reason)

        return result, reason

    def do_delete(self, cluster, policy_data):
        reason = 'Deletion in progress'
        cluster.set_status(self.context, cluster.DELETING, reason)
        node_list = cluster.get_nodes()

        for node in node_list:
            action = base.Action(self.context, 'NODE_DELETE',
                                 name='node_delete_%s' % node.id[:8],
                                 target=node.id,
                                 cause=base.CAUSE_DERIVED)
            action.store(self.context)

            # Build dependency and make the new action ready
            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(self.READY)

            dispatcher.notify(self.context, dispatcher.Dispatcher.NEW_ACTION,
                              None, action_id=action.id)

        result = self.RES_OK
        reason = 'Cluster deletion completed'
        if cluster.size > 0 and len(node_list) > 0:
            # The size may not be accurate, so we check the node_list as well
            result, reason = self._wait_for_dependents()

        if result == self.RES_OK:
            res = cluster.do_delete(self.context)
            if not res:
                return self.RES_ERROR, 'Cannot delete cluster object.'

        if result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_FAILED]:
            cluster.set_status(self.context, cluster.ACTIVE, reason)
        else:
            # RETRY
            pass

        return result, reason

    def do_add_nodes(self, cluster, policy_data=None):
        nodes = self.inputs.get('nodes')

        # NOTE: node states might have changed before we lock the cluster
        failures = {}
        for node_id in nodes:
            try:
                node = node_mod.Node.load(self.context, node_id)
            except exception.NodeNotFound:
                failures[node_id] = 'Node not found'
                continue

            if node.cluster_id == cluster.id:
                nodes.remove(node_id)
                continue

            if node.cluster_id is not None:
                failures[node_id] = _('Node already owned by cluster '
                                      '%s') % node.cluster_id
                continue
            if node.status != node_mod.Node.ACTIVE:
                failures[node_id] = _('Node not in ACTIVE status')
                continue

            # check profile type matching
            node_profile_type = node.rt['profile'].type
            cluster_profile_type = cluster.rt['profile'].type
            if node_profile_type != cluster_profile_type:
                failures[node.id] = 'Profile type does not match'
                continue

        if len(failures) > 0:
            return self.RES_ERROR, str(failures)

        reason = 'Completed adding nodes'
        if len(nodes) == 0:
            return self.RES_OK, reason

        for node_id in nodes:
            action = base.Action(self.context, 'NODE_JOIN',
                                 name='node_join_%s' % node.id[:8],
                                 target=node.id,
                                 cause=base.CAUSE_DERIVED,
                                 inputs={'cluster_id': cluster.id})
            action.store(self.context)
            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(self.READY)
            dispatcher.notify(self.context, dispatcher.Dispatcher.NEW_ACTION,
                              None, action_id=action.id)

        # Wait for dependent action if any
        result, new_reason = self._wait_for_dependents()
        if result != self.RES_OK:
            reason = new_reason
        return result, reason

    def do_del_nodes(self, cluster, policy_data=None):
        nodes = self.inputs.get('nodes')

        # NOTE: node states might have changed before we lock the cluster
        failures = {}
        for node_id in nodes:
            try:
                node = node_mod.Node.load(self.context, node_id)
            except exception.NodeNotFound:
                failures[node_id] = 'Node not found'
                continue

            if node.cluster_id is None:
                nodes.remove(node_id)

        if len(failures) > 0:
            return self.RES_ERROR, str(failures)

        reason = 'Completed deleting nodes'
        if len(nodes) == 0:
            return self.RES_OK, reason

        for node_id in nodes:
            action = base.Action(self.context, 'NODE_LEAVE',
                                 name='node_leave_%s' % node_id[:8],
                                 target=node_id,
                                 cause=base.CAUSE_DERIVED)
            action.store(self.context)

            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(self.READY)
            dispatcher.notify(self.context, dispatcher.Dispatcher.NEW_ACTION,
                              None, action_id=action.id)

        result, new_reason = self._wait_for_dependents()
        if result != self.RES_OK:
            reason = new_reason
        return result, reason

    def do_scale_up(self, cluster, policy_data=None):
        return self.RES_OK, ''

    def do_scale_down(self, cluster, policy_data=None):
        count = policy_data.get('count', 0)
        # TODO(anyone): determine what 0 means here
        candidates = policy_data.get('candidates', [])

        # Go through all policies before scaling down.
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

        # TODO(Qiming): Need to rework this
        action_list = []
        for node_id in candidates:
            kwargs = {
                'name': 'node_delete_%s' % node_id[:8],
                'target': node_id,
                'cause': base.CAUSE_DERIVED,
            }
            action = base.Action(self.context, 'NODE_DELETE', **kwargs)
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
            if self.is_timeout():
                # Action timeout, set cluster status to ERROR and return
                reason = 'Cluster scale_down action %s timeout' % self.id
                LOG.debug(reason)
                return self.RES_TIMEOUT, reason

            scheduler.reschedule(self, 1)

        cluster.delete_nodes(candidates)

        # set cluster status to OK
        return self.RES_OK, ''

    def do_attach_policy(self, cluster):
        policy_id = self.inputs.get('policy_id', None)
        if not policy_id:
            raise exception.PolicyNotSpecified()

        policy = policy_mod.Policy.load(self.context, policy_id)
        # Check if policy has already been attached
        all = db_api.cluster_get_policies(self.context, cluster.id)
        for existing in all:
            # Policy already attached
            if existing.policy_id == policy_id:
                return self.RES_OK

            # Detect policy type conflicts
            curr = policy_mod.Policy.load(self.context, existing.policy_id)
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
        return self.RES_OK, ''

    def do_detach_policy(self, cluster):
        return self.RES_OK, ''

    def _execute(self, cluster):
        # do pre-action policy checking
        policy_data = self.policy_check(cluster.id, 'BEFORE')
        if policy_data.status != policy_mod.CHECK_OK:
            return self.RES_ERROR, 'Policy failure:' + policy_data.reason

        result = self.RES_OK
        action_name = self.action.lower()
        method_name = action_name.replace('cluster', 'do')
        method = getattr(self, method_name)
        if method is None:
            raise exception.ActionNotSupported(action=self.action)

        result, reason = method(cluster, policy_data=policy_data)

        # do post-action policy checking
        if result == self.RES_OK:
            policy_data = self.policy_check(cluster.id, 'AFTER')
            if policy_data.status != policy_mod.CHECK_OK:
                return self.RES_ERROR, policy_data.reason

        return result, reason

    def execute(self, **kwargs):
        '''Wrapper of action execution.
        This is mainly a wrapper that executes an action with cluster lock
        acquired.
        :return: A tuple (res, reason) that indicates whether the execution
                 was a success and why if it wasn't a success.
        '''

        try:
            cluster = cluster_mod.Cluster.load(self.context, self.target)
        except exception.NotFound:
            reason = _('Cluster %(id)s not found') % {'id': self.target}
            LOG.error(_LE(reason))
            return self.RES_ERROR, reason

        # Try to lock cluster before do real operation
        forced = True if self.action == self.CLUSTER_DELETE else False
        res = senlin_lock.cluster_lock_acquire(cluster.id, self.id,
                                               senlin_lock.CLUSTER_SCOPE,
                                               forced)
        if not res:
            return self.RES_ERROR, _('Failed locking cluster')

        try:
            res, reason = self._execute(cluster)
        finally:
            senlin_lock.cluster_lock_release(cluster.id, self.id,
                                             senlin_lock.CLUSTER_SCOPE)

        return res, reason

    def cancel(self):
        return self.RES_OK
