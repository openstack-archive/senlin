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

import eventlet
import six

from oslo_log import log as logging

from senlin.common.i18n import _
from senlin.common import trust
from senlin.drivers import base
from senlin.drivers.openstack import neutron_v2 as neutronclient

LOG = logging.getLogger(__name__)


class LoadBalancerDriver(base.DriverBase):
    """Common driver for LoadBalancer management"""

    def __init__(self, context):
        super(LoadBalancerDriver, self).__init__(context)
        self.context = context
        params = trust.get_connection_params(context)
        self.nc = neutronclient.NeutronClient(params)

    def _wait_for_lb_ready(self, lb_data, ignore_not_found=False):
        """Keep waiting until loadbalancer is in ready status

        This method will keep waiting until loadbalancer resource listed in
        lb_data becoming ready which means its provisioning_status is ACTIVE
        its operating_status is ONLINE. If ignore_not_found is set to True,
        unexisting of loadbalancer resource is also an acceptable result.
        """
        loadbalancer_id = lb_data.get('loadbalancer')

        while True:
            loadbalancer_ready = True

            if loadbalancer_id:
                lb = self.nc.loadbalancer_get(loadbalancer_id)
                if lb is None:
                    loadbalancer_ready = True if ignore_not_found else False
                elif (lb.provisioning_status == 'ACTIVE') and (
                        lb.operating_status == 'ONLINE'):
                    loadbalancer_ready = True
                else:
                    loadbalancer_ready = False

            if loadbalancer_ready:
                return True, lb_data
            else:
                LOG.debug(_('Waiting for loadbalancer %(lb)s becoming ready'
                            ) % {'lb': loadbalancer_id})

                eventlet.sleep(2)

            # TODO(Yanyan Hu): Add timeout check.

    def lb_create(self, vip, pool):
        """Create a Neutron lbaas instance"""

        # Catch all exceptions that could happen in each step and gracefully
        # removing all lbaas related resources that have been created before
        # returning.
        try:
            # Create loadblancer
            lb_data = {}
            subnet = vip.get('subnet', None)
            subnet_id = (self.nc.subnet_get(subnet)).id
            address = vip.get('address', None)
            admin_state_up = vip.get('admin_state_up', None)

            lb = self.nc.loadbalancer_create(subnet_id, address,
                                             admin_state_up)
            lb_data['loadbalancer'] = lb.id
            res, reason = self._wait_for_lb_ready(lb_data)
            if res is not True:
                return res, reason

            # Create listener
            protocol = vip.get('protocol')
            protocol_port = vip.get('protocol_port')
            connection_limit = vip.get('connection_limit', None)

            listener = self.nc.listener_create(lb.id, protocol, protocol_port,
                                               connection_limit,
                                               admin_state_up)
            lb_data['listener'] = listener.id
            res, reason = self._wait_for_lb_ready(lb_data)
            if res is not True:
                return res, reason

            # Create pool
            lb_algorithm = pool.get('lb_method')
            protocol = pool.get('protocol')
            admin_state_up = pool.get('admin_state_up')

            pool = self.nc.pool_create(lb_algorithm, listener.id, protocol,
                                       admin_state_up)
            lb_data['pool'] = pool.id
            res, reason = self._wait_for_lb_ready(lb_data)
            if res is not True:
                return res, reason
        except Exception as ex:
            self.lb_delete(**lb_data)
            msg = _('Failed in creating lb resources: %(ex)s '
                    ) % {'ex': six.text_type(ex)}
            LOG.error(msg)
            return False, msg

        return True, lb_data

    def lb_delete(self, **kwargs):
        """Delete a Neutron lbaas instance

        The following Neutron lbaas resources will be deleted in order:
        1)healthmonitor; 2)pool; 3)listener; 4)loadbalancer.
        """

        loadbalancer_id = kwargs.get('loadbalancer')
        listener_id = kwargs.get('listener')
        pool_id = kwargs.get('pool')
        healthmonitor_id = kwargs.get('healthmonitor', None)
        lb_data = kwargs

        try:
            if healthmonitor_id is not None:
                self.nc.healthmonitor_delete(healthmonitor_id)
                del lb_data['healthmonitor']
                self._wait_for_lb_ready(lb_data, ignore_not_found=True)

            self.nc.pool_delete(pool_id)
            del lb_data['pool']
            self._wait_for_lb_ready(lb_data, ignore_not_found=True)

            self.nc.listener_delete(listener_id)
            del lb_data['listener']
            self._wait_for_lb_ready(lb_data, ignore_not_found=True)

            self.nc.loadbalancer_delete(loadbalancer_id)

        except Exception as ex:
            msg = _('Failed in deleting lb resources %(data)s: %(ex)s'
                    ) % {'data': lb_data, 'ex': six.text_type(ex)}
            LOG.error(msg)
            return False, msg

        return True, 'lb resource deleting succeeded'

    def member_add(self, **kwargs):
        """Add a member to Neutron lbaas pool"""

        node = kwargs.get('node')
        pool_id = kwargs.get('pool_id')
        port = kwargs.get('port')
        subnet = kwargs.get('subnet')

        try:
            addresses = self._get_node_address(node, version=4)
            if not addresses:
                msg = _('Node does not have valid IPv%(version)s address'
                        ) % {'version': 4}
                raise Exception(msg)
            else:
                network_id = (self.nc.subnet_get(subnet))['network_id']
                network_name = (self.nc.network_get(network_id))['name']
                if network_name in addresses:
                    address = addresses[network_name]
                else:
                    msg = _('Node is not in subnet %(subnet)s'
                            ) % {'subnet': subnet}
                    raise Exception(msg)

            subnet_id = (self.nc.subnet_get(subnet)).id
            pool_member = self.nc.pool_member_create(pool_id, address, port,
                                                     subnet_id)

            pool = self.nc.pool_get(pool_id)
            listener = self.nc.listener_get(pool.listeners[0]['id'])
            lb_data = {
                'loadbalancer': listener.loadbalancers[0]['id'],
                'member': pool_member.id
            }
            self._wait_for_lb_ready(lb_data)
        except Exception as ex:
            msg = _('Failed in adding node %(node)s into pool %(pool)s as '
                    'a member: %(ex)s') % {'node': node.id, 'pool': pool_id,
                                           'ex': six.text_type(ex)}
            LOG.error(msg)
            return False

        return pool_member.id

    def member_remove(self, **kwargs):
        """Delete a member from Neutron lbaas pool"""

        pool_id = kwargs.get('pool_id')
        member_id = kwargs.get('member_id')

        try:
            self.nc.pool_member_delete(pool_id, member_id)
            pool = self.nc.pool_get(pool_id)
            listener = self.nc.listener_get(pool.listeners[0]['id'])
            lb_data = {
                'loadbalancer': listener.loadbalancers[0]['id'],
            }
            self._wait_for_lb_ready(lb_data)
        except Exception as ex:
            msg = _('Failed in removing member %(member)s from pool %(pool): '
                    '%(ex)s') % {'member': member_id, 'pool': pool_id,
                                 'ex': six.test_type(ex)}
            LOG.error(msg)
            return False

        return True

    def _get_node_address(self, node, version=4):
        """Get IP address of node with specific version"""

        node_detail = node.get_details(self.context)
        node_addresses = node_detail.get('addresses')

        address = {}
        for network in node_addresses:
            for addr in node_addresses[network]:
                if addr['version'] == version:
                    address[network] = addr['addr']

        return address
