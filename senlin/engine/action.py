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

from oslo.config import cfg


class Action(object):
    '''
    An action can be performed on a cluster or a node of a cluster.
    '''
    RETURNS = (
        OK, FAILED, RETRY,
    ) = (
        'OK', 'FAILED', 'RETRY',
    )

    def __init__(self, context):
        self.context = context
        # the context should contain a request ID
        self.request_id = context['request_id']

        # TODO: make action timeout configurable
        # heat.common.default_action_timeout
        self.timeout = cfg.CONF.default_action_timeout

    def execute(self, **kwargs):
        return NotImplemented

    def cancel(self):
        return NotImplemented


class ClusterAction(Action):
    '''
    An action performed on a cluster.
    '''
    ACTIONS = (
        CREATE, DELETE, ADD_MEMBER, DEL_MEMBER, UPDATE,
        ATTACH_POLICY, DETACH_POLICY,
    ) = (
        'CREATE', 'DELETE', 'ADD_MEMBER', 'DEL_MEMBER', 'UPDATE',
        'ATTACH_POLICY', 'DETACH_POLICY',
    )

    def __init__(self, context, cluster):
        super(ClusterAction, self).__init__(context)

    def execute(self, action, **kwargs):
        if action not in self.ACTIONS:
            return self.FAILED 

        if action == self.CREATE:
            cluster.do_create(kwargs)
        else:
            return self.FAILED

        return self.OK 

    def cancel(self):
        return self.FAILED 


class NodeAction(Action):
    '''
    An action performed on a cluster member.
    '''
    ACTIONS = (
        CREATE, DELETE, UPDATE, JOIN, LEAVE,
    ) = (
        'CREATE', 'DELETE', 'UPDATE', 'JOIN', 'LEAVE',
    )

    def __init__(self, context, node_id):
        super(NodeAction, self).__init__(context)

        # get cluster of this node 
        # get policies associated with the cluster

    def execute(self, action):
        if action not in self.ACTIONS:
            return self.FAILED 
        return self.OK 

    def cancel(self):
        return self.OK 


class PolicyAction(Action):
    '''
    An action performed on a cluster policy.
    '''

    ACTIONS = (
        ENABLE, DISABLE, UPDATE,
    ) = (
        'ENABLE', 'DISABLE', 'UPDATE',
    )

    def __init__(self, context, cluster_id, policy_id):
        super(PolicyAction, self).__init__(context)
        # get policy associaton using the cluster id and policy id

    def execute(self, action, **kwargs):
        if action not in self.ACTIONS:
            return self.FAILED 
        return self.OK 

    def cancel(self):
        return self.OK 
