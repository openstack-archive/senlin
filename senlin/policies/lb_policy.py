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

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import schema
from senlin.drivers.openstack import lbaas
from senlin.engine import cluster_policy
from senlin.engine import node as node_mod
from senlin.policies import base

LOG = logging.getLogger(__name__)


class LoadBalancingPolicy(base.Policy):
    '''Policy for load balancing among members of a cluster.

    This policy is expected to be enforced after the member list of a cluster
    is changed. We need to reload the load-balancer specified (or internally
    created) when these actions are performed.
    '''

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_DEL_NODES),
        ('AFTER', consts.CLUSTER_SCALE_OUT),
        ('AFTER', consts.CLUSTER_SCALE_IN),
        ('AFTER', consts.CLUSTER_RESIZE),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
    ]

    KEYS = (
        POOL, VIP,
    ) = (
        'pool', 'vip',
    )

    _POOL_KEYS = (
        POOL_ID, POOL_PROTOCOL, POOL_PROTOCOL_PORT, POOL_SUBNET,
        POOL_LB_METHOD, POOL_ADMIN_STATE_UP, POOL_SESSION_PERSISTENCE,
    ) = (
        'id', 'protocol', 'protocol_port', 'subnet',
        'lb_method', 'admin_state_up', 'session_persistence',
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
        VIP_ID, VIP_SUBNET, VIP_ADDRESS, VIP_CONNECTION_LIMIT, VIP_PROTOCOL,
        VIP_PROTOCOL_PORT, VIP_ADMIN_STATE_UP,
    ) = (
        'id', 'subnet', 'address', 'connection_limit', 'protocol',
        'protocol_port', 'admin_state_up',
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
        POOL: schema.Map(
            _('LB pool properties.'),
            schema={
                POOL_ID: schema.String(
                    _('ID of an existing load-balanced pool.'),
                ),
                POOL_PROTOCOL: schema.String(
                    _('Protocol used for load balancing.'),
                    constraints=[
                        constraints.AllowedValues(PROTOCOLS),
                    ],
                    default=HTTP,
                ),
                POOL_PROTOCOL_PORT: schema.Integer(
                    _('Port on which servers are running on the nodes.'),
                    default=80,
                ),
                POOL_SUBNET: schema.String(
                    _('Name or ID of subnet for the port on which nodes can '
                      'be connected.'),
                    required=True,
                ),
                POOL_LB_METHOD: schema.String(
                    _('Load balancing algorithm.'),
                    constraints=[
                        constraints.AllowedValues(LB_METHODS),
                    ],
                    default=ROUND_ROBIN,
                ),
                POOL_ADMIN_STATE_UP: schema.Boolean(
                    _('Administrative state of the pool.'),
                    default=True,
                ),
                POOL_SESSION_PERSISTENCE: schema.Map(
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
        VIP: schema.Map(
            _('VIP address and port of the pool.'),
            schema={
                VIP_ID: schema.String(
                    _('ID of an existing VIP object.'),
                ),
                VIP_SUBNET: schema.String(
                    _('Name or ID of Subnet on which the VIP address will be '
                      'allocated.'),
                    required=True,
                ),
                VIP_ADDRESS: schema.String(
                    _('IP address of the VIP.'),
                ),
                VIP_CONNECTION_LIMIT: schema.Integer(
                    _('Maximum number of connections per second allowed for '
                      'this VIP'),
                ),
                VIP_PROTOCOL: schema.String(
                    _('Protocol used for VIP.'),
                    constraints=[
                        constraints.AllowedValues(PROTOCOLS),
                    ],
                    default=HTTP,
                ),
                VIP_PROTOCOL_PORT: schema.Integer(
                    _('TCP port to listen on.'),
                    default=80,
                ),
                VIP_ADMIN_STATE_UP: schema.Boolean(
                    _('Administrative state of the VIP.'),
                    default=True,
                ),
            },
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(LoadBalancingPolicy, self).__init__(type_name, name, **kwargs)
        self.pool_spec = self.spec_data.get(self.POOL, None)
        self.vip_spec = self.spec_data.get(self.VIP, None)
        self.validate()
        self.lb = None

    def attach(self, cluster_id, action):
        self.action = action
        pool_id = self.pool_spec.get(self.POOL_ID, None)
        if pool_id is not None:
            data = {
                'pool': self.pool_id,
                'pool_need_delete': False
            }
        else:
            res, data = self.lb_driver.lb_create(self.vip_spec,
                                                 self.pool_spec)
            if res is not True:
                return res, data
            else:
                data['pool_need_delete'] = True

        port = self.pool_spec.get(self.POOL_PROTOCOL_PORT)
        subnet = self.pool_spec.get(self.POOL_SUBNET)
        nodes = node_mod.Node.load_all(action.context, cluster_id=cluster_id)

        for node in nodes:
            params = {
                'pool_id': data['pool'],
                'node': node,
                'port': port,
                'subnet': subnet
            }
            member_id = self.lb_driver.member_add(**params)
            if member_id is None:
                # Adding member failed, remove all lb resources that
                # have been created and return failure reason.
                # TODO(Yanyan Hu): Maybe we should tolerate member adding
                # failure and allow policy attaching to succeed without
                # all nodes being added into lb pool?
                self.lb_driver.lb_delete(**data)
                return False, 'Failed in adding existed node into lb pool'
            else:
                node.data.update({'lb_member': member_id})
                node.store(action.context)

        return True, data

    def detach(self, cluster_id, action):
        res = True
        self.action = action
        cp = cluster_policy.ClusterPolicy.load(action.context, cluster_id,
                                               self.id)

        if cp.data['pool_need_delete']:
            res, reason = self.lb_driver.lb_delete(**cp.data)

        if res is not True:
            return res, reason
        else:
            return res, 'lb resources deleting succeeded'

    def post_op(self, cluster_id, action):
        """Add new created node(s) to lb pool"""

        self.action = action
        cp = cluster_policy.ClusterPolicy.load(action.context, cluster_id,
                                               self.id)
        pool_id = cp.data['pool']
        port = self.pool_spec.get(self.POOL_PROTOCOL_PORT)
        subnet = self.pool_spec.get(self.POOL_SUBNET)

        nodes = action.data.get('nodes')
        if nodes is None:
            return

        for node_id in nodes:
            node = node_mod.Node.load(action.context, node_id=node_id,
                                      show_deleted=True)
            member_id = node.data.get('lb_member')
            if (action.action in (consts.CLUSTER_DEL_NODES,
                                  consts.CLUSTER_SCALE_IN))\
                    or (action.action == consts.CLUSTER_RESIZE and
                        action.data.get('deletion')):
                if member_id:
                    # Remove nodes that have been deleted from lb pool
                    params = {
                        'pool_id': pool_id,
                        'member_id': member_id,
                    }
                    res = self.lb_driver.member_remove(**params)
                    if res is not True:
                        action.data['status'] = base.CHECK_ERROR
                        action.data['reason'] = _('Failed in removing deleted '
                                                  'node from lb pool')
                        return
                else:
                    msg = _('Node %(node)s is not in loadbalancer pool '
                            '%(pool)s when being deleted from cluster '
                            '%(cluster)s.') % {'node': node_id,
                                               'pool': pool_id,
                                               'cluster': node.cluster_id}
                    LOG.warning(msg)

            if (action.action in (consts.CLUSTER_ADD_NODES,
                                  consts.CLUSTER_SCALE_OUT))\
                    or (action.action == consts.CLUSTER_RESIZE and
                        action.data.get('creation')):
                if member_id is None:
                    # Add new created nodes into lb pool
                    params = {
                        'pool_id': pool_id,
                        'node': node,
                        'port': port,
                        'subnet': subnet
                    }
                    member_id = self.lb_driver.member_add(**params)
                    if member_id is None:
                        action.data['status'] = base.CHECK_ERROR
                        action.data['reason'] = _('Failed in adding new node '
                                                  'into lb pool')
                        return

                    node.data.update({'lb_member': member_id})
                    node.store(action.context)
                else:
                    msg = _('Node %(node)s has been in a loadbalancer pool as'
                            'member %(member)s before being added to cluster '
                            '%(cluster)s.') % {'node': node_id,
                                               'member': member_id,
                                               'cluster': node.cluster_id}
                    LOG.warning(msg)

        return

    @property
    def lb_driver(self):
        if self.lb is None:
            self.lb = lbaas.LoadBalancerDriver(self.action.context)
            return self.lb
        else:
            return self.lb
