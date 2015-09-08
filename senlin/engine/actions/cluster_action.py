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
import random

from oslo_log import log as logging

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import scaleutils
from senlin.db import api as db_api
from senlin.engine.actions import base
from senlin.engine import cluster as cluster_mod
from senlin.engine import cluster_policy as cp_mod
from senlin.engine import dispatcher
from senlin.engine import event as event_mod
from senlin.engine import node as node_mod
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.policies import base as policy_mod

LOG = logging.getLogger(__name__)


class ClusterAction(base.Action):
    '''An action performed on a cluster.'''

    ACTIONS = (
        CLUSTER_CREATE, CLUSTER_DELETE, CLUSTER_UPDATE,
        CLUSTER_ADD_NODES, CLUSTER_DEL_NODES,
        CLUSTER_RESIZE,
        CLUSTER_SCALE_OUT, CLUSTER_SCALE_IN,
        CLUSTER_ATTACH_POLICY, CLUSTER_DETACH_POLICY, CLUSTER_UPDATE_POLICY
    ) = (
        consts.CLUSTER_CREATE, consts.CLUSTER_DELETE, consts.CLUSTER_UPDATE,
        consts.CLUSTER_ADD_NODES, consts.CLUSTER_DEL_NODES,
        consts.CLUSTER_RESIZE,
        consts.CLUSTER_SCALE_OUT, consts.CLUSTER_SCALE_IN,
        consts.CLUSTER_ATTACH_POLICY, consts.CLUSTER_DETACH_POLICY,
        consts.CLUSTER_UPDATE_POLICY,
    )

    def _wait_for_dependents(self):
        status = self.get_status()
        reason = ''
        while status != self.READY:
            if status == self.FAILED:
                reason = _('%(action)s [%(id)s] failed') % {
                    'action': self.action, 'id': self.id[:8]}
                LOG.debug(reason)
                return self.RES_ERROR, reason

            if self.is_cancelled():
                # During this period, if cancel request comes, cancel this
                # operation immediately, then release the cluster lock
                reason = _('%(action)s [%(id)s] cancelled') % {
                    'action': self.action, 'id': self.id[:8]}
                LOG.debug(reason)
                return self.RES_CANCEL, reason

            if self.is_timeout():
                # Action timeout, return
                reason = _('%(action)s [%(id)s] timeout') % {
                    'action': self.action, 'id': self.id[:8]}
                LOG.debug(reason)
                return self.RES_TIMEOUT, reason

            # Continue waiting (with reschedule)
            scheduler.reschedule(self.id, 3)
            status = self.get_status()

        return self.RES_OK, 'All dependents ended with success'

    def _create_nodes(self, cluster, count):
        '''Utility method for node creation.'''
        placement = self.data.get('placement', None)

        db_cluster = db_api.cluster_get(self.context, cluster.id)
        index = db_cluster.next_index

        nodes = []
        for m in range(count):

            kwargs = {
                'user': cluster.user,
                'project': cluster.project,
                'domain': cluster.domain,
                'index': index + m,
                'metadata': {}
            }
            name = 'node-%s-%003d' % (cluster.id[:8], index)
            node = node_mod.Node(name, cluster.profile_id, cluster.id,
                                 context=self.context, **kwargs)

            if placement is not None:
                # We assume placement is a list
                node.data['placement'] = placement[m]
            node.store(self.context)
            nodes.append(node.id)

            kwargs = {
                'name': 'node_create_%s' % node.id[:8],
                'cause': base.CAUSE_DERIVED,
            }

            action = base.Action(self.context, node.id, 'NODE_CREATE',
                                 **kwargs)
            action.store(self.context)

            # Build dependency and make the new action ready
            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(action.READY)

            dispatcher.start_action(action_id=action.id)

        if count > 0:
            # Wait for cluster creation to complete
            res, reason = self._wait_for_dependents()
            if res == self.RES_OK:
                self.data['nodes'] = nodes
                # TODO(anyone): refresh cluster node memebership
            return res, reason

        return self.RES_OK, ''

    def do_create(self, cluster):
        res = cluster.do_create(self.context)

        if not res:
            reason = _('Cluster creation failed.')
            cluster.set_status(self.context, cluster.ERROR, reason)
            return self.RES_ERROR, reason

        result, reason = self._create_nodes(cluster, cluster.desired_capacity)

        if result == self.RES_OK:
            reason = _('Cluster creation succeeded.')
            cluster.set_status(self.context, cluster.ACTIVE, reason)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_ERROR]:
            cluster.set_status(self.context, cluster.ERROR, reason)
        else:
            # RETRY or FAILED?
            pass

        return result, reason

    def do_update(self, cluster):
        profile_id = self.inputs.get('new_profile_id')

        for node in cluster.nodes:
            kwargs = {
                'name': 'node_update_%s' % node.id[:8],
                'cause': base.CAUSE_DERIVED,
                'inputs': {
                    'new_profile_id': profile_id,
                }
            }
            action = base.Action(self.context, node.id, 'NODE_UPDATE',
                                 **kwargs)
            action.store(self.context)

            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(action.READY)
            dispatcher.start_action(action_id=action.id)

        # Wait for nodes to complete update
        result = self.RES_OK
        reason = _('Cluster update completed.')
        if len(cluster.nodes) > 0:
            result, new_reason = self._wait_for_dependents()

            if result != self.RES_OK:
                return result, new_reason

        # TODO(anyone): this seems an overhead
        cluster.profile_id = profile_id
        cluster.store(self.context)

        cluster.set_status(self.context, cluster.ACTIVE, reason)
        return self.RES_OK, reason

    def _delete_nodes(self, cluster, nodes):
        action_name = consts.NODE_DELETE

        pd = self.data.get('deletion', None)
        if pd is not None:
            destroy = pd.get('destroy_after_delete', True)
            if not destroy:
                action_name = consts.NODE_LEAVE

        for node_id in nodes:
            action = base.Action(self.context, node_id, action_name,
                                 name='node_delete_%s' % node_id[:8],
                                 cause=base.CAUSE_DERIVED)
            action.store(self.context)

            # Build dependency and make the new action ready
            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(action.READY)

            dispatcher.start_action(action_id=action.id)

        if len(nodes) > 0:
            res, reason = self._wait_for_dependents()
            if res == self.RES_OK:
                self.data['nodes'] = nodes
                # TODO(anyone): refresh cluster node memebership
            return res, reason

        return self.RES_OK, ''

    def do_delete(self, cluster):
        reason = _('Deletion in progress.')
        cluster.set_status(self.context, cluster.DELETING, reason)
        node_ids = [node.id for node in cluster.nodes]

        # For cluster delete, we delete the nodes
        data = {
            'deletion': {
                'destroy_after_delete': True
            }
        }
        self.data.update(data)
        result, reason = self._delete_nodes(cluster, node_ids)

        if result == self.RES_OK:
            res = cluster.do_delete(self.context)
            if not res:
                return self.RES_ERROR, _('Cannot delete cluster object.')
        elif result == self.RES_CANCEL:
            cluster.set_status(self.context, cluster.ACTIVE, reason)
        elif result in [self.RES_TIMEOUT, self.RES_ERROR]:
            cluster.set_status(self.context, cluster.WARNING, reason)
        else:
            # RETRY
            pass

        return result, reason

    def do_add_nodes(self, cluster):
        nodes = self.inputs.get('nodes')

        errors = []
        for node_id in nodes:
            try:
                node = node_mod.Node.load(self.context, node_id)
            except exception.NodeNotFound:
                errors.append(_('Node [%s] is not found.') % node_id)
                continue

            if node.cluster_id == cluster.id:
                nodes.remove(node_id)
                continue

            if node.cluster_id is not None:
                errors.append(_('Node [%(n)s] is already owned by cluster '
                                '[%(c)s].') % {'n': node_id,
                                               'c': node.cluster_id})
                continue
            if node.status != node.ACTIVE:
                errors.append(_('Node [%s] is not in ACTIVE status.'
                                ) % node_id)
                continue

        if len(errors) > 0:
            return self.RES_ERROR, ''.join(errors)

        reason = _('Completed adding nodes.')
        if len(nodes) == 0:
            return self.RES_OK, reason

        for node_id in nodes:
            action = base.Action(self.context, node_id, 'NODE_JOIN',
                                 name='node_join_%s' % node_id[:8],
                                 cause=base.CAUSE_DERIVED,
                                 inputs={'cluster_id': cluster.id})
            action.store(self.context)
            db_api.action_add_dependency(self.context, action.id, self.id)
            action.set_status(self.READY)
            dispatcher.start_action(action_id=action.id)

        # Wait for dependent action if any
        result, new_reason = self._wait_for_dependents()
        if result != self.RES_OK:
            reason = new_reason
        else:
            self.data['nodes'] = nodes

        return result, reason

    def do_del_nodes(self, cluster):
        nodes = self.inputs.get('nodes', [])

        node_ids = copy.deepcopy(nodes)
        errors = []
        for node_id in node_ids:
            try:
                node = db_api.node_get(self.context, node_id)
            except exception.NodeNotFound:
                errors.append(_('Node [%s] is not found.') % node_id)
                continue
            if (node.cluster_id is None) or (node.cluster_id != cluster.id):
                nodes.remove(node_id)

        if len(errors) > 0:
            return self.RES_ERROR, ''.join(errors)

        reason = _('Completed deleting nodes.')
        if len(nodes) == 0:
            return self.RES_OK, reason

        # For deleting nodes from cluster, set destroy to false
        data = {
            'deletion': {
                'destroy_after_delete': False,
            }
        }
        self.data.update(data)
        result, new_reason = self._delete_nodes(cluster, nodes)

        if result != self.RES_OK:
            reason = new_reason
        return result, reason

    def _update_cluster_properties(self, cluster, desired, min_size, max_size):
        # update cluster properties related to size and profile

        need_store = False
        if min_size is not None and min_size != cluster.min_size:
            cluster.min_size = min_size
            need_store = True
        if max_size is not None and max_size != cluster.max_size:
            cluster.max_size = max_size
            need_store = True
        if desired is not None and desired != cluster.desired_capacity:
            cluster.desired_capacity = desired
            need_store = True

        if need_store is False:
            return self.RES_OK, ''

        cluster.status_reason = _('Cluster properties updated.')
        cluster.store(self.context)
        return self.RES_OK, ''

    def do_resize(self, cluster):
        adj_type = self.inputs.get(consts.ADJUSTMENT_TYPE, None)
        number = self.inputs.get(consts.ADJUSTMENT_NUMBER, None)
        min_size = self.inputs.get(consts.ADJUSTMENT_MIN_SIZE, None)
        max_size = self.inputs.get(consts.ADJUSTMENT_MAX_SIZE, None)
        min_step = self.inputs.get(consts.ADJUSTMENT_MIN_STEP, None)
        strict = self.inputs.get(consts.ADJUSTMENT_STRICT, False)

        desired = cluster.desired_capacity
        if adj_type is not None:
            # number must be not None according to previous tests
            desired = scaleutils.calculate_desired(
                desired, adj_type, number, min_step)

        # truncate adjustment if permitted (strict==False)
        if strict is False:
            desired = scaleutils.truncate_desired(
                cluster, desired, min_size, max_size)

        # check provided params against current properties
        # desired is checked when strict is True
        result = scaleutils.check_size_params(cluster, desired, min_size,
                                              max_size, strict)
        if result != '':
            return self.RES_ERROR, result

        # save sanitized properties
        self._update_cluster_properties(cluster, desired, min_size,
                                        max_size)
        node_list = cluster.nodes
        current_size = len(node_list)

        # delete nodes if necessary
        if desired < current_size:
            adjustment = current_size - desired
            if 'deletion' not in self.data:
                self.data['deletion'] = {'count': adjustment}
            candidates = []
            # Choose victims randomly
            i = adjustment
            while i > 0:
                r = random.randrange(len(node_list))
                candidates.append(node_list[r].id)
                node_list.remove(node_list[r])
                i = i - 1

            result, reason = self._delete_nodes(cluster, candidates)
            if result != self.RES_OK:
                return result, reason

        # Create new nodes if desired_capacity increased
        if desired > current_size:
            delta = desired - current_size
            self.data['creation'] = {'count': delta}
            result, reason = self._create_nodes(cluster, delta)
            if result != self.RES_OK:
                return result, reason

        reason = _('Cluster resize succeeded.')
        cluster.set_status(self.context, cluster.ACTIVE, reason)
        return self.RES_OK, reason

    def do_scale_out(self, cluster):
        # We use policy output if any, or else the count is
        # set to 1 as default.
        pd = self.data.get('creation', None)
        if pd is not None:
            count = pd.get('count', 1)
        else:
            # If no scaling policy is attached, use the
            # input count directly
            count = self.inputs.get('count', 1)

        if count <= 0:
            reason = _('Invalid count (%s) for scaling out.') % count
            return self.RES_ERROR, reason

        # check provided params against current properties
        # desired is checked when strict is True
        curr_size = len(cluster.nodes)
        new_size = curr_size + count

        result = scaleutils.check_size_params(cluster, new_size,
                                              None, None, True)
        if result != '':
            return self.RES_ERROR, result

        # Update desired_capacity of cluster
        # TODO(anyone): make this behavior customizable
        self._update_cluster_properties(cluster, new_size, None, None)

        result, reason = self._create_nodes(cluster, count)

        if result == self.RES_OK:
            reason = _('Cluster scaling succeeded.')
            cluster.set_status(self.context, cluster.ACTIVE, reason)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_ERROR]:
            cluster.set_status(self.context, cluster.ERROR, reason)
        else:
            # RETRY?
            pass

        return result, reason

    def do_scale_in(self, cluster):
        # We use policy data if any, or else the count is
        # set to 1 as default.
        pd = self.data.get('deletion', None)
        if pd is not None:
            count = pd.get('count', 1)
            candidates = pd.get('candidates', [])
        else:
            # If no scaling policy is attached, use the input count directly
            count = self.inputs.get('count', 1)
            candidates = []

        if count <= 0:
            reason = _('Invalid count (%s) for scaling in.') % count
            return self.RES_ERROR, reason

        # check provided params against current properties
        # desired is checked when strict is True
        curr_size = len(cluster.nodes)
        if count > curr_size:
            LOG.warning(_('Triming count (%(count)s) to current cluster size '
                          '(%(curr)s) for scaling in'),
                        {'count': count, 'curr': curr_size})
            count = curr_size
        new_size = curr_size - count

        result = scaleutils.check_size_params(cluster, new_size,
                                              None, None, False)
        if result != '':
            return self.RES_ERROR, result

        # Update desired_capacity of cluster
        # TODO(anyone): make this behavior customizable
        self._update_cluster_properties(cluster, new_size, None, None)

        # Choose victims randomly
        if len(candidates) == 0:
            ids = [node.id for node in cluster.nodes]
            i = count
            while i > 0:
                r = random.randrange(len(ids))
                candidates.append(ids[r])
                ids.remove(ids[r])
                i = i - 1

        # The policy data may contain destroy flag and grace period option
        result, reason = self._delete_nodes(cluster, candidates)

        if result == self.RES_OK:
            reason = _('Cluster scaling succeeded.')
            cluster.set_status(self.context, cluster.ACTIVE, reason)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_ERROR]:
            cluster.set_status(self.context, cluster.ERROR, reason)
        else:
            # RETRY or FAILED?
            pass

        return result, reason

    def do_attach_policy(self, cluster):
        '''Attach policy to the cluster.'''

        policy_id = self.inputs.get('policy_id', None)
        if not policy_id:
            return self.RES_ERROR, _('Policy not specified.')

        policy = policy_mod.Policy.load(self.context, policy_id)
        # Check if policy has already been attached
        for existing in cluster.policies:
            # Policy already attached
            if existing.id == policy_id:
                return self.RES_OK, _('Policy already attached.')

            # Detect policy type conflicts
            if (existing.type == policy.type) and policy.singleton:
                reason = _('Only one instance of policy type (%(ptype)s) can '
                           'be attached to a cluster, but another instance '
                           '(%(existing)s) is found attached to the cluster '
                           '(%(cluster)s) already.'
                           ) % {'ptype': policy.type,
                                'existing': existing.id,
                                'cluster': cluster.id}
                return self.RES_ERROR, reason

        res, data = policy.attach(cluster)
        if not res:
            return self.RES_ERROR, data

        # Initialize data field of cluster_policy object with information
        # generated during policy attaching
        values = {
            'priority': self.inputs['priority'],
            'cooldown': self.inputs['cooldown'],
            'level': self.inputs['level'],
            'enabled': self.inputs['enabled'],
            'data': data,
        }

        cp = cp_mod.ClusterPolicy(cluster.id, policy_id, **values)
        cp.store(self.context)

        cluster.add_policy(policy)
        return self.RES_OK, _('Policy attached.')

    def do_detach_policy(self, cluster):
        '''Attach policy to the cluster.'''

        policy_id = self.inputs.get('policy_id', None)
        if not policy_id:
            return self.RES_ERROR, _('Policy not specified.')

        # Check if policy has already been attached
        found = False
        for existing in cluster.policies:
            if existing.id == policy_id:
                found = True
                break
        if not found:
            return self.RES_OK, _('Policy not attached.')

        policy = policy_mod.Policy.load(self.context, policy_id)
        res, data = policy.detach(cluster)
        if not res:
            return self.RES_ERROR, data

        db_api.cluster_policy_detach(self.context, cluster.id, policy_id)

        cluster.remove_policy(policy)
        return self.RES_OK, _('Policy detached.')

    def do_update_policy(self, cluster):
        policy_id = self.inputs.get('policy_id', None)
        if not policy_id:
            return self.RES_ERROR, _('Policy not specified.')

        # Check if policy has already been attached
        found = False
        for existing in cluster.policies:
            if existing.id == policy_id:
                found = True
                break
        if not found:
            return self.RES_ERROR, _('Policy not attached.')

        values = {}
        cooldown = self.inputs.get('cooldown')
        if cooldown is not None:
            values['cooldown'] = cooldown
        level = self.inputs.get('level')
        if level is not None:
            values['level'] = level
        priority = self.inputs.get('priority')
        if priority is not None:
            values['priority'] = priority
        enabled = self.inputs.get('enabled')
        if enabled is not None:
            values['enabled'] = bool(enabled)
        if not values:
            return self.RES_OK, _('No update is needed.')

        db_api.cluster_policy_update(self.context, cluster.id, policy_id,
                                     values)

        return self.RES_OK, _('Policy updated.')

    def _execute(self, cluster):
        # do pre-action policy checking
        self.policy_check(cluster.id, 'BEFORE')
        if self.data['status'] != policy_mod.CHECK_OK:
            reason = _('Policy check failure: %s') % self.data['reason']
            event_mod.error(cluster.id, self.action, 'Failed', reason)
            return self.RES_ERROR, reason

        result = self.RES_OK
        action_name = self.action.lower()
        method_name = action_name.replace('cluster', 'do')
        method = getattr(self, method_name, None)
        if method is None:
            error = _('Unsupported action: %s.') % self.action
            event_mod.error(cluster.id, self.action, 'Failed', error)
            return self.RES_ERROR, error

        result, reason = method(cluster)

        # do post-action policy checking
        if result == self.RES_OK:
            self.policy_check(cluster.id, 'AFTER')
            if self.data['status'] != policy_mod.CHECK_OK:
                error = _('Policy check failure: %s') % self.data['reason']
                event_mod.error(cluster.id, self.action, 'Failed', error)
                return self.RES_ERROR, error

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
        except exception.ClusterNotFound:
            reason = _('Cluster (%(id)s) is not found') % {'id': self.target}
            event_mod.error(self.target, self.action, 'Failed', reason)
            return self.RES_ERROR, reason

        # Try to lock cluster before do real operation
        forced = True if self.action == self.CLUSTER_DELETE else False
        res = senlin_lock.cluster_lock_acquire(cluster.id, self.id,
                                               senlin_lock.CLUSTER_SCOPE,
                                               forced)
        if not res:
            return self.RES_ERROR, _('Failed in locking cluster.')

        try:
            res, reason = self._execute(cluster)
        finally:
            senlin_lock.cluster_lock_release(cluster.id, self.id,
                                             senlin_lock.CLUSTER_SCOPE)

        return res, reason

    def cancel(self):
        return self.RES_OK
