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

from senlin.common import exception
from senlin.common.i18n import _LE
from senlin.engine.actions import base
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock
from senlin.openstack.common import log as logging
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
            return self.RES_OK, 'Node created successfully'
        else:
            return self.RES_ERROR, 'Node creation failed'

    def do_delete(self, node):
        res = node.do_delete(self.context)
        if res:
            return self.RES_OK, 'Node deleted successfully'
        else:
            return self.RES_ERROR, 'Node deletion failed'

    def do_update(self, node):
        new_profile_id = self.inputs.get('new_profile_id')
        res = node.do_update(self.context, new_profile_id)
        if res:
            return self.RES_OK, 'Node updated successfully'
        else:
            return self.RES_ERROR, 'Node update failed'

    def do_join(self, node):
        cluster_id = self.inputs.get('cluster_id')
        res = node.do_join(self.context, cluster_id)
        if res:
            return self.RES_OK, 'Node successfully joined cluster'
        else:
            return self.RES_ERROR, 'Node failed joining cluster'

    def do_leave(self, node):
        res = node.do_leave(self.context)
        if res:
            return self.RES_OK, 'Node successfully left cluster'
        else:
            return self.RES_ERROR, 'Node failed leaving cluster'

    def _execute(self, node):
        # TODO(Qiming): Add node status changes
        result = self.RES_OK
        action_name = self.action.lower()
        method_name = action_name.replace('node', 'do')
        method = getattr(self, method_name)

        if method is None:
            raise exception.ActionNotSupported(action=self.action)

        result, reason = method(node)
        return result, reason

    def execute(self, **kwargs):
        try:
            node = node_mod.Node.load(self.context, node_id=self.target)
        except exception.NotFound:
            reason = _('Node with id (%s) is not found') % self.target
            LOG.error(_LE(reason))
            return self.RES_ERROR, reason

        reason = ''
        if node.cluster_id:
            if self.cause == base.CAUSE_RPC:
                res = senlin_lock.cluster_lock_acquire(
                    node.cluster_id, self.id, senlin_lock.NODE_SCOPE, False)
                if not res:
                    return self.RES_RETRY, 'Failed locking cluster'

            policy_data = self.policy_check(node.cluster_id, 'BEFORE')
            if policy_data.status != policy_mod.CHECK_OK:
                # Don't emit message here since policy_check should have
                # done it
                if self.cause == base.CAUSE_RPC:
                    senlin_lock.cluster_lock_release(
                        node.cluster_id, self.id, senlin_lock.NODE_SCOPE)

                return self.RES_ERROR, 'Policy check:' + policy_data.reason

        try:
            res = senlin_lock.node_lock_acquire(node.id, self.id, False)
            if not res:
                reason = 'Failed locking node'
            else:
                res, reason = self._execute(node)
                if res == self.RES_OK and node.cluster_id is not None:
                    policy_data = self.policy_check(node.cluster_id, 'AFTER')
                    if policy_data.status != policy_mod.CHECK_OK:
                        res = self.RES_ERROR
                        reason = 'Policy check:' + policy_data.reason
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
