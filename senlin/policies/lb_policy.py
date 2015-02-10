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

from senlin.common import consts
from senlin.policies import base

neutron = None


class LoadBalancingPolicy(base.Policy):
    '''Policy for load balancing among members of a cluster.

    This policy is expected to be enforced after the member list of a cluster
    is changed. We need to reload the load-balancer specified (or internally
    created) when these actions are performed.
    '''

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
        'aws.autoscaling.launchconfig',
    ]

    def __init__(self, type_name, name, **kwargs):
        super(LoadBalancingPolicy, self).__init__(type_name, name, kwargs)

        self.pool_spec = kwargs.get('pool', None)
        self.vip_spec = kwargs.get('vip', None)
        self.pool = None
        self.vip = None
        self.pool_need_delete = True
        self.vip_need_delete = True

    def attach(self, cluster_id):
        pool_id = self.pool_spec.get('pool')
        if pool_id is not None:
            self.pool = neutron.get_pool(pool_id)
            self.pool_need_delete = False
        else:
            # Create pool using the specified params
            self.pool = neutron.create_pool({'pool': self.pool_spec})['pool']

        vip_id = self.vip_spec.get('vip')
        if vip_id is not None:
            self.vip = neutron.get_vip(vip_id)
            self.vip_need_delete = False
        else:
            # Create vip using specified params
            self.vip = neutron.create_vip({'vip': self.vip_spec})['vip']

        return True

    def detach(self, cluster_id):
        if self.vip_need_delete:
            neutron.delete_vip(self.vip)
        if self.pool_need_delete:
            neutron.delete_pool(self.pool)

        return True

    def pre_op(self, cluster_id, action, policy_data):
        if action not in (consts.CLUSTER_DEL_NODES, consts.CLUSTER_SCALE_IN):
            return True
        nodes = policy_data.get('nodes', [])
        for node in nodes:
            member_id = node.data.get('lb_member')
            neutron.delete_member(member_id)

        return True

    def post_op(self, cluster_id, action, policy_data):
        if action not in (consts.CLUSTER_ADD_NODES, consts.CLUSTER_SCALE_OUT):
            return True

        nodes = policy_data.get('nodes', [])
        for node in nodes:
            params = {
                'pool_id': self.pool,
                'address': node.data.get('ip'),
                'protocol_port': self.protocol_port,
                'admin_state_up': True,
            }
            member = neutron.create_member({'member': params})['member']
            node.data.update('lb_member', member['id'])

        return True
