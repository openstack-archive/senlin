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

"""
Policy for load-balancing among nodes in a cluster.

NOTE: For full documentation about how the deletion policy works, check:
http://docs.openstack.org/developer/senlin/developer/policies/
load_balance_v1.html
"""

from oslo_context import context as oslo_context
from oslo_log import log as logging

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common.i18n import _LW
from senlin.common import scaleutils
from senlin.common import schema
from senlin.drivers import base as driver_base
from senlin.engine import cluster_policy
from senlin.engine import node as nm
from senlin.objects import cluster as co
from senlin.objects import node as no
from senlin.policies import base

LOG = logging.getLogger(__name__)


class LoadBalancingPolicy(base.Policy):
    """Policy for load balancing among members of a cluster.

    This policy is expected to be enforced before or after the membership of a
    cluster is changed. We need to refresh the load-balancer associated with
    the cluster (which could be created by the policy) when these actions are
    performed.
    """
    VERSION = '1.0'

    PRIORITY = 500

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_SCALE_OUT),
        ('AFTER', consts.CLUSTER_RESIZE),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_RESIZE),
    ]

    PROFILE_TYPE = [
        'os.nova.server-1.0',
    ]

    KEYS = (
        POOL, VIP, HEALTH_MONITOR,
    ) = (
        'pool', 'vip', 'health_monitor',
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

    HEALTH_MONITOR_TYPES = (
        PING, TCP, HTTP, HTTPS,
    ) = (
        'PING', 'TCP', 'HTTP', 'HTTPS',
    )

    HTTP_METHODS = (
        GET, POST, PUT, DELETE,
    ) = (
        'GET', 'POST', 'PUT', 'DELETE',
    )

    _VIP_KEYS = (
        VIP_SUBNET, VIP_ADDRESS, VIP_CONNECTION_LIMIT, VIP_PROTOCOL,
        VIP_PROTOCOL_PORT, VIP_ADMIN_STATE_UP,
    ) = (
        'subnet', 'address', 'connection_limit', 'protocol',
        'protocol_port', 'admin_state_up',
    )

    HEALTH_MONITOR_KEYS = (
        HM_TYPE, HM_DELAY, HM_TIMEOUT, HM_MAX_RETRIES, HM_ADMIN_STATE_UP,
        HM_HTTP_METHOD, HM_URL_PATH, HM_EXPECTED_CODES,
    ) = (
        'type', 'delay', 'timeout', 'max_retries', 'admin_state_up',
        'http_method', 'url_path', 'expected_codes',
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
        HEALTH_MONITOR: schema.Map(
            _('Health monitor for loadbalancer.'),
            schema={
                HM_TYPE: schema.String(
                    _('The type of probe sent by the load balancer to verify '
                      'the member state.'),
                    constraints=[
                        constraints.AllowedValues(HEALTH_MONITOR_TYPES),
                    ],
                    default=PING,
                ),
                HM_DELAY: schema.Integer(
                    _('The amount of time in milliseconds between sending '
                      'probes to members.'),
                    default=10,
                ),
                HM_TIMEOUT: schema.Integer(
                    _('The maximum time in milliseconds that a monitor waits '
                      'to connect before it times out.'),
                    default=5,
                ),
                HM_MAX_RETRIES: schema.Integer(
                    _('The number of allowed connection failures before '
                      'changing the status of the member to INACTIVE.'),
                    default=3,
                ),
                HM_ADMIN_STATE_UP: schema.Boolean(
                    _('Administrative state of the health monitor.'),
                    default=True,
                ),
                HM_HTTP_METHOD: schema.String(
                    _('The HTTP method that the monitor uses for requests.'),
                    constraints=[
                        constraints.AllowedValues(HTTP_METHODS),
                    ],
                ),
                HM_URL_PATH: schema.String(
                    _('The HTTP path of the request sent by the monitor to '
                      'test the health of a member.'),
                ),
                HM_EXPECTED_CODES: schema.String(
                    _('Expected HTTP codes for a passing HTTP(S) monitor.'),
                ),
            },
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(LoadBalancingPolicy, self).__init__(name, spec, **kwargs)

        self.pool_spec = self.properties.get(self.POOL, {})
        self.vip_spec = self.properties.get(self.VIP, {})
        self.hm_spec = self.properties.get(self.HEALTH_MONITOR, None)
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

        nodes = nm.Node.load_all(oslo_context.get_current(),
                                 cluster_id=cluster.id)

        params = self._build_conn_params(cluster)
        lb_driver = driver_base.SenlinDriver().loadbalancing(params)

        res, data = lb_driver.lb_create(self.vip_spec, self.pool_spec,
                                        self.hm_spec)
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
                # TODO(anyone): May need to "roll-back" changes caused by any
                # successful member_add() calls.
                lb_driver.lb_delete(**data)
                return False, 'Failed in adding node into lb pool'

            node.data.update({'lb_member': member_id})
            node.store(oslo_context.get_current())

        cluster_data_lb = cluster.data.get('loadbalancers', {})
        cluster_data_lb[self.id] = {'vip_address': data.pop('vip_address')}
        cluster.data['loadbalancers'] = cluster_data_lb

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

        nodes = nm.Node.load_all(oslo_context.get_current(),
                                 cluster_id=cluster.id)
        for node in nodes:
            if 'lb_member' in node.data:
                node.data.pop('lb_member')
                node.store(oslo_context.get_current())

        lb_data = cluster.data.get('loadbalancers', {})
        if lb_data and isinstance(lb_data, dict):
            lb_data.pop(self.id, None)
            if lb_data:
                cluster.data['loadbalancers'] = lb_data
            else:
                cluster.data.pop('loadbalancers')

        return True, reason

    def _get_delete_candidates(self, cluster_id, action):
        deletion = action.data.get('deletion', None)
        # No deletion field in action.data which means no scaling
        # policy or deletion policy is attached.
        candidates = None
        if deletion is None:
            if action.action == consts.CLUSTER_DEL_NODES:
                # Get candidates from action.input
                candidates = action.inputs.get('candidates', [])
                count = len(candidates)
            elif action.action == consts.CLUSTER_RESIZE:
                # Calculate deletion count based on action input
                db_cluster = co.Cluster.get(action.context, cluster_id)
                scaleutils.parse_resize_params(action, db_cluster)
                if 'deletion' not in action.data:
                    return []
                else:
                    count = action.data['deletion']['count']
            else:  # action.action == consts.CLUSTER_SCALE_IN
                count = 1
        else:
            count = deletion.get('count', 0)
            candidates = deletion.get('candidates', None)

        # Still no candidates available, pick count of nodes randomly
        if candidates is None:
            if count == 0:
                return []
            nodes = no.Node.get_all_by_cluster(action.context, cluster_id)
            if count > len(nodes):
                count = len(nodes)
            candidates = scaleutils.nodes_by_random(nodes, count)
            deletion_data = action.data.get('deletion', {})
            deletion_data.update({
                'count': len(candidates),
                'candidates': candidates
            })
            action.data.update({'deletion': deletion_data})

        return candidates

    def pre_op(self, cluster_id, action):
        """Routine to be called before an action has been executed.

        For this particular policy, we take this chance to update the pool
        maintained by the load-balancer.

        :param cluster_id: The ID of the cluster on which a relevant action
            has been executed.
        :param action: The action object that triggered this operation.
        :returns: Nothing.
        """

        candidates = self._get_delete_candidates(cluster_id, action)
        if len(candidates) == 0:
            return

        db_cluster = co.Cluster.get(action.context, cluster_id)
        params = self._build_conn_params(db_cluster)
        lb_driver = driver_base.SenlinDriver().loadbalancing(params)
        cp = cluster_policy.ClusterPolicy.load(action.context, cluster_id,
                                               self.id)
        policy_data = self._extract_policy_data(cp.data)
        lb_id = policy_data['loadbalancer']
        pool_id = policy_data['pool']

        # Remove nodes that will be deleted from lb pool
        for node_id in candidates:
            node = nm.Node.load(action.context, node_id=node_id)
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

        return

    def post_op(self, cluster_id, action):
        """Routine to be called after an action has been executed.

        For this particular policy, we take this chance to update the pool
        maintained by the load-balancer.

        :param cluster_id: The ID of the cluster on which a relevant action
            has been executed.
        :param action: The action object that triggered this operation.
        :returns: Nothing.
        """

        # TODO(Yanyanhu): Need special handling for cross-az scenario
        # which is supported by Neutron lbaas.
        creation = action.data.get('creation', None)
        nodes_added = creation.get('nodes', []) if creation else []
        if len(nodes_added) == 0:
            return

        db_cluster = co.Cluster.get(action.context, cluster_id)
        params = self._build_conn_params(db_cluster)
        lb_driver = driver_base.SenlinDriver().loadbalancing(params)
        cp = cluster_policy.ClusterPolicy.load(action.context, cluster_id,
                                               self.id)
        policy_data = self._extract_policy_data(cp.data)
        lb_id = policy_data['loadbalancer']
        pool_id = policy_data['pool']
        port = self.pool_spec.get(self.POOL_PROTOCOL_PORT)
        subnet = self.pool_spec.get(self.POOL_SUBNET)

        # Add new nodes to lb pool
        for node_id in nodes_added:
            node = nm.Node.load(action.context, node_id=node_id)
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
