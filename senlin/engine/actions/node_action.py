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

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import scaleutils
from senlin.engine.actions import base
from senlin.engine import cluster as cluster_mod
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock
from senlin.policies import base as policy_mod

LOG = logging.getLogger(__name__)


class NodeAction(base.Action):
    '''An action performed on a cluster member.'''

    ACTIONS = (
        NODE_CREATE, NODE_DELETE, NODE_UPDATE,
        NODE_JOIN, NODE_LEAVE,
    ) = (
        'NODE_CREATE', 'NODE_DELETE', 'NODE_UPDATE',
        'NODE_JOIN', 'NODE_LEAVE',
    )

    def do_create(self, node):
        res = node.do_create(self.context)
        if res:
            return self.RES_OK, _('Node created successfully')
        else:
            return self.RES_ERROR, _('Node creation failed')

    def do_delete(self, node):
        res = node.do_delete(self.context)
        if res:
            return self.RES_OK, _('Node deleted successfully')
        else:
            return self.RES_ERROR, _('Node deletion failed')

    def do_update(self, node):
        params = self.inputs
        res = node.do_update(self.context, params)
        if res:
            return self.RES_OK, _('Node updated successfully')
        else:
            return self.RES_ERROR, _('Node update failed')

    def do_join(self, node):
        cluster_id = self.inputs.get('cluster_id')
        # Check the size constraint of parent cluster
        cluster = cluster_mod.Cluster.load(self.context, cluster_id)
        desired_capacity = cluster.desired_capacity + 1
        result = scaleutils.check_size_params(cluster, desired_capacity,
                                              None, None, True)
        if result != '':
            return self.RES_ERROR, result

        result = node.do_join(self.context, cluster_id)
        if result:
            # Update cluster desired_capacity if node join succeeded
            cluster.desired_capacity = desired_capacity
            cluster.store(self.context)
            return self.RES_OK, _('Node successfully joined cluster')
        else:
            return self.RES_ERROR, _('Node failed in joining cluster')

    def do_leave(self, node):
        # Check the size constraint of parent cluster
        cluster = cluster_mod.Cluster.load(self.context, node.cluster_id)
        desired_capacity = cluster.desired_capacity - 1
        result = scaleutils.check_size_params(cluster, desired_capacity,
                                              None, None, True)
        if result != '':
            return self.RES_ERROR, result

        res = node.do_leave(self.context)
        if res:
            # Update cluster desired_capacity if node leave succeeded
            cluster.desired_capacity = desired_capacity
            cluster.store(self.context)
            return self.RES_OK, _('Node successfully left cluster')
        else:
            return self.RES_ERROR, _('Node failed in leaving cluster')

    def _execute(self, node):
        action_name = self.action.lower()
        method_name = action_name.replace('node', 'do')
        method = getattr(self, method_name, None)

        if method is None:
            reason = _('Unsupported action: %s') % self.action
            EVENT.error(self.context, node, self.action, 'Failed', reason)
            return self.RES_ERROR, reason

        return method(node)

    def execute(self, **kwargs):
        try:
            node = node_mod.Node.load(self.context, node_id=self.target)
        except exception.NodeNotFound:
            reason = _('Node with id (%s) is not found') % self.target
            EVENT.error(self.context, None, self.action, 'Failed',
                        reason)
            return self.RES_ERROR, reason

        if node.cluster_id:
            if self.cause == base.CAUSE_RPC:
                res = senlin_lock.cluster_lock_acquire(
                    node.cluster_id, self.id, senlin_lock.NODE_SCOPE, False)
                if not res:
                    return self.RES_RETRY, _('Failed in locking cluster')

            self.policy_check(node.cluster_id, 'BEFORE')
            if self.data['status'] != policy_mod.CHECK_OK:
                # Don't emit message here since policy_check should have
                # done it
                if self.cause == base.CAUSE_RPC:
                    senlin_lock.cluster_lock_release(
                        node.cluster_id, self.id, senlin_lock.NODE_SCOPE)

                return self.RES_ERROR, 'Policy check: ' + self.data['reason']

        reason = ''
        try:
            res = senlin_lock.node_lock_acquire(node.id, self.id, False)
            if not res:
                res = self.RES_ERROR
                reason = _('Failed in locking node')
            else:
                res, reason = self._execute(node)
                if res == self.RES_OK and node.cluster_id is not None:
                    self.policy_check(node.cluster_id, 'AFTER')
                    if self.data['status'] != policy_mod.CHECK_OK:
                        res = self.RES_ERROR
                        reason = 'Policy check: ' + self.data['reason']
                    else:
                        res = self.RES_OK
        finally:
            senlin_lock.node_lock_release(node.id, self.id)
            if node.cluster_id is not None and self.cause == base.CAUSE_RPC:
                senlin_lock.cluster_lock_release(node.cluster_id, self.id,
                                                 senlin_lock.NODE_SCOPE)
        return res, reason

    def cancel(self):
        return self.RES_OK
