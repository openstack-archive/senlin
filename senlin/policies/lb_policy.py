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

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import schema
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

    KEYS = (
        PROTOCOL_PORT, POOL, VIP,
    ) = (
        'protocol_port', 'pool', 'vip',
    )

    _POOL_KEYS = (
        POOL_ID, PROTOCOL, POOL_SUBNET, LB_METHOD, ADMIN_STATE_UP,
    ) = (
        'pool_id', 'protocol', 'subnet', 'lb_method', 'admin_state_up',
    )

    PROTOCOLS = (
        HTTP, HTTPS,
    ) = (
        'HTTP', 'HTTPS',
    )

    LB_METHODS = (
        ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP,
    ) = (
        'ROUND_ROBIN', 'LEAST_CONNECTIONS', 'SOURCE_IP',
    )

    _VIP_KEYS = (
        VIP_ID, VIP_SUBNET, ADDRESS, CONNECTION_LIMIT, VIP_PROTOCOL_PORT,
        VIP_ADMIN_STATE_UP, SESSION_PERSISTENCE,
    ) = (
        'vip_id', 'subnet', 'address', 'connection_limit', 'protocol_port',
        'admin_state_up', 'session_persistence',
    )

    _SESSION_PERSISTENCE_KEYS = (
        PERSISTENCE_TYPE, COOKIE_NAME,
    ) = (
        'type', 'cookie_name',
    )

    PERSISTENCE_TYPES = (
        PERSIST_SOURCE_IP, PERSIST_HTTP_COOKIE, PERSIST_APP_COOKIE,
    ) = (
        'SOURCE_IP', 'HTTP_COOKIE', 'APP_COOKIE',
    )

    spec_schema = {
        PROTOCOL_PORT: schema.Integer(
            _('Port on which servers are running on the nodes.'),
            default=80,
        ),
        POOL: schema.Map(
            _('LB pool properties.'),
            schema={
                POOL_ID: schema.String(
                    _('ID of an existing load-balanced pool.'),
                ),
                PROTOCOL: schema.String(
                    _('Protocol used for load balancing.'),
                    constraints=[
                        constraints.AllowedValues(PROTOCOLS),
                    ],
                    default=HTTP,
                ),
                POOL_SUBNET: schema.String(
                    _('Subnet for the port on which nodes can be connected.'),
                    required=True,
                ),
                LB_METHOD: schema.String(
                    _('Load balancing algorithm.'),
                    constraints=[
                        constraints.AllowedValues(LB_METHODS),
                    ],
                    default=ROUND_ROBIN,
                ),
                ADMIN_STATE_UP: schema.Boolean(
                    _('Administrative state of the pool.'),
                    default=True,
                ),
            },
        ),
        VIP: schema.Map(
            _('VIP address and port of the pool.'),
            schema={
                VIP_ID: schema.String(
                    _('ID of an existing VIP object.'),
                ),
                VIP_SUBNET: schema.String(
                    _('Subnet of the VIP address.'),
                ),
                ADDRESS: schema.String(
                    _('IP address of the VIP.'),
                    required=True,
                ),
                CONNECTION_LIMIT: schema.Integer(
                    _('Maximum number of connections per second allowed for '
                      'this VIP'),
                ),
                VIP_PROTOCOL_PORT: schema.Integer(
                    _('TCP port to listen on.'),
                    default=80,
                ),
                VIP_ADMIN_STATE_UP: schema.Boolean(
                    _('Administrative state of the VIP.'),
                    default=True,
                ),
                SESSION_PERSISTENCE: schema.Map(
                    _('Session pesistence configuration.'),
                    schema={
                        PERSISTENCE_TYPE: schema.String(
                            _('Type of session persistence implementation.'),
                            constraints=[
                                constraints.AllowedValues(PERSISTENCE_TYPES),
                            ],
                            default=PERSIST_SOURCE_IP,
                        ),
                        COOKIE_NAME: schema.String(
                            _('Name of cookie if type set to APP_COOKIE.'),
                        ),
                    },
                ),
            },
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(LoadBalancingPolicy, self).__init__(type_name, name, **kwargs)

        self.pool_spec = kwargs.get('pool', None)
        self.vip_spec = kwargs.get('vip', None)
        self.pool = None
        self.vip = None
        self.pool_need_delete = True
        self.vip_need_delete = True

    def attach(self, cluster_id, action):
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

    def detach(self, cluster_id, action):
        if self.vip_need_delete:
            neutron.delete_vip(self.vip)
        if self.pool_need_delete:
            neutron.delete_pool(self.pool)

        return True

    def pre_op(self, cluster_id, action):
        if action not in (consts.CLUSTER_DEL_NODES, consts.CLUSTER_SCALE_IN):
            return
        nodes = action.data.get('nodes', [])
        for node in nodes:
            member_id = node.data.get('lb_member')
            neutron.delete_member(member_id)

        return

    def post_op(self, cluster_id, action):
        if action not in (consts.CLUSTER_ADD_NODES, consts.CLUSTER_SCALE_OUT):
            return

        nodes = action.data.get('nodes', [])
        for node in nodes:
            params = {
                'pool_id': self.pool,
                'address': node.data.get('ip'),
                'protocol_port': self.protocol_port,
                'admin_state_up': True,
            }
            member = neutron.create_member({'member': params})['member']
            node.data.update('lb_member', member['id'])

        return
