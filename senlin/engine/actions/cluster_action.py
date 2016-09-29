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
from oslo_utils import timeutils

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
        CLUSTER_ATTACH_POLICY, CLUSTER_DETACH_POLICY, CLUSTER_UPDATE_POLICY,
        CLUSTER_REPLACE_NODES
    ) = (
        consts.CLUSTER_CREATE, consts.CLUSTER_DELETE, consts.CLUSTER_UPDATE,
        consts.CLUSTER_ADD_NODES, consts.CLUSTER_DEL_NODES,
        consts.CLUSTER_RESIZE, consts.CLUSTER_CHECK, consts.CLUSTER_RECOVER,
        consts.CLUSTER_SCALE_OUT, consts.CLUSTER_SCALE_IN,
        consts.CLUSTER_ATTACH_POLICY, consts.CLUSTER_DETACH_POLICY,
        consts.CLUSTER_UPDATE_POLICY, consts.CLUSTER_REPLACE_NODES
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

    def _sleep(self, period):
        if period:
            eventlet.sleep(period)

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

        params = {}
        if result == self.RES_OK:
            reason = _('Cluster creation succeeded.')
            params = {'created_at': timeutils.utcnow(True)}
        self.cluster.eval_status(self.context, self.CLUSTER_CREATE, **params)

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
            self.cluster.eval_status(self.context, self.CLUSTER_UPDATE,
                                     updated_at=timeutils.utcnow(True))
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
                self.cluster.eval_status(self.context, self.CLUSTER_UPDATE)
                return result, _('Failed in updating nodes.')

        self.cluster.profile_id = profile_id
        self.cluster.eval_status(self.context, self.CLUSTER_UPDATE,
                                 profile_id=profile_id,
                                 updated_at=timeutils.utcnow(True))
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
                self.cluster.eval_status(self.context, self.CLUSTER_DELETE)
                return self.RES_ERROR, _('Cannot delete cluster object.')
        else:
            self.cluster.eval_status(self.context, self.CLUSTER_DELETE)

        return result, reason

    def do_add_nodes(self):
        """Handler for the CLUSTER_ADD_NODES action.

        TODO(anyone): handle placement data

        :returns: A tuple containing the result and the corresponding reason.
        """
        node_ids = self.inputs.get('nodes')
        errors = []
        nodes = []
        for nid in node_ids:
            node = no.Node.get(self.context, nid)
            if not node:
                errors.append(_('Node %s is not found.') % nid)
                continue

            if node.cluster_id:
                errors.append(_('Node %(n)s is already owned by cluster %(c)s.'
                                ) % {'n': nid, 'c': node.cluster_id})
                continue

            if node.status != "ACTIVE":
                errors.append(_('Node %s is not in ACTIVE status.') % nid)
                continue

            nodes.append(node)

        if len(errors) > 0:
            return self.RES_ERROR, '\n'.join(errors)

        reason = _('Completed adding nodes.')
        current = no.Node.count_by_cluster(self.context, self.target)
        child = []
        for node in nodes:
            nid = node.id
            kwargs = {
                'name': 'node_join_%s' % nid[:8],
                'cause': base.CAUSE_DERIVED,
                'inputs': {'cluster_id': self.target},
            }
            action_id = base.Action.create(self.context, nid, consts.NODE_JOIN,
                                           **kwargs)
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
            desired = current + len(node_ids)
            self.cluster.eval_status(self.context, self.CLUSTER_ADD_NODES,
                                     desired_capacity=desired)
            self.outputs['nodes_added'] = node_ids
            creation = self.data.get('creation', {})
            creation['nodes'] = node_ids
            self.data['creation'] = creation
            for node in nodes:
                obj = node_mod.Node.load(self.context, db_node=node)
                self.cluster.add_node(obj)

        return result, reason

    def do_del_nodes(self):
        """Handler for the CLUSTER_DEL_NODES action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # Use policy decision if any, or fall back to defaults
        destroy_after_deletion = False
        grace_period = 0
        reduce_desired_capacity = True
        pd = self.data.get('deletion', None)
        if pd:
            destroy_after_deletion = pd.get('destroy_after_deletion', False)
            grace_period = pd.get('grace_period', 0)
            reduce_desired_capacity = pd.get('reduce_desired_capacity', True)

        data = {
            'deletion': {
                'destroy_after_deletion': destroy_after_deletion,
                'grace_period': grace_period,
                'reduce_desired_capacity': reduce_desired_capacity,
            }
        }
        self.data.update(data)
        nodes = self.inputs.get('candidates', [])

        node_ids = copy.deepcopy(nodes)
        errors = []
        for node_id in node_ids:
            node = no.Node.get(self.context, node_id)

            # The return value is None if node not found
            if not node:
                errors.append(_('Node %s is not found.') % node_id)
                continue

            if ((not node.cluster_id) or (node.cluster_id != self.target)):
                nodes.remove(node_id)

        if len(errors) > 0:
            return self.RES_ERROR, ''.join(errors)

        reason = _('Completed deleting nodes.')
        if len(nodes) == 0:
            return self.RES_OK, reason

        # sleep period
        self._sleep(grace_period)

        current = no.Node.count_by_cluster(self.context, self.target)
        result, new_reason = self._delete_nodes(nodes)

        params = {}
        if result != self.RES_OK:
            reason = new_reason
        if reduce_desired_capacity:
            params['desired_capacity'] = current - len(nodes)

        self.cluster.eval_status(self.context,
                                 self.CLUSTER_DEL_NODES, **params)

        return result, reason

    def do_replace_nodes(self):
        """Handler for the CLUSTER_REPLACE_NODES action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        node_dict = self.inputs

        errors = []
        original_nodes = []
        replacement_nodes = []
        for (original, replacement) in node_dict.items():
            original_node = no.Node.get(self.context, original)
            replacement_node = no.Node.get(self.context, replacement)

            # The return value is None if node not found
            if not original_node:
                errors.append(_('Original node %s not found.'
                                ) % original)
                continue
            if not replacement_node:
                errors.append(_('Replacement node %s not found.'
                                ) % replacement)
                continue
            if original_node.cluster_id != self.target:
                errors.append(_('Node %(o)s is not a member of the '
                                'cluster %(c)s.') % {'o': original,
                                                     'c': self.target})
                continue
            if replacement_node.cluster_id:
                errors.append(_('Node %(r)s is already owned by cluster %(c)s.'
                                ) % {'r': replacement,
                                     'c': replacement_node.cluster_id})
                continue
            if replacement_node.status != node_mod.Node.ACTIVE:
                errors.append(_('Node %s is not in ACTIVE status.'
                                ) % replacement)
                continue
            original_nodes.append(original_node)
            replacement_nodes.append(replacement_node)

        if len(errors) > 0:
            return self.RES_ERROR, '\n'.join(errors)

        result = self.RES_OK
        reason = _('Completed replacing nodes.')

        children = []
        for (original, replacement) in node_dict.items():
            kwargs = {
                'cause': base.CAUSE_DERIVED,
            }

            # node_leave action
            kwargs['name'] = 'node_leave_%s' % original[:8]
            leave_action_id = base.Action.create(self.context, original,
                                                 consts.NODE_LEAVE, **kwargs)
            # node_join action
            kwargs['name'] = 'node_join_%s' % replacement[:8]
            kwargs['inputs'] = {'cluster_id': self.target}
            join_action_id = base.Action.create(self.context, replacement,
                                                consts.NODE_JOIN, **kwargs)

            children.append((join_action_id, leave_action_id))

        if children:
            dobj.Dependency.create(self.context, [c[0] for c in children],
                                   self.id)
            for child in children:
                join_id = child[0]
                leave_id = child[1]
                ao.Action.update(self.context, join_id,
                                 {'status': base.Action.READY})

                dobj.Dependency.create(self.context, [join_id], leave_id)
                ao.Action.update(self.context, leave_id,
                                 {'status': base.Action.READY})

                dispatcher.start_action()

            result, new_reason = self._wait_for_dependents()
            if result != self.RES_OK:
                reason = new_reason
            else:
                for n in range(len(original_nodes)):
                    self.cluster.remove_node(original_nodes[n])
                    self.cluster.add_node(replacement_nodes[n])

        self.cluster.eval_status(self.context, self.CLUSTER_REPLACE_NODES)
        return result, reason

    def do_check(self):
        """Handler for CLUSTER_CHECK action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        self.cluster.do_check(self.context)

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

        self.cluster.eval_status(self.context, self.CLUSTER_CHECK)
        return res, reason

    def do_recover(self):
        """Handler for the CLUSTER_RECOVER action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        self.cluster.do_recover(self.context)

        # process data from health_policy
        pd = self.data.get('health', None)
        inputs = {}
        if pd:
            recover_action = pd.get('recover_action', None)
            fencing = pd.get('fencing', None)
            if recover_action is not None:
                inputs['operation'] = recover_action
            if fencing is not None and 'COMPUTE' in fencing:
                inputs['force'] = True

        children = []
        for node in self.cluster.nodes:
            if node.status == 'ACTIVE':
                continue
            node_id = node.id
            action_id = base.Action.create(
                self.context, node_id, consts.NODE_RECOVER,
                name='node_recover_%s' % node_id[:8],
                cause=base.CAUSE_DERIVED, inputs=inputs,
            )
            children.append(action_id)

        res = self.RES_OK
        reason = _('Cluster recovery succeeded.')
        if children:
            dobj.Dependency.create(self.context, [c for c in children],
                                   self.id)
            for cid in children:
                ao.Action.update(self.context, cid, {'status': 'READY'})
            dispatcher.start_action()

            # Wait for dependent action if any
            res, new_reason = self._wait_for_dependents()
            if res != self.RES_OK:
                reason = new_reason

        self.cluster.eval_status(self.context, self.CLUSTER_RECOVER)
        return res, reason

    def _update_cluster_size(self, desired):
        """Private function for updating cluster properties."""
        kwargs = {'desired_capacity': desired}
        min_size = self.inputs.get(consts.ADJUSTMENT_MIN_SIZE, None)
        max_size = self.inputs.get(consts.ADJUSTMENT_MAX_SIZE, None)
        if min_size is not None:
            kwargs['min_size'] = min_size
        if max_size is not None:
            kwargs['max_size'] = max_size
        self.cluster.set_status(self.context, self.cluster.RESIZING,
                                _('Cluster resize started.'), **kwargs)

    def do_resize(self):
        """Handler for the CLUSTER_RESIZE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # if no policy decision(s) found, use policy inputs directly,
        # Note the 'parse_resize_params' function is capable of calculating
        # desired capacity and handling best effort scaling. It also verifies
        # that the inputs are valid
        curr_capacity = no.Node.count_by_cluster(self.context, self.cluster.id)
        if 'creation' not in self.data and 'deletion' not in self.data:
            result, reason = scaleutils.parse_resize_params(self, self.cluster,
                                                            curr_capacity)
            if result != self.RES_OK:
                return result, reason

        # action input consolidated to action data now
        reason = _('Cluster resize succeeded.')
        if 'deletion' in self.data:
            count = self.data['deletion']['count']
            candidates = self.data['deletion'].get('candidates', [])

            # Choose victims randomly if not already picked
            if not candidates:
                node_list = self.cluster.nodes
                candidates = scaleutils.nodes_by_random(node_list, count)

            self._update_cluster_size(curr_capacity - count)

            grace_period = self.data['deletion'].get('grace_period', 0)
            self._sleep(grace_period)
            result, new_reason = self._delete_nodes(candidates)
        else:
            # 'creation' in self.data:
            count = self.data['creation']['count']
            self._update_cluster_size(curr_capacity + count)
            result, new_reason = self._create_nodes(count)

        if result != self.RES_OK:
            reason = new_reason

        self.cluster.eval_status(self.context, self.CLUSTER_RESIZE)
        return result, reason

    def do_scale_out(self):
        """Handler for the CLUSTER_SCALE_OUT action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # We use policy output if any, or else the count is
        # set to 1 as default.
        pd = self.data.get('creation', None)
        if pd is not None:
            count = pd.get('count', 1)
        else:
            # If no scaling policy is attached, use the input count directly
            count = self.inputs.get('count', 1)
            try:
                count = utils.parse_int_param('count', count, allow_zero=False)
            except exception.InvalidParameter:
                reason = _('Invalid count (%s) for scaling out.') % count
                return self.RES_ERROR, reason

        # check provided params against current properties
        # desired is checked when strict is True
        curr_size = no.Node.count_by_cluster(self.context, self.target)
        new_size = curr_size + count
        result = scaleutils.check_size_params(self.cluster, new_size,
                                              None, None, True)
        if result:
            return self.RES_ERROR, result

        self.cluster.set_status(self.context, self.cluster.RESIZING,
                                _('Cluster scale out started.'),
                                desired_capacity=new_size)

        result, reason = self._create_nodes(count)
        if result == self.RES_OK:
            reason = _('Cluster scaling succeeded.')
        self.cluster.eval_status(self.context, self.CLUSTER_SCALE_OUT)

        return result, reason

    def do_scale_in(self):
        """Handler for the CLUSTER_SCALE_IN action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # We use policy data if any, deletion policy and scaling policy might
        # be attached.
        pd = self.data.get('deletion', None)
        grace_period = 0
        if pd:
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
                return self.RES_ERROR, reason

        # check provided params against current properties
        # desired is checked when strict is True
        curr_size = no.Node.count_by_cluster(self.context, self.target)
        if count > curr_size:
            msg = _("Triming count (%(count)s) to current "
                    "cluster size (%(curr)s) for scaling in")
            LOG.warning(msg, {'count': count, 'curr': curr_size})
            count = curr_size
        new_size = curr_size - count

        result = scaleutils.check_size_params(self.cluster, new_size,
                                              None, None, True)
        if result:
            return self.RES_ERROR, result

        self.cluster.set_status(self.context, self.cluster.RESIZING,
                                _('Cluster scale in started.'),
                                desired_capacity=new_size)

        # Choose victims randomly
        if len(candidates) == 0:
            candidates = scaleutils.nodes_by_random(self.cluster.nodes, count)

        #
        self._sleep(grace_period)

        result, reason = self._delete_nodes(candidates)

        if result == self.RES_OK:
            reason = _('Cluster scaling succeeded.')

        self.cluster.eval_status(self.context, self.CLUSTER_SCALE_IN)

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
