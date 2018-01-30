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

from oslo_context import context as oslo_context
from oslo_log import log as logging

from senlin.common import exception
from senlin.common.i18n import _
from senlin.drivers import base
from senlin.drivers.os import neutron_v2 as neutronclient
from senlin.drivers.os import octavia_v2 as octaviaclient
from senlin.engine import node as nodem

LOG = logging.getLogger(__name__)


class LoadBalancerDriver(base.DriverBase):
    """Load-balancing driver based on Neutron LBaaS V2 service."""

    def __init__(self, params):
        super(LoadBalancerDriver, self).__init__(params)
        self.lb_status_timeout = 600
        self._oc = None
        self._nc = None

    def oc(self):
        """Octavia client

        :return: octavia client
        """

        if self._oc:
            return self._oc

        self._oc = octaviaclient.OctaviaClient(self.conn_params)
        return self._oc

    def nc(self):
        """Neutron client

        :return: neutron client
        """
        if self._nc:
            return self._nc

        self._nc = neutronclient.NeutronClient(self.conn_params)
        return self._nc

    def _wait_for_lb_ready(self, lb_id, ignore_not_found=False):
        """Keep waiting until loadbalancer is ready

        This method will keep waiting until loadbalancer resource specified
        by lb_id becomes ready, i.e. its provisioning_status is ACTIVE and
        its operating_status is ONLINE.

        :param lb_id: ID of the load-balancer to check.
        :param ignore_not_found: if set to True, nonexistent loadbalancer
            resource is also an acceptable result.
        """
        waited = 0
        while waited < self.lb_status_timeout:
            try:
                lb = self.oc().loadbalancer_get(lb_id, ignore_missing=True)
            except exception.InternalError as ex:
                msg = ('Failed in getting loadbalancer: %s.'
                       % six.text_type(ex))
                LOG.exception(msg)
                return False
            if lb is None:
                lb_ready = ignore_not_found
            else:
                lb_ready = ((lb.provisioning_status == 'ACTIVE') and
                            (lb.operating_status == 'ONLINE'))

            if lb_ready is True:
                return True

            LOG.debug('Waiting for loadbalancer %(lb)s to become ready',
                      {'lb': lb_id})

            eventlet.sleep(10)
            waited += 10

        return False

    def lb_create(self, vip, pool, hm=None):
        """Create a LBaaS instance

        :param vip: A dict containing the properties for the VIP;
        :param pool: A dict describing the pool of load-balancer members.
        :param hm: A dict describing the health monitor.
        """
        def _cleanup(msg, **kwargs):
            LOG.error(msg)
            self.lb_delete(**kwargs)
            return

        result = {}
        # Create loadblancer
        try:
            subnet = self.nc().subnet_get(vip['subnet'])
        except exception.InternalError as ex:
            msg = 'Failed in getting subnet: %s.' % six.text_type(ex)
            LOG.exception(msg)
            return False, msg
        subnet_id = subnet.id
        try:
            lb = self.oc().loadbalancer_create(subnet_id,
                                               vip.get('address', None),
                                               vip['admin_state_up'])
        except exception.InternalError as ex:
            msg = ('Failed in creating loadbalancer: %s.'
                   % six.text_type(ex))
            LOG.exception(msg)
            return False, msg
        result['loadbalancer'] = lb.id
        result['vip_address'] = lb.vip_address

        res = self._wait_for_lb_ready(lb.id)
        if res is False:
            msg = 'Failed in creating loadbalancer (%s).' % lb.id
            del result['vip_address']
            _cleanup(msg, **result)
            return False, msg

        # Create listener
        try:
            listener = self.oc().listener_create(lb.id, vip['protocol'],
                                                 vip['protocol_port'],
                                                 vip.get('connection_limit',
                                                         None),
                                                 vip['admin_state_up'])
        except exception.InternalError as ex:
            msg = 'Failed in creating lb listener: %s.' % six.text_type(ex)
            LOG.exception(msg)
            return False, msg
        result['listener'] = listener.id
        res = self._wait_for_lb_ready(lb.id)
        if res is False:
            msg = 'Failed in creating listener (%s).' % listener.id
            del result['vip_address']
            _cleanup(msg, **result)
            return res, msg

        # Create pool
        try:
            pool = self.oc().pool_create(pool['lb_method'], listener.id,
                                         pool['protocol'],
                                         pool['admin_state_up'])
        except exception.InternalError as ex:
            msg = 'Failed in creating lb pool: %s.' % six.text_type(ex)
            LOG.exception(msg)
            return False, msg
        result['pool'] = pool.id
        res = self._wait_for_lb_ready(lb.id)
        if res is False:
            msg = 'Failed in creating pool (%s).' % pool.id
            del result['vip_address']
            _cleanup(msg, **result)
            return res, msg

        if not hm:
            return True, result

        # Create health monitor
        try:
            health_monitor = self.oc().healthmonitor_create(
                hm['type'], hm['delay'], hm['timeout'], hm['max_retries'],
                pool.id, hm['admin_state_up'], hm['http_method'],
                hm['url_path'], hm['expected_codes'])
        except exception.InternalError as ex:
            msg = ('Failed in creating lb health monitor: %s.'
                   % six.text_type(ex))
            LOG.exception(msg)
            return False, msg
        result['healthmonitor'] = health_monitor.id
        res = self._wait_for_lb_ready(lb.id)
        if res is False:
            msg = 'Failed in creating health monitor (%s).' % health_monitor.id
            del result['vip_address']
            _cleanup(msg, **result)
            return res, msg

        return True, result

    def lb_find(self, name_or_id, ignore_missing=False,
                show_deleted=False):
        return self.oc().loadbalancer_get(name_or_id, ignore_missing,
                                          show_deleted)

    def lb_delete(self, **kwargs):
        """Delete a Neutron lbaas instance

        The following Neutron lbaas resources will be deleted in order:
        1)healthmonitor; 2)pool; 3)listener; 4)loadbalancer.
        """
        lb_id = kwargs.pop('loadbalancer')

        lb = self.lb_find(lb_id, ignore_missing=True)
        if lb is None:
            LOG.debug('Loadbalancer (%s) is not existing.', lb_id)
            return True, _('LB deletion succeeded')

        healthmonitor_id = kwargs.pop('healthmonitor', None)
        if healthmonitor_id:
            try:
                self.oc().healthmonitor_delete(healthmonitor_id)
            except exception.InternalError as ex:
                msg = ('Failed in deleting healthmonitor: %s.'
                       % six.text_type(ex))
                LOG.exception(msg)
                return False, msg
            res = self._wait_for_lb_ready(lb_id)
            if res is False:
                msg = ('Failed in deleting healthmonitor '
                       '(%s).') % healthmonitor_id
                return False, msg

        pool_id = kwargs.pop('pool', None)
        if pool_id:
            try:
                self.oc().pool_delete(pool_id)
            except exception.InternalError as ex:
                msg = ('Failed in deleting lb pool: %s.'
                       % six.text_type(ex))
                LOG.exception(msg)
                return False, msg
            res = self._wait_for_lb_ready(lb_id)
            if res is False:
                msg = 'Failed in deleting pool (%s).' % pool_id
                return False, msg

        listener_id = kwargs.pop('listener', None)
        if listener_id:
            try:
                self.oc().listener_delete(listener_id)
            except exception.InternalError as ex:
                msg = ('Failed in deleting listener: %s.'
                       % six.text_type(ex))
                LOG.exception(msg)
                return False, msg
            res = self._wait_for_lb_ready(lb_id)
            if res is False:
                msg = 'Failed in deleting listener (%s).' % listener_id
                return False, msg

        self.oc().loadbalancer_delete(lb_id)
        res = self._wait_for_lb_ready(lb_id, ignore_not_found=True)
        if res is False:
            msg = 'Failed in deleting loadbalancer (%s).' % lb_id
            return False, msg

        return True, _('LB deletion succeeded')

    def member_add(self, node, lb_id, pool_id, port, subnet):
        """Add a member to Neutron lbaas pool.

        :param node: A node object to be added to the specified pool.
        :param lb_id: The ID of the loadbalancer.
        :param pool_id: The ID of the pool for receiving the node.
        :param port: The port for the new LB member to be created.
        :param subnet: The subnet to be used by the new LB member.
        :returns: The ID of the new LB member or None if errors occurred.
        """
        try:
            subnet_obj = self.nc().subnet_get(subnet)
            net_id = subnet_obj.network_id
            net = self.nc().network_get(net_id)
        except exception.InternalError as ex:
            resource = 'subnet' if subnet in ex.message else 'network'
            msg = ('Failed in getting %(resource)s: %(msg)s.'
                   % {'resource': resource, 'msg': six.text_type(ex)})
            LOG.exception(msg)
            return None
        net_name = net.name

        ctx = oslo_context.get_current()
        node_obj = nodem.Node.load(ctx, db_node=node)
        node_detail = node_obj.get_details(ctx)
        addresses = node_detail.get('addresses')
        if net_name not in addresses:
            msg = 'Node is not in subnet %(subnet)s'
            LOG.error(msg, {'subnet': subnet})
            return None

        # Use the first IP address if more than one are found in target network
        address = addresses[net_name][0]['addr']
        try:
            # FIXME(Yanyan Hu): Currently, Neutron lbaasv2 service can not
            # handle concurrent lb member operations well: new member creation
            # deletion request will directly fail rather than being lined up
            # when another operation is still in progress. In this workaround,
            # loadbalancer status will be checked before creating lb member
            # request is sent out. If loadbalancer keeps unready till waiting
            # timeout, exception will be raised to fail member_add.
            res = self._wait_for_lb_ready(lb_id)
            if not res:
                msg = 'Loadbalancer %s is not ready.' % lb_id
                raise exception.Error(msg)
            member = self.oc().pool_member_create(pool_id, address, port,
                                                  subnet_obj.id)
        except (exception.InternalError, exception.Error) as ex:
            msg = ('Failed in creating lb pool member: %s.'
                   % six.text_type(ex))
            LOG.exception(msg)
            return None
        res = self._wait_for_lb_ready(lb_id)
        if res is False:
            LOG.error('Failed in creating pool member (%s).', member.id)
            return None

        return member.id

    def member_remove(self, lb_id, pool_id, member_id):
        """Delete a member from Neutron lbaas pool.

        :param lb_id: The ID of the loadbalancer the operation is targeted at;
        :param pool_id: The ID of the pool from which the member is deleted;
        :param member_id: The ID of the LB member.
        :returns: True if the operation succeeded or False if errors occurred.
        """
        try:
            # FIXME(Yanyan Hu): Currently, Neutron lbaasv2 service can not
            # handle concurrent lb member operations well: new member creation
            # deletion request will directly fail rather than being lined up
            # when another operation is still in progress. In this workaround,
            # loadbalancer status will be checked before deleting lb member
            # request is sent out. If loadbalancer keeps unready till waiting
            # timeout, exception will be raised to fail member_remove.
            res = self._wait_for_lb_ready(lb_id)
            if not res:
                msg = 'Loadbalancer %s is not ready.' % lb_id
                raise exception.Error(msg)
            self.oc().pool_member_delete(pool_id, member_id)
        except (exception.InternalError, exception.Error) as ex:
            msg = ('Failed in removing member %(m)s from pool %(p)s: '
                   '%(ex)s' % {'m': member_id, 'p': pool_id,
                               'ex': six.text_type(ex)})
            LOG.exception(msg)
            return None
        res = self._wait_for_lb_ready(lb_id)
        if res is False:
            LOG.error('Failed in deleting pool member (%s).', member_id)
            return None

        return True
