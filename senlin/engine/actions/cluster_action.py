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
import eventlet

from oslo_log import log as logging

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI
from senlin.common import scaleutils
from senlin.common import utils
from senlin.engine.actions import base
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.objects import action as ao
from senlin.objects import cluster as co
from senlin.objects import dependency as dobj
from senlin.objects import node as no
from senlin.policies import base as policy_mod

LOG = logging.getLogger(__name__)


class ClusterAction(base.Action):
    """An action that can be performed on a cluster."""

    ACTIONS = (
        CLUSTER_CREATE, CLUSTER_DELETE, CLUSTER_UPDATE,
        CLUSTER_ADD_NODES, CLUSTER_DEL_NODES,
        CLUSTER_RESIZE, CLUSTER_CHECK, CLUSTER_RECOVER,
        CLUSTER_SCALE_OUT, CLUSTER_SCALE_IN,
        CLUSTER_ATTACH_POLICY, CLUSTER_DETACH_POLICY, CLUSTER_UPDATE_POLICY
    ) = (
        consts.CLUSTER_CREATE, consts.CLUSTER_DELETE, consts.CLUSTER_UPDATE,
        consts.CLUSTER_ADD_NODES, consts.CLUSTER_DEL_NODES,
        consts.CLUSTER_RESIZE, consts.CLUSTER_CHECK, consts.CLUSTER_RECOVER,
        consts.CLUSTER_SCALE_OUT, consts.CLUSTER_SCALE_IN,
        consts.CLUSTER_ATTACH_POLICY, consts.CLUSTER_DETACH_POLICY,
        consts.CLUSTER_UPDATE_POLICY,
    )

    def __init__(self, target, action, context, **kwargs):
        """Constructor for cluster action.

        :param target: ID of the target cluster.
        :param action: Name of the action to be executed.
        :param context: Context used when interacting with DB layer.
        :param dict kwargs: Other optional arguments for the action.
        """
        super(ClusterAction, self).__init__(target, action, context, **kwargs)

        try:
            self.cluster = cluster_mod.Cluster.load(self.context, self.target)
        except Exception:
            self.cluster = None

    def _wait_for_dependents(self):
        """Wait for dependent actions to complete.

        :returns: A tuple containing the result and the corresponding reason.
        """
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

    def _create_nodes(self, count):
        """Utility method for node creation.

        :param count: Number of nodes to create.
        :returns: A tuple comprised of the result and reason.
        """

        if count == 0:
            return self.RES_OK, ''

        placement = self.data.get('placement', None)

        nodes = []
        child = []
        for m in range(count):
            index = co.Cluster.get_next_index(self.context, self.cluster.id)
            kwargs = {
                'index': index,
                'metadata': {},
                'user': self.cluster.user,
                'project': self.cluster.project,
                'domain': self.cluster.domain,
            }
            if placement is not None:
                # We assume placement is a list
                kwargs['data'] = {'placement': placement['placements'][m]}

            name = 'node-%s-%003d' % (self.cluster.id[:8], index)
            node = node_mod.Node(name, self.cluster.profile_id,
                                 self.cluster.id, context=self.context,
                                 **kwargs)

            node.store(self.context)
            nodes.append(node)

            kwargs = {
                'name': 'node_create_%s' % node.id[:8],
                'cause': base.CAUSE_DERIVED,
            }

            action_id = base.Action.create(self.context, node.id,
                                           consts.NODE_CREATE, **kwargs)
            child.append(action_id)

        if child:
            # Build dependency and make the new action ready
            dobj.Dependency.create(self.context, [a for a in child], self.id)
            for cid in child:
                ao.Action.update(self.context, cid,
                                 {'status': base.Action.READY})
            dispatcher.start_action()

            # Wait for cluster creation to complete
            res, reason = self._wait_for_dependents()
            if res == self.RES_OK:
                nodes_added = [n.id for n in nodes]
                self.outputs['nodes_added'] = nodes_added
                creation = self.data.get('creation', {})
                creation['nodes'] = nodes_added
                self.data['creation'] = creation
                for node in nodes:
                    self.cluster.add_node(node)
            else:
                reason = _('Failed in creating nodes.')

            return res, reason

        return self.RES_OK, ''

    def do_create(self):
        """Handler for CLUSTER_CREATE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.cluster.do_create(self.context)

        if not res:
            reason = _('Cluster creation failed.')
            self.cluster.set_status(self.context, self.cluster.ERROR, reason)
            return self.RES_ERROR, reason

        result, reason = self._create_nodes(self.cluster.desired_capacity)

        if result == self.RES_OK:
            reason = _('Cluster creation succeeded.')
            self.cluster.set_status(self.context, self.cluster.ACTIVE, reason)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_ERROR]:
            self.cluster.set_status(self.context, self.cluster.ERROR, reason)
        else:
            # in case of RES_RETRY, need to reset cluster status
            self.cluster.set_status(self.context, self.cluster.INIT)

        return result, reason

    def do_update(self):
        """Handler for CLUSTER_UPDATE action.

        :returns: A tuple consisting the result and the corresponding reason.
        """
        res = self.cluster.do_update(self.context)
        if not res:
            reason = _('Cluster update failed.')
            self.cluster.set_status(self.context, self.cluster.ERROR, reason)
            return self.RES_ERROR, reason

        name = self.inputs.get('name')
        metadata = self.inputs.get('metadata')
        timeout = self.inputs.get('timeout')
        profile_id = self.inputs.get('new_profile_id')

        if name is not None:
            self.cluster.name = name
        if metadata is not None:
            self.cluster.metadata = metadata
        if timeout is not None:
            self.cluster.timeout = timeout
        self.cluster.store(self.context)

        reason = _('Cluster update completed.')
        if profile_id is None:
            self.cluster.set_status(self.context, self.cluster.ACTIVE, reason)
            return self.RES_OK, reason

        fmt = _LI("Updating cluster '%(cluster)s': profile='%(profile)s'.")
        LOG.info(fmt, {'cluster': self.cluster.id, 'profile': profile_id})
        child = []
        for node in self.cluster.nodes:
            kwargs = {
                'name': 'node_update_%s' % node.id[:8],
                'cause': base.CAUSE_DERIVED,
                'inputs': {
                    'new_profile_id': profile_id,
                },
            }
            action_id = base.Action.create(self.context, node.id,
                                           consts.NODE_UPDATE, **kwargs)
            child.append(action_id)

        if child:
            dobj.Dependency.create(self.context, [c for c in child], self.id)
            for cid in child:
                ao.Action.update(self.context, cid,
                                 {'status': base.Action.READY})
            dispatcher.start_action()

            result, new_reason = self._wait_for_dependents()
            if result != self.RES_OK:
                new_reason = _('Failed in updating nodes.')
                self.cluster.set_status(self.context, self.cluster.WARNING,
                                        new_reason)
                return result, new_reason

        self.cluster.set_status(self.context, self.cluster.ACTIVE,
                                reason, profile_id=profile_id)
        return self.RES_OK, reason

    def _delete_nodes(self, node_ids):
        action_name = consts.NODE_DELETE

        pd = self.data.get('deletion', None)
        if pd is not None:
            destroy = pd.get('destroy_after_deletion', True)
            if not destroy:
                action_name = consts.NODE_LEAVE

        child = []
        for node_id in node_ids:
            kwargs = {
                'name': 'node_delete_%s' % node_id[:8],
                'cause': base.CAUSE_DERIVED,
            }
            action_id = base.Action.create(self.context, node_id, action_name,
                                           **kwargs)
            child.append(action_id)

        if child:
            dobj.Dependency.create(self.context, [c for c in child], self.id)
            for cid in child:
                # Build dependency and make the new action ready
                ao.Action.update(self.context, cid,
                                 {'status': base.Action.READY})
            dispatcher.start_action()

            res, reason = self._wait_for_dependents()
            if res == self.RES_OK:
                self.outputs['nodes_removed'] = node_ids
                for node_id in node_ids:
                    self.cluster.remove_node(node_id)
            else:
                reason = _('Failed in deleting nodes.')

            return res, reason

        return self.RES_OK, ''

    def _wait_before_deletion(self, period):
        eventlet.sleep(period)

    def do_delete(self):
        """Handler for the CLUSTER_DELETE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        reason = _('Deletion in progress.')
        self.cluster.set_status(self.context, self.cluster.DELETING, reason)
        node_ids = [node.id for node in self.cluster.nodes]

        # For cluster delete, we delete the nodes
        data = {
            'deletion': {
                'destroy_after_deletion': True
            }
        }
        self.data.update(data)
        result, reason = self._delete_nodes(node_ids)

        if result == self.RES_OK:
            res = self.cluster.do_delete(self.context)
            if not res:
                return self.RES_ERROR, _('Cannot delete cluster object.')
        elif result == self.RES_CANCEL:
            self.cluster.set_status(self.context, self.cluster.ACTIVE, reason)
        elif result in [self.RES_TIMEOUT, self.RES_ERROR]:
            self.cluster.set_status(self.context, self.cluster.WARNING, reason)
        else:
            # RETRY
            pass

        return result, reason

    def do_add_nodes(self):
        """Handler for the CLUSTER_ADD_NODES action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        node_ids = self.inputs.get('nodes')
        # TODO(anyone): handle placement data

        errors = []
        nodes = []
        for node_id in node_ids:
            try:
                node = node_mod.Node.load(self.context, node_id)
            except exception.NodeNotFound:
                errors.append(_('Node [%s] is not found.') % node_id)
                continue
            if node.cluster_id:
                errors.append(_('Node [%(n)s] is already owned by cluster '
                                '[%(c)s].') % {'n': node_id,
                                               'c': node.cluster_id})
                continue
            if node.status != node.ACTIVE:
                errors.append(_('Node [%s] is not in ACTIVE status.'
                                ) % node_id)
                continue
            nodes.append(node)

        if len(errors) > 0:
            return self.RES_ERROR, ''.join(errors)

        reason = _('Completed adding nodes.')

        child = []
        for node in nodes:
            kwargs = {
                'name': 'node_join_%s' % node.id[:8],
                'cause': base.CAUSE_DERIVED,
                'inputs': {'cluster_id': self.target},
            }
            action_id = base.Action.create(self.context, node.id,
                                           consts.NODE_JOIN, **kwargs)
            child.append(action_id)

        if child:
            dobj.Dependency.create(self.context, [c for c in child], self.id)
            for cid in child:
                ao.Action.update(self.context, cid,
                                 {'status': base.Action.READY})
            dispatcher.start_action()

        # Wait for dependent action if any
        result, new_reason = self._wait_for_dependents()
        if result != self.RES_OK:
            reason = new_reason
        else:
            self.cluster.desired_capacity += len(nodes)
            self.cluster.store(self.context)
            nodes_added = [n.id for n in nodes]
            self.outputs['nodes_added'] = nodes_added
            creation = self.data.get('creation', {})
            creation['nodes'] = nodes_added
            self.data['creation'] = creation
            for node in nodes:
                self.cluster.add_node(node)

        return result, reason

    def do_del_nodes(self):
        """Handler for the CLUSTER_DEL_NODES action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # Check if deletion policy is attached to the action, if is,
        # get grace_period value
        pd = self.data.get('deletion', None)
        grace_period = None
        if pd is not None:
            grace_period = self.data['deletion'].get('grace_period')
        else:  # if not, deleting nodes from cluster, don't destroy them
            data = {
                'deletion': {
                    'destroy_after_deletion': False,
                }
            }
            self.data.update(data)
        nodes = self.inputs.get('candidates', [])

        node_ids = copy.deepcopy(nodes)
        errors = []
        for node_id in node_ids:
            try:
                node = no.Node.get(self.context, node_id)
            except exception.NodeNotFound:
                errors.append(_('Node [%s] is not found.') % node_id)
                continue
            if ((not node.cluster_id) or
                    (node.cluster_id != self.cluster.id)):
                nodes.remove(node_id)

        if len(errors) > 0:
            return self.RES_ERROR, ''.join(errors)

        reason = _('Completed deleting nodes.')
        if len(nodes) == 0:
            return self.RES_OK, reason

        if grace_period is not None:
            self._wait_before_deletion(grace_period)
        result, new_reason = self._delete_nodes(nodes)

        if result != self.RES_OK:
            reason = new_reason
        else:
            self.cluster.desired_capacity -= len(nodes)
            self.cluster.store(self.context)

        return result, reason

    def _get_action_data(self, current_size):
        if 'deletion' in self.data:
            count = self.data['deletion']['count']
            desired = current_size - count
            candidates = self.data['deletion'].get('candidates', [])
        elif 'creation' in self.data:
            count = self.data['creation']['count']
            desired = current_size + count
            candidates = None
        else:
            return 0, 0, None
        return count, desired, candidates

    def do_check(self):
        """Handler for CLUSTER_CHECK action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        saved_status = self.cluster.status
        saved_reason = self.cluster.status_reason
        res = self.cluster.do_check(self.context)
        if not res:
            reason = _('Cluster checking failed.')
            self.cluster.set_status(self.context, saved_status, saved_reason)
            return self.RES_ERROR, reason

        child = []
        res = self.RES_OK
        reason = _('Cluster checking completed.')
        for node in self.cluster.nodes:
            node_id = node.id
            action_id = base.Action.create(
                self.context, node_id, consts.NODE_CHECK,
                name='node_check_%s' % node_id[:8],
                cause=base.CAUSE_DERIVED,
            )
            child.append(action_id)

        if child:
            dobj.Dependency.create(self.context, [c for c in child], self.id)
            for cid in child:
                ao.Action.update(self.context, cid,
                                 {'status': base.Action.READY})
            dispatcher.start_action()

            # Wait for dependent action if any
            res, new_reason = self._wait_for_dependents()
            if res != self.RES_OK:
                reason = new_reason

        self.cluster.set_status(self.context, saved_status, saved_reason)

        return res, reason

    def do_recover(self):
        """Handler for the CLUSTER_RECOVER action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.cluster.do_recover(self.context)
        if not res:
            reason = _('Cluster recovery failed.')
            self.cluster.set_status(self.context, self.cluster.ERROR, reason)
            return self.RES_ERROR, reason

        # process data from health_policy
        pd = self.data.get('health', None)
        if pd is None:
            pd = {
                'health': {
                    'recover_action': 'RECREATE',
                }
            }
            self.data.update(pd)
        recover_action = pd.get('recover_action', 'RECREATE')

        reason = _('Cluster recovery succeeded.')

        children = []
        for node in self.cluster.nodes:
            if node.status == 'ACTIVE':
                continue
            node_id = node.id
            action_id = base.Action.create(
                self.context, node_id, consts.NODE_RECOVER,
                name='node_recover_%s' % node_id[:8],
                cause=base.CAUSE_DERIVED,
                inputs={'operation': recover_action}
            )
            children.append(action_id)

        if children:
            dobj.Dependency.create(self.context, [c for c in children],
                                   self.id)
            for cid in children:
                ao.Action.update(self.context, cid, {'status': 'READY'})
            dispatcher.start_action()

            # Wait for dependent action if any
            res, reason = self._wait_for_dependents()

            if res != self.RES_OK:
                self.cluster.set_status(self.context, self.cluster.ERROR,
                                        reason)
                return res, reason

        self.cluster.set_status(self.context, self.cluster.ACTIVE, reason)

        return self.RES_OK, reason

    def do_resize(self):
        """Handler for the CLUSTER_RESIZE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        self.cluster.set_status(self.context, self.cluster.RESIZING,
                                'Cluster resize started.')
        node_list = self.cluster.nodes
        current_size = len(node_list)
        count, desired, candidates = self._get_action_data(current_size)
        grace_period = None
        # if policy is attached to the cluster, use policy data directly,
        # or parse resize params to get action data.
        if count == 0:
            result, reason = scaleutils.parse_resize_params(self, self.cluster)
            if result != self.RES_OK:
                status_reason = _('Cluster resizing failed: %s') % reason
                self.cluster.set_status(self.context, self.cluster.ACTIVE,
                                        status_reason)
                return result, reason
            count, desired, candidates = self._get_action_data(current_size)
        elif 'deletion' in self.data:
            grace_period = self.data['deletion'].get('grace_period', None)
        if candidates is not None and len(candidates) == 0:
            # Choose victims randomly
            candidates = scaleutils.nodes_by_random(self.cluster.nodes, count)

        # delete nodes if necessary
        if desired < current_size:
            if grace_period is not None:
                self._wait_before_deletion(grace_period)
            result, reason = self._delete_nodes(candidates)
        # Create new nodes if desired_capacity increased
        else:
            result, reason = self._create_nodes(count)

        if result != self.RES_OK:
            self.cluster.set_status(self.context, self.cluster.WARNING, reason)
            return result, reason

        reason = _('Cluster resize succeeded.')
        kwargs = {'desired_capacity': desired}
        min_size = self.inputs.get(consts.ADJUSTMENT_MIN_SIZE, None)
        max_size = self.inputs.get(consts.ADJUSTMENT_MAX_SIZE, None)
        if min_size is not None:
            kwargs['min_size'] = min_size
        if max_size is not None:
            kwargs['max_size'] = max_size
        self.cluster.set_status(self.context, self.cluster.ACTIVE, reason,
                                **kwargs)
        return self.RES_OK, reason

    def do_scale_out(self):
        """Handler for the CLUSTER_SCALE_OUT action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        self.cluster.set_status(self.context, self.cluster.RESIZING,
                                'Cluster scale out started.')
        # We use policy output if any, or else the count is
        # set to 1 as default.
        pd = self.data.get('creation', None)
        if pd is not None:
            count = pd.get('count', 1)
        else:
            # If no scaling policy is attached, use the
            # input count directly
            count = self.inputs.get('count', 1)
            try:
                count = utils.parse_int_param('count', count,
                                              allow_zero=False)
            except exception.InvalidParameter:
                reason = _('Invalid count (%s) for scaling out.') % count
                status_reason = _('Cluster scaling failed: %s') % reason
                self.cluster.set_status(self.context, self.cluster.ACTIVE,
                                        status_reason)
                return self.RES_ERROR, reason

        # check provided params against current properties
        # desired is checked when strict is True
        curr_size = len(self.cluster.nodes)
        new_size = curr_size + count

        result = scaleutils.check_size_params(self.cluster, new_size,
                                              None, None, True)
        if result:
            status_reason = _('Cluster scaling failed: %s') % result
            self.cluster.set_status(self.context, self.cluster.ACTIVE,
                                    status_reason)
            return self.RES_ERROR, result

        result, reason = self._create_nodes(count)
        if result == self.RES_OK:
            reason = _('Cluster scaling succeeded.')
            self.cluster.set_status(self.context, self.cluster.ACTIVE, reason,
                                    desired_capacity=new_size)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_ERROR]:
            self.cluster.set_status(self.context, self.cluster.ERROR, reason,
                                    desired_capacity=new_size)
        else:  # RES_RETRY
            pass

        return result, reason

    def do_scale_in(self):
        """Handler for the CLUSTER_SCALE_IN action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        self.cluster.set_status(self.context, self.cluster.RESIZING,
                                'Cluster scale in started.')
        # We use policy data if any, deletion policy and scaling policy might
        # be attached.
        pd = self.data.get('deletion', None)
        grace_period = None
        if pd is not None:
            grace_period = pd.get('grace_period', 0)
            candidates = pd.get('candidates', [])
            # if scaling policy is attached, get 'count' from action data
            count = len(candidates) or pd['count']
        else:
            # If no scaling policy is attached, use the input count directly
            candidates = []
            count = self.inputs.get('count', 1)
            try:
                count = utils.parse_int_param('count', count,
                                              allow_zero=False)
            except exception.InvalidParameter:
                reason = _('Invalid count (%s) for scaling in.') % count
                status_reason = _('Cluster scaling failed: %s') % reason
                self.cluster.set_status(self.context, self.cluster.ACTIVE,
                                        status_reason)
                return self.RES_ERROR, reason

        # check provided params against current properties
        # desired is checked when strict is True
        curr_size = len(self.cluster.nodes)
        if count > curr_size:
            LOG.warning(_('Triming count (%(count)s) to current cluster size '
                          '(%(curr)s) for scaling in'),
                        {'count': count, 'curr': curr_size})
            count = curr_size
        new_size = curr_size - count

        result = scaleutils.check_size_params(self.cluster, new_size,
                                              None, None, True)
        if result:
            status_reason = _('Cluster scaling failed: %s') % result
            self.cluster.set_status(self.context, self.cluster.ACTIVE,
                                    status_reason)
            return self.RES_ERROR, result

        # Choose victims randomly
        if len(candidates) == 0:
            candidates = scaleutils.nodes_by_random(self.cluster.nodes, count)

        if grace_period is not None:
            self._wait_before_deletion(grace_period)
        # The policy data may contain destroy flag and grace period option
        result, reason = self._delete_nodes(candidates)

        if result == self.RES_OK:
            reason = _('Cluster scaling succeeded.')
            self.cluster.set_status(self.context, self.cluster.ACTIVE, reason,
                                    desired_capacity=new_size)
        elif result in [self.RES_CANCEL, self.RES_TIMEOUT, self.RES_ERROR]:
            self.cluster.set_status(self.context, self.cluster.ERROR, reason,
                                    desired_capacity=new_size)
        else:
            # RES_RETRY
            pass

        return result, reason

    def do_attach_policy(self):
        """Handler for the CLUSTER_ATTACH_POLICY action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        inputs = dict(self.inputs)
        policy_id = inputs.pop('policy_id', None)
        if not policy_id:
            return self.RES_ERROR, _('Policy not specified.')

        res, reason = self.cluster.attach_policy(self.context, policy_id,
                                                 inputs)
        result = self.RES_OK if res else self.RES_ERROR

        # Store cluster since its data could have been updated
        if result == self.RES_OK:
            self.cluster.store(self.context)

        return result, reason

    def do_detach_policy(self):
        """Handler for the CLUSTER_DETACH_POLICY action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        policy_id = self.inputs.get('policy_id', None)
        if not policy_id:
            return self.RES_ERROR, _('Policy not specified.')

        res, reason = self.cluster.detach_policy(self.context, policy_id)
        result = self.RES_OK if res else self.RES_ERROR

        # Store cluster since its data could have been updated
        if result == self.RES_OK:
            self.cluster.store(self.context)

        return result, reason

    def do_update_policy(self):
        """Handler for the CLUSTER_UPDATE_POLICY action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        policy_id = self.inputs.pop('policy_id', None)
        if not policy_id:
            return self.RES_ERROR, _('Policy not specified.')
        res, reason = self.cluster.update_policy(self.context, policy_id,
                                                 **self.inputs)
        result = self.RES_OK if res else self.RES_ERROR
        return result, reason

    def _execute(self, **kwargs):
        """Private method for action execution.

        This function search for the handler based on the action name for
        execution and it wraps the action execution with policy checks.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # do pre-action policy checking
        self.policy_check(self.cluster.id, 'BEFORE')
        if self.data['status'] != policy_mod.CHECK_OK:
            reason = _('Policy check failure: %s') % self.data['reason']
            EVENT.error(self.context, self.cluster, self.action, 'Failed',
                        reason)
            return self.RES_ERROR, reason

        result = self.RES_OK
        action_name = self.action.lower()
        method_name = action_name.replace('cluster', 'do')
        method = getattr(self, method_name, None)
        if method is None:
            error = _('Unsupported action: %s.') % self.action
            EVENT.error(self.context, self.cluster, self.action, 'Failed',
                        error)
            return self.RES_ERROR, error

        result, reason = method()

        # do post-action policy checking
        if result == self.RES_OK:
            self.policy_check(self.cluster.id, 'AFTER')
            if self.data['status'] != policy_mod.CHECK_OK:
                error = _('Policy check failure: %s') % self.data['reason']
                EVENT.error(self.context, self.cluster, self.action, 'Failed',
                            error)
                return self.RES_ERROR, error

        return result, reason

    def execute(self, **kwargs):
        """Wrapper of action execution.

        This is mainly a wrapper that executes an action with cluster lock
        acquired.

        :returns: A tuple (res, reason) that indicates whether the execution
                 was a success and why if it wasn't a success.
        """
        # Try to lock cluster before do real operation
        forced = True if self.action == self.CLUSTER_DELETE else False
        res = senlin_lock.cluster_lock_acquire(self.context, self.target,
                                               self.id, self.owner,
                                               senlin_lock.CLUSTER_SCOPE,
                                               forced)
        if not res:
            return self.RES_ERROR, _('Failed in locking cluster.')

        try:
            res, reason = self._execute(**kwargs)
        finally:
            senlin_lock.cluster_lock_release(self.target, self.id,
                                             senlin_lock.CLUSTER_SCOPE)

        return res, reason

    def cancel(self):
        """Handler to cancel the execution of action."""
        return self.RES_OK
