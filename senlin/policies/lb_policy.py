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

from senlin.common import senlin_consts as consts
from senlin.policies import base


class LoadBalancingPolicy(base.Policy):
    '''
    Policy for load balancing among members of a cluster.

    This policy is expected to be enforced after the member list of a cluster
    is changed. We need to reload the load-balancer specified (or internally
    created) when these actions are performed.
    '''

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_SCALE_UP),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_SCALE_DOWN),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
        'aws.autoscaling.launchconfig',
    ]

    def __init__(self, type_name, name, **kwargs):
        super(LoadBalancingPolicy, self).__init__(type_name, name, kwargs)

        self.lb_names = kwargs.get('loadbalancer_names')

    def pre_op(self, cluster_id, action, **args):
        if action not in (consts.CLUSTER_DEL_NODES,
                          consts.CLUSTER_SCALE_DOWN):
            return True

        # TODO(anyone): remove nodes from loadbalancer
        return True

    def enforce(self, cluster_id, action, **args):
        pass

    def post_op(self, cluster_id, action, **args):
        if action not in (consts.CLUSTER_ADD_NODES, consts.CLUSTER_SCALE_UP):
            return True

        # TODO(anyone): add nodes to loadbalancer
        return True
