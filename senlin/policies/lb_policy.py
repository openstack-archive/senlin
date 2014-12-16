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

from senlin.policies import base


class LoadBalancingPolicy(base.PolicyBase):
    '''
    Policy for load balancing among members of a cluster.

    This policy is expected to be enforced after the member list of a cluster
    is changed. We need to reload the load-balancer specified (or internally
    created) when these actions are performed.
    '''

    TARGET = [
        ('AFTER', 'CLUSTER', 'ADD_MEMBER'),
        ('AFTER', 'CLUSTER', 'DEL_MEMBER'),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
        'aws.autoscaling.launchconfig',
    ]

    def __init__(self, name, type_name, **kwargs):
        super(LoadBalancingPolicy, self).__init__(name, type_name, kwargs)

        self.lb_names = kwargs.get('loadbalancer_names')

    def pre_op(self, cluster_id, action, **args):
        pass

    def enforce(self, cluster_id, action, **args):
        pass

    def post_op(self, cluster_id, action, **args):
        # TODO: reload load-balancer
        # NOTE: lb_names is a list of load-balancer
        return True
