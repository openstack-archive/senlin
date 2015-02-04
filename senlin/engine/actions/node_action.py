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

LOG = logging.getLogger(__name__)


class NodeAction(base.Action):
    '''An action performed on a cluster member.'''

    ACTIONS = (
        NODE_CREATE, NODE_DELETE, NODE_UPDATE,
        NODE_JOIN_CLUSTER, NODE_LEAVE_CLUSTER,
    ) = (
        'NODE_CREATE', 'NODE_DELETE', 'NODE_UPDATE',
        'NODE_JOIN_CLUSTER', 'NODE_LEAVE_CLUSTER',
    )

    def __init__(self, context, action, **kwargs):
        super(NodeAction, self).__init__(context, action, **kwargs)

    def _execute(self, node):
        # TODO(Qiming): Add node status changes
        if self.action == self.NODE_CREATE:
            res = node.do_create(self.context)
        elif self.action == self.NODE_DELETE:
            res = node.do_delete(self.context)
        elif self.action == self.NODE_UPDATE:
            new_profile_id = self.inputs.get('new_profile_id')
            res = node.do_update(self.context, new_profile_id)
        elif self.action == self.NODE_JOIN_CLUSTER:
            new_cluster_id = self.inputs.get('cluster_id', None)
            if not new_cluster_id:
                raise exception.ClusterNotSpecified()
            res = node.do_join(new_cluster_id)
        elif self.action == self.NODE_LEAVE_CLUSTER:
            res = node.do_leave(self.context)

        return self.RES_OK if res else self.RES_ERROR

    def execute(self, **kwargs):
        try:
            node = node_mod.Node.load(self.context, node_id=self.target)
        except exception.NotFound:
            LOG.error(_LE('Node with id (%s) is not found'), self.target)
            return self.RES_ERROR

        if node.cluster_id:
            if self.cause == base.CAUSE_RPC:
                res = senlin_lock.cluster_lock_acquire(
                    node.cluster_id, self.id, senlin_lock.NODE_SCOPE, False)
                if not res:
                    return self.RES_RETRY

            check_result = self.policy_check(node.cluster_id, 'BEFORE')
            if not check_result:
                # Don't emit message here since policy_check should have
                # done it
                if self.cause == base.CAUSE_RPC:
                    senlin_lock.cluster_lock_release(
                        node.cluster_id, self.id, senlin_lock.NODE_SCOPE)

                return self.RES_ERROR

        try:
            res = senlin_lock.node_lock_acquire(node.id, self.id, False)
            if res:
                res = self._execute(node)
            if res == self.RES_OK and node.cluster_id is not None:
                check_result = self.policy_check(node.cluster_id, 'AFTER')
                res = self.RES_OK if check_result else self.ERROR
        finally:
            senlin_lock.node_lock_release(node.id, self.id)
            if node.cluster_id is not None and self.cause == base.CAUSE_RPC:
                senlin_lock.cluster_lock_release(node.cluster_id, self.id,
                                                 senlin_lock.NODE_SCOPE)
        return res

    def cancel(self):
        return self.RES_OK
