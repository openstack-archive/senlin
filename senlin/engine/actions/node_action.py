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

from senlin.common.i18n import _
from senlin.common import scaleutils
from senlin.engine.actions import base
from senlin.engine import cluster as cluster_mod
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock
from senlin.policies import base as policy_mod


class NodeAction(base.Action):
    """An action that can be performed on a cluster member (node)."""

    ACTIONS = (
        NODE_CREATE, NODE_DELETE, NODE_UPDATE,
        NODE_JOIN, NODE_LEAVE,
        NODE_CHECK, NODE_RECOVER
    ) = (
        'NODE_CREATE', 'NODE_DELETE', 'NODE_UPDATE',
        'NODE_JOIN', 'NODE_LEAVE',
        'NODE_CHECK', 'NODE_RECOVER'
    )

    def __init__(self, target, action, context, **kwargs):
        """Constructor for a node action object.

        :param target: ID of the target node object on which the action is to
                       be executed.
        :param action: The name of the action to be executed.
        :param context: The context used for accessing the DB layer.
        :param dict kwargs: Additional parameters that can be passed to the
                            action.
        """
        super(NodeAction, self).__init__(target, action, context, **kwargs)

        try:
            self.node = node_mod.Node.load(self.context, node_id=self.target)
        except Exception:
            self.node = None

    def do_create(self):
        """Handler for the NODE_CREATE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        if self.node.cluster_id and self.cause == base.CAUSE_RPC:
            # If node is created with target cluster specified,
            # check cluster size constraint
            cluster = cluster_mod.Cluster.load(self.context,
                                               self.node.cluster_id)
            result = scaleutils.check_size_params(
                cluster, cluster.desired_capacity + 1, None, None, True)

            if result:
                return self.RES_ERROR, result

        res = self.node.do_create(self.context)
        if res:
            if self.node.cluster_id and self.cause == base.CAUSE_RPC:
                # Update cluster desired_capacity if node creation succeeded
                cluster.desired_capacity += 1
                cluster.store(self.context)
                cluster.add_node(self.node)
            return self.RES_OK, _('Node created successfully.')
        else:
            return self.RES_ERROR, _('Node creation failed.')

    def do_check(self):
        """Handler for the NODE_check action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.node.do_check(self.context)
        if res:
            return self.RES_OK, _('Node status is ACTIVE.')
        else:
            return self.RES_ERROR, _('Node status is not ACTIVE.')

    def do_delete(self):
        """Handler for the NODE_DELETE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        if self.node.cluster_id and self.cause == base.CAUSE_RPC:
            # If node belongs to a cluster, check size constraint
            # before deleting it
            cluster = cluster_mod.Cluster.load(self.context,
                                               self.node.cluster_id)
            result = scaleutils.check_size_params(cluster,
                                                  cluster.desired_capacity - 1,
                                                  None, None, True)
            if result:
                return self.RES_ERROR, result

        res = self.node.do_delete(self.context)
        if res:
            if self.node.cluster_id and self.cause == base.CAUSE_RPC:
                # Update cluster desired_capacity if node deletion succeeded
                cluster.desired_capacity -= 1
                cluster.store(self.context)
                cluster.remove_node(self.node.id)
            return self.RES_OK, _('Node deleted successfully.')
        else:
            return self.RES_ERROR, _('Node deletion failed.')

    def do_update(self):
        """Handler for the NODE_UPDATE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        params = self.inputs
        res = self.node.do_update(self.context, params)
        if res:
            return self.RES_OK, _('Node updated successfully.')
        else:
            return self.RES_ERROR, _('Node update failed.')

    def do_join(self):
        """Handler for the NODE_JOIN action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        cluster_id = self.inputs.get('cluster_id')
        # Check the size constraint of parent cluster
        cluster = cluster_mod.Cluster.load(self.context, cluster_id)
        new_capacity = cluster.desired_capacity + 1
        result = scaleutils.check_size_params(cluster, new_capacity,
                                              None, None, True)
        if result:
            return self.RES_ERROR, result

        result = self.node.do_join(self.context, cluster_id)
        if result:
            cluster.add_node(self.node)
            return self.RES_OK, _('Node successfully joined cluster.')
        else:
            return self.RES_ERROR, _('Node failed in joining cluster.')

    def do_leave(self):
        """Handler for the NODE_LEAVE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        # Check the size constraint of parent cluster
        cluster = cluster_mod.Cluster.load(self.context,
                                           self.node.cluster_id)
        new_capacity = cluster.desired_capacity - 1
        result = scaleutils.check_size_params(cluster, new_capacity,
                                              None, None, True)
        if result:
            return self.RES_ERROR, result

        res = self.node.do_leave(self.context)
        if res:
            cluster.remove_node(self.node.id)
            return self.RES_OK, _('Node successfully left cluster.')
        else:
            return self.RES_ERROR, _('Node failed in leaving cluster.')

    def do_recover(self):
        """Handler for the NODE_RECOVER action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.node.do_recover(self.context, **self.inputs)
        if res:
            return self.RES_OK, _('Node recovered successfully.')
        else:
            return self.RES_ERROR, _('Node recover failed.')

    def _execute(self):
        """Private function that finds out the handler and execute it."""

        action_name = self.action.lower()
        method_name = action_name.replace('node', 'do')
        method = getattr(self, method_name, None)

        if method is None:
            reason = _('Unsupported action: %s') % self.action
            EVENT.error(self.context, self.node, self.action, 'Failed', reason)
            return self.RES_ERROR, reason

        return method()

    def execute(self, **kwargs):
        """Interface function for action execution.

        :param dict kwargs: Parameters provided to the action, if any.
        :returns: A tuple containing the result and the related reason.
        """
        # Since node.cluster_id could be reset to None in _execute progress,
        # we record it here for policy check and cluster lock release.
        saved_cluster_id = self.node.cluster_id
        if self.node.cluster_id:
            if self.cause == base.CAUSE_RPC:
                res = senlin_lock.cluster_lock_acquire(
                    self.context,
                    self.node.cluster_id, self.id, self.owner,
                    senlin_lock.NODE_SCOPE, False)
                if not res:
                    return self.RES_RETRY, _('Failed in locking cluster')

            self.policy_check(self.node.cluster_id, 'BEFORE')
            if self.data['status'] != policy_mod.CHECK_OK:
                # Don't emit message here since policy_check should have
                # done it
                if self.cause == base.CAUSE_RPC:
                    senlin_lock.cluster_lock_release(
                        self.node.cluster_id, self.id, senlin_lock.NODE_SCOPE)

                return self.RES_ERROR, 'Policy check: ' + self.data['reason']

        reason = ''
        try:
            res = senlin_lock.node_lock_acquire(self.context, self.node.id,
                                                self.id, self.owner, False)
            if not res:
                res = self.RES_ERROR
                reason = _('Failed in locking node')
            else:
                res, reason = self._execute()
                if res == self.RES_OK and saved_cluster_id is not None:
                    self.policy_check(saved_cluster_id, 'AFTER')
                    if self.data['status'] != policy_mod.CHECK_OK:
                        res = self.RES_ERROR
                        reason = 'Policy check: ' + self.data['reason']
                    else:
                        res = self.RES_OK
        finally:
            senlin_lock.node_lock_release(self.node.id, self.id)
            if saved_cluster_id is not None and self.cause == base.CAUSE_RPC:
                senlin_lock.cluster_lock_release(saved_cluster_id, self.id,
                                                 senlin_lock.NODE_SCOPE)
        return res, reason

    def cancel(self):
        """Handler for cancelling the action."""
        return self.RES_OK
