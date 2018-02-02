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

import eventlet

from oslo_log import log as logging
from osprofiler import profiler

from senlin.common import consts
from senlin.common import scaleutils as su
from senlin.engine.actions import base
from senlin.engine import cluster as cm
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock
from senlin.objects import action as ao
from senlin.objects import node as no
from senlin.policies import base as pb

LOG = logging.getLogger(__name__)


class NodeAction(base.Action):
    """An action that can be performed on a cluster member (node)."""

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
            self.entity = node_mod.Node.load(self.context, node_id=self.target)
        except Exception:
            self.entity = None

    @profiler.trace('NodeAction.do_create', hide_args=False)
    def do_create(self):
        """Handler for the NODE_CREATE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        cluster_id = self.entity.cluster_id
        if cluster_id and self.cause == consts.CAUSE_RPC:
            # Check cluster size constraint if target cluster is specified
            cluster = cm.Cluster.load(self.context, cluster_id)
            desired = no.Node.count_by_cluster(self.context, cluster_id)
            result = su.check_size_params(cluster, desired, None, None, True)
            if result:
                # cannot place node into the cluster
                no.Node.update(self.context, self.entity.id,
                               {'cluster_id': '', 'status': consts.NS_ERROR})
                return self.RES_ERROR, result

        res = self.entity.do_create(self.context)

        if cluster_id and self.cause == consts.CAUSE_RPC:
            # Update cluster's desired_capacity and re-evaluate its status no
            # matter the creation is a success or not because the node object
            # is already treated as member of the cluster and the node
            # creation may have changed the cluster's status
            cluster.eval_status(self.context, consts.NODE_CREATE,
                                desired_capacity=desired)
        if res:
            return self.RES_OK, 'Node created successfully.'
        else:
            return self.RES_ERROR, 'Node creation failed.'

    @profiler.trace('NodeAction.do_delete', hide_args=False)
    def do_delete(self):
        """Handler for the NODE_DELETE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        cluster_id = self.entity.cluster_id
        if cluster_id and self.cause == consts.CAUSE_RPC:
            # If node belongs to a cluster, check size constraint
            # before deleting it
            cluster = cm.Cluster.load(self.context, cluster_id)
            current = no.Node.count_by_cluster(self.context, cluster_id)
            desired = current - 1
            result = su.check_size_params(cluster, desired, None, None, True)
            if result:
                return self.RES_ERROR, result

            # handle grace_period
            pd = self.data.get('deletion', None)
            if pd:
                grace_period = pd.get('grace_period', 0)
                if grace_period:
                    eventlet.sleep(grace_period)

        res = self.entity.do_delete(self.context)

        if cluster_id and self.cause == consts.CAUSE_RPC:
            # check if desired_capacity should be changed
            do_reduce = True
            params = {}
            pd = self.data.get('deletion', None)
            if pd:
                do_reduce = pd.get('reduce_desired_capacity', True)
            if do_reduce and res:
                params = {'desired_capacity': desired}
            cluster.eval_status(self.context, consts.NODE_DELETE, **params)

        if not res:
            return self.RES_ERROR, 'Node deletion failed.'

        # Remove all action records which target on deleted
        # node except the on-going NODE_DELETE action from DB
        try:
            ao.Action.delete_by_target(
                self.context, self.target,
                action_excluded=[consts.NODE_DELETE],
                status=[consts.ACTION_SUCCEEDED, consts.ACTION_FAILED])
        except Exception as ex:
            LOG.warning('Failed to clean node action records: %s',
                        ex)
        return self.RES_OK, 'Node deleted successfully.'

    @profiler.trace('NodeAction.do_update', hide_args=False)
    def do_update(self):
        """Handler for the NODE_UPDATE action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        params = self.inputs
        new_profile_id = params.get('new_profile_id', None)
        if new_profile_id and new_profile_id == self.entity.profile_id:
            params.pop('new_profile_id')

        if not params:
            return self.RES_OK, 'No property to update.'

        res = self.entity.do_update(self.context, params)
        if res:
            return self.RES_OK, 'Node updated successfully.'
        else:
            return self.RES_ERROR, 'Node update failed.'

    @profiler.trace('NodeAction.do_join', hide_args=False)
    def do_join(self):
        """Handler for the NODE_JOIN action.

        Note that we don't manipulate the cluster's status after this
        operation. This is because a NODE_JOIN is always an internal action,
        i.e. derived from a cluster action. The cluster's status is supposed
        to be checked and set in the outer cluster action rather than here.

        :returns: A tuple containing the result and the corresponding reason.
        """
        cluster_id = self.inputs.get('cluster_id')
        result = self.entity.do_join(self.context, cluster_id)
        if result:
            return self.RES_OK, 'Node successfully joined cluster.'
        else:
            return self.RES_ERROR, 'Node failed in joining cluster.'

    @profiler.trace('NodeAction.do_leave', hide_args=False)
    def do_leave(self):
        """Handler for the NODE_LEAVE action.

        Note that we don't manipulate the cluster's status after this
        operation. This is because a NODE_JOIN is always an internal action,
        i.e. derived from a cluster action. The cluster's status is supposed
        to be checked and set in the outer cluster action rather than here.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.entity.do_leave(self.context)
        if res:
            return self.RES_OK, 'Node successfully left cluster.'
        else:
            return self.RES_ERROR, 'Node failed in leaving cluster.'

    @profiler.trace('NodeAction.do_check', hide_args=False)
    def do_check(self):
        """Handler for the NODE_check action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.entity.do_check(self.context)
        if res:
            return self.RES_OK, 'Node check succeeded.'
        else:
            return self.RES_ERROR, 'Node check failed.'

    @profiler.trace('NodeAction.do_recover', hide_args=False)
    def do_recover(self):
        """Handler for the NODE_RECOVER action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        res = self.entity.do_recover(self.context, self)
        if res:
            return self.RES_OK, 'Node recovered successfully.'
        else:
            return self.RES_ERROR, 'Node recover failed.'

    @profiler.trace('NodeAction.do_operation', hide_args=False)
    def do_operation(self):
        """Handler for the NODE_OPERATION action.

        :returns: A tuple containing the result and the corresponding reason.
        """
        operation = self.inputs['operation']
        res = self.entity.do_operation(self.context, **self.inputs)
        if res:
            return self.RES_OK, "Node operation '%s' succeeded." % operation
        else:
            return self.RES_ERROR, "Node operation '%s' failed." % operation

    def _execute(self):
        """Private function that finds out the handler and execute it."""

        action_name = self.action.lower()
        method_name = action_name.replace('node', 'do')
        method = getattr(self, method_name, None)

        if method is None:
            reason = 'Unsupported action: %s' % self.action
            EVENT.error(self, consts.PHASE_ERROR, reason)
            return self.RES_ERROR, reason

        return method()

    def execute(self, **kwargs):
        """Interface function for action execution.

        :param dict kwargs: Parameters provided to the action, if any.
        :returns: A tuple containing the result and the related reason.
        """
        # Since node.cluster_id could be reset to '' during action execution,
        # we record it here for policy check and cluster lock release.
        saved_cluster_id = self.entity.cluster_id
        if saved_cluster_id:
            if self.cause == consts.CAUSE_RPC:
                res = senlin_lock.cluster_lock_acquire(
                    self.context, self.entity.cluster_id, self.id, self.owner,
                    senlin_lock.NODE_SCOPE, False)

                if not res:
                    return self.RES_RETRY, 'Failed in locking cluster'

                self.policy_check(self.entity.cluster_id, 'BEFORE')
                if self.data['status'] != pb.CHECK_OK:
                    # Don't emit message since policy_check should have done it
                    senlin_lock.cluster_lock_release(saved_cluster_id, self.id,
                                                     senlin_lock.NODE_SCOPE)
                    return self.RES_ERROR, ('Policy check: ' +
                                            self.data['reason'])
            elif self.cause == consts.CAUSE_DERIVED_LCH:
                self.policy_check(self.entity.cluster_id, 'BEFORE')

        reason = ''
        try:
            res = senlin_lock.node_lock_acquire(self.context, self.entity.id,
                                                self.id, self.owner, False)
            if not res:
                res = self.RES_RETRY
                reason = 'Failed in locking node'
            else:
                res, reason = self._execute()
                if (res == self.RES_OK and saved_cluster_id and
                        self.cause == consts.CAUSE_RPC):
                    self.policy_check(saved_cluster_id, 'AFTER')
                    if self.data['status'] != pb.CHECK_OK:
                        res = self.RES_ERROR
                        reason = 'Policy check: ' + self.data['reason']
                    else:
                        res = self.RES_OK
        finally:
            senlin_lock.node_lock_release(self.entity.id, self.id)
            if saved_cluster_id and self.cause == consts.CAUSE_RPC:
                senlin_lock.cluster_lock_release(saved_cluster_id, self.id,
                                                 senlin_lock.NODE_SCOPE)
        return res, reason

    def cancel(self):
        """Handler for cancelling the action."""
        return self.RES_OK
