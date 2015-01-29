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
from senlin.common.i18n import _
from senlin.engine.actions import base
from senlin.engine import node as nodem
from senlin.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class NodeAction(base.Action):
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
        try:
            node = nodem.Node.load(self.context, self.target)
        except exception.NotFound:
            LOG.error(_LE('Node with id (%s) is not found'), self.target)
            return res.RES_ERROR

        if node.cluster_id:
            check_result = self.policy_check(node.cluster_id, 'BEFORE')
            if not check_result:
                # Don't emit message here since policy_check should have done it
                return res.RES_ERROR

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

    def cancel(self):
        return self.RES_OK
