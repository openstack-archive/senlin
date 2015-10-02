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

from oslo_context import context as oslo_context
from oslo_log import log as logging

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common.i18n import _LW
from senlin.common import schema
from senlin.db import api as db_api
from senlin.drivers import base as driver_base
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
    VERSION = '1.0'

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_DEL_NODES),
        ('AFTER', consts.CLUSTER_SCALE_OUT),
        ('AFTER', consts.CLUSTER_SCALE_IN),
        ('AFTER', consts.CLUSTER_RESIZE),
    ]

    PROFILE_TYPE = [
        'os.nova.server-1.0',
    ]

    KEYS = (
        POOL, VIP,
    ) = (
        'pool', 'vip',
    )

    _POOL_KEYS = (
        POOL_PROTOCOL, POOL_PROTOCOL_PORT, POOL_SUBNET,
        POOL_LB_METHOD, POOL_ADMIN_STATE_UP, POOL_SESSION_PERSISTENCE,
    ) = (
        'protocol', 'protocol_port', 'subnet',
        'lb_method', 'admin_state_up', 'session_persistence',
    )

    PROTOCOLS = (
        HTTP, HTTPS, TCP,
    ) = (
        'HTTP', 'HTTPS', 'TCP',
    )

    LB_METHODS = (
        ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP,
    ) = (
        'ROUND_ROBIN', 'LEAST_CONNECTIONS', 'SOURCE_IP',
    )

    _VIP_KEYS = (
        VIP_SUBNET, VIP_ADDRESS, VIP_CONNECTION_LIMIT, VIP_PROTOCOL,
        VIP_PROTOCOL_PORT, VIP_ADMIN_STATE_UP,
    ) = (
        'subnet', 'address', 'connection_limit', 'protocol',
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

    properties_schema = {
        POOL: schema.Map(
            _('LB pool properties.'),
            schema={
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
                        ),
                        COOKIE_NAME: schema.String(
                            _('Name of cookie if type set to APP_COOKIE.'),
                        ),
                    },
                    default={},
                ),
            },
        ),
        VIP: schema.Map(
            _('VIP address and port of the pool.'),
            schema={
                VIP_SUBNET: schema.String(
                    _('Name or ID of Subnet on which the VIP address will be '
                      'allocated.'),
                    required=True,
                ),
                VIP_ADDRESS: schema.String(
                    _('IP address of the VIP.'),
                    default=None,
                ),
                VIP_CONNECTION_LIMIT: schema.Integer(
                    _('Maximum number of connections per second allowed for '
                      'this VIP'),
                    default=-1,
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

    def __init__(self, name, spec, **kwargs):
        super(LoadBalancingPolicy, self).__init__(name, spec, **kwargs)

        self.pool_spec = self.properties.get(self.POOL, {})
        self.vip_spec = self.properties.get(self.VIP, {})
        self.validate()
        self.lb = None

    def validate(self):
        super(LoadBalancingPolicy, self).validate()

        # validate subnet's exists
        # subnet = self.nc.subnet_get(vip[self.VIP_SUBNET])

    def attach(self, cluster):
        """Routine to be invoked when policy is to be attached to a cluster.

        :param cluster: The target cluster to be attached to;
        :returns: When the operation was successful, returns a tuple (True,
                  message); otherwise, return a tuple (False, error).
        """
        res, data = super(LoadBalancingPolicy, self).attach(cluster)
        if res is False:
            return False, data

        nodes = node_mod.Node.load_all(oslo_context.get_current(),
                                       cluster_id=cluster.id)

        params = self._build_conn_params(cluster)
        lb_driver = driver_base.SenlinDriver().loadbalancing(params)

        res, data = lb_driver.lb_create(self.vip_spec, self.pool_spec)
        if res is False:
            return False, data

        port = self.pool_spec.get(self.POOL_PROTOCOL_PORT)
        subnet = self.pool_spec.get(self.POOL_SUBNET)

        for node in nodes:
            member_id = lb_driver.member_add(node, data['loadbalancer'],
                                             data['pool'], port, subnet)
            if member_id is None:
                # When failed in adding member, remove all lb resources that
                # were created and return the failure reason.
                # TODO(Yanyan Hu): Maybe we should tolerate member adding
                # failure and allow policy attaching to succeed without
                # all nodes being added into lb pool?
                lb_driver.lb_delete(**data)
                return False, 'Failed in adding node into lb pool'

            node.data.update({'lb_member': member_id})
            node.store(oslo_context.get_current())

        policy_data = self._build_policy_data(data)

        return True, policy_data

    def detach(self, cluster):
        """Routine to be called when the policy is detached from a cluster.

        :param cluster: The cluster from which the policy is to be detached.
        :returns: When the operation was successful, returns a tuple of
            (True, data) where the data contains references to the resources
            created; otherwise returns a tuple of (False, err) where the err
            contains a error message.
        """
        reason = _('LB resources deletion succeeded.')
        params = self._build_conn_params(cluster)
        lb_driver = driver_base.SenlinDriver().loadbalancing(params)

        cp = cluster_policy.ClusterPolicy.load(oslo_context.get_current(),
                                               cluster.id, self.id)

        policy_data = self._extract_policy_data(cp.data)
        if policy_data is None:
            return True, reason

        res, reason = lb_driver.lb_delete(**policy_data)
        if res is False:
            return False, reason

        nodes = node_mod.Node.load_all(oslo_context.get_current(),
                                       cluster_id=cluster.id)
        for node in nodes:
            if 'lb_member' in node.data:
                node.data.pop('lb_member')
                node.store(oslo_context.get_current())

        return True, reason

    def post_op(self, cluster_id, action):
        """Routine to be called after an action has been executed.

        For this particular policy, we take this chance to update the pool
        maintained by the load-balancer.

        :param cluster_id: The ID of the cluster on which a relevant action
            has been executed.
        :param action: The action object that triggered this operation.
        :returns: Nothing.
        """
        nodes_added = action.outputs.get('nodes_added', [])
        nodes_removed = action.outputs.get('nodes_removed', [])
        if ((len(nodes_added) == 0) and (len(nodes_removed) == 0)):
            return

        db_cluster = db_api.cluster_get(action.context, cluster_id)
        params = self._build_conn_params(db_cluster)
        lb_driver = driver_base.SenlinDriver().loadbalancing(params)
        cp = cluster_policy.ClusterPolicy.load(action.context, cluster_id,
                                               self.id)
        policy_data = self._extract_policy_data(cp.data)
        lb_id = policy_data['loadbalancer']
        pool_id = policy_data['pool']
        port = self.pool_spec.get(self.POOL_PROTOCOL_PORT)
        subnet = self.pool_spec.get(self.POOL_SUBNET)

        # Remove nodes that have been deleted from lb pool
        for node_id in nodes_removed:
            node = node_mod.Node.load(action.context, node_id=node_id,
                                      show_deleted=True)
            member_id = node.data.get('lb_member', None)
            if member_id is None:
                LOG.warning(_LW('Node %(n)s not found in lb pool %(p)s.'),
                            {'n': node_id, 'p': pool_id})
                continue

            res = lb_driver.member_remove(lb_id, pool_id, member_id)
            if res is not True:
                action.data['status'] = base.CHECK_ERROR
                action.data['reason'] = _('Failed in removing deleted '
                                          'node(s) from lb pool.')
                return

        # Add new nodes to lb pool
        for node_id in nodes_added:
            node = node_mod.Node.load(action.context, node_id=node_id,
                                      show_deleted=True)
            member_id = node.data.get('lb_member', None)
            if member_id:
                LOG.warning(_LW('Node %(n)s already in lb pool %(p)s.'),
                            {'n': node_id, 'p': pool_id})
                continue

            member_id = lb_driver.member_add(node, lb_id, pool_id, port,
                                             subnet)
            if member_id is None:
                action.data['status'] = base.CHECK_ERROR
                action.data['reason'] = _('Failed in adding new node(s) '
                                          'into lb pool.')
                return

            node.data.update({'lb_member': member_id})
            node.store(action.context)

        return
