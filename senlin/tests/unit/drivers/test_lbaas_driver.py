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
import mock

from oslo_context import context as oslo_context

from senlin.common import exception
from senlin.common.i18n import _
from senlin.drivers.openstack import lbaas
from senlin.drivers.openstack import neutron_v2
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNeutronLBaaSDriver(base.SenlinTestCase):

    def setUp(self):
        super(TestNeutronLBaaSDriver, self).setUp()
        self.context = utils.dummy_context()
        self.conn_params = self.context.to_dict()
        self.lb_driver = lbaas.LoadBalancerDriver(self.conn_params)
        self.patchobject(neutron_v2, 'NeutronClient')
        self.nc = self.lb_driver.nc()

        self.vip = {
            'subnet': 'subnet-01',
            'address': '192.168.1.100',
            'admin_state_up': True,
            'protocol': 'HTTP',
            'protocol_port': 80,
            'connection_limit': 50
        }
        self.pool = {
            'lb_method': 'ROUND_ROBIN',
            'protocol': 'HTTP',
            'admin_state_up': True
        }
        self.hm = {
            "type": "HTTP",
            "delay": "1",
            "timeout": 1,
            "max_retries": 5,
            "pool_id": "POOL_ID",
            "admin_state_up": True,
            "http_method": "GET",
            "url_path": "/index.html",
            "expected_codes": "200,201,202"
        }

    def test_init(self):
        res = lbaas.LoadBalancerDriver(self.conn_params)
        self.assertEqual(self.conn_params, res.conn_params)
        self.assertIsNone(res._nc)

    @mock.patch.object(neutron_v2, 'NeutronClient')
    def test_nc_initialize(self, mock_neutron_client):
        fake_nc = mock.Mock()
        mock_neutron_client.return_value = fake_nc
        lb_driver = lbaas.LoadBalancerDriver(self.conn_params)
        self.assertIsNone(lb_driver._nc)

        # Create a new NeutronClient
        res = lb_driver.nc()
        mock_neutron_client.assert_called_once_with(self.conn_params)
        self.assertEqual(fake_nc, res)

        # Use the existing NeutronClient stored in self._nc
        fake_nc_new = mock.Mock()
        mock_neutron_client.return_value = fake_nc_new
        res1 = lb_driver.nc()
        mock_neutron_client.assert_called_once_with(self.conn_params)
        self.assertNotEqual(fake_nc_new, res1)
        self.assertEqual(res, res1)

    def test_wait_for_lb_ready(self):
        lb_id = 'ID1'
        lb_obj = mock.Mock()
        lb_obj.id = lb_id
        lb_obj.provisioning_status = 'ACTIVE'
        lb_obj.operating_status = 'ONLINE'
        self.nc.loadbalancer_get.return_value = lb_obj

        res = self.lb_driver._wait_for_lb_ready(lb_id, timeout=4)
        self.assertTrue(res)

    def test_wait_for_lb_ready_ignore_not_found(self):
        lb_id = 'LB_ID'
        self.nc.loadbalancer_get.return_value = None

        res = self.lb_driver._wait_for_lb_ready(lb_id, timeout=4,
                                                ignore_not_found=True)
        self.assertTrue(res)

    @mock.patch.object(eventlet, 'sleep')
    def test_wait_for_lb_ready_timeout(self, mock_sleep):
        lb_id = 'LB_ID'
        lb_obj = mock.Mock()
        lb_obj.id = lb_id
        self.nc.loadbalancer_get.return_value = lb_obj

        lb_obj.provisioning_status = 'PENDING_UPDATE'
        lb_obj.operating_status = 'OFFLINE'
        res = self.lb_driver._wait_for_lb_ready(lb_id, timeout=2)
        self.assertFalse(res)
        mock_sleep.assert_called_once_with(2)

    def test_lb_create_succeeded(self):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        pool_obj = mock.Mock()
        hm_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        lb_obj.vip_address = '192.168.1.100'
        listener_obj.id = 'LISTENER_ID'
        pool_obj.id = 'POOL_ID'
        subnet_obj = mock.Mock()
        subnet_obj.name = 'subnet1'
        subnet_obj.id = 'SUBNET_ID'
        subnet_obj.network_id = 'NETWORK_ID'
        hm_obj.id = 'HEALTHMONITOR_ID'

        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.nc.pool_create.return_value = pool_obj
        self.nc.healthmonitor_create.return_value = hm_obj
        self.nc.subnet_get.return_value = subnet_obj

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True
        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)

        self.assertTrue(status)
        self.nc.loadbalancer_create.assert_called_once_with(
            'SUBNET_ID', self.vip['address'], self.vip['admin_state_up'])
        self.assertEqual('LB_ID', res['loadbalancer'])
        self.assertEqual('192.168.1.100', res['vip_address'])
        self.nc.listener_create.assert_called_once_with(
            'LB_ID', self.vip['protocol'], self.vip['protocol_port'],
            self.vip['connection_limit'], self.vip['admin_state_up'])
        self.assertEqual('LISTENER_ID', res['listener'])
        self.nc.pool_create.assert_called_once_with(
            self.pool['lb_method'], 'LISTENER_ID', self.pool['protocol'],
            self.pool['admin_state_up'])
        self.assertEqual('POOL_ID', res['pool'])
        self.nc.healthmonitor_create.assert_called_once_with(
            self.hm['type'], self.hm['delay'], self.hm['timeout'],
            self.hm['max_retries'], 'POOL_ID', self.hm['admin_state_up'],
            self.hm['http_method'], self.hm['url_path'],
            self.hm['expected_codes'])
        self.assertEqual('HEALTHMONITOR_ID', res['healthmonitor'])
        self.lb_driver._wait_for_lb_ready.assert_called_with('LB_ID')
        calls = [mock.call('LB_ID') for i in range(1, 5)]
        self.lb_driver._wait_for_lb_ready.assert_has_calls(
            calls, any_order=False)

    def test_lb_create_loadbalancer_creation_failed(self):
        lb_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        subnet_obj = mock.Mock()
        subnet_obj.name = 'subnet1'
        subnet_obj.id = 'SUBNET_ID'
        subnet_obj.network_id = 'NETWORK_ID'
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.subnet_get.return_value = subnet_obj

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [False]
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating load balancer (%s).') % 'LB_ID'
        self.assertEqual(msg, res)
        self.nc.loadbalancer_create.assert_called_once_with(
            'SUBNET_ID', self.vip['address'], self.vip['admin_state_up'])
        self.lb_driver._wait_for_lb_ready.assert_called_once_with('LB_ID')
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID')

        # Exception happens in subnet_get.
        self.nc.subnet_get.side_effect = exception.InternalError(
            code=500, message='GET FAILED')
        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in getting subnet: GET FAILED.')
        self.assertEqual(msg, res)

        # Exception happens in loadbalancer_create.
        self.nc.subnet_get.side_effect = None
        self.nc.loadbalancer_create.side_effect = exception.InternalError(
            code=500, message='CREATE FAILED')
        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating loadbalancer: CREATE FAILED.')
        self.assertEqual(msg, res)

    @mock.patch.object(eventlet, 'sleep')
    def test_lb_create_listener_creation_failed(self, mock_sleep):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        listener_obj.id = 'LISTENER_ID'
        subnet_obj = mock.Mock()
        subnet_obj.name = 'subnet1'
        subnet_obj.id = 'SUBNET_ID'
        subnet_obj.network_id = 'NETWORK_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, False]
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.nc.subnet_get.return_value = subnet_obj
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating listener (%s).') % 'LISTENER_ID'
        self.assertEqual(msg, res)
        self.nc.loadbalancer_create.assert_called_once_with(
            'SUBNET_ID', self.vip['address'], self.vip['admin_state_up'])
        self.nc.listener_create.assert_called_once_with(
            'LB_ID', self.vip['protocol'], self.vip['protocol_port'],
            self.vip['connection_limit'], self.vip['admin_state_up'])
        self.lb_driver._wait_for_lb_ready.assert_called_with('LB_ID')
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID', listener='LISTENER_ID')

        # Exception happens in listen_create
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, False]
        self.nc.listener_create.side_effect = exception.InternalError(
            code=500, message='CREATE FAILED')
        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating lb listener: CREATE FAILED.')
        self.assertEqual(msg, res)

    def test_lb_create_pool_creation_failed(self):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        pool_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        lb_obj.vip_address = '192.169.1.100'
        listener_obj.id = 'LISTENER_ID'
        pool_obj.id = 'POOL_ID'
        subnet_obj = mock.Mock()
        subnet_obj.name = 'subnet1'
        subnet_obj.id = 'SUBNET_ID'
        subnet_obj.network_id = 'NETWORK_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, True, False]
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.nc.pool_create.return_value = pool_obj
        self.nc.subnet_get.return_value = subnet_obj
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating pool (%s).') % 'POOL_ID'
        self.assertEqual(msg, res)
        self.nc.loadbalancer_create.assert_called_once_with(
            'SUBNET_ID', self.vip['address'], self.vip['admin_state_up'])
        self.nc.listener_create.assert_called_once_with(
            'LB_ID', self.vip['protocol'], self.vip['protocol_port'],
            self.vip['connection_limit'], self.vip['admin_state_up'])
        self.nc.pool_create.assert_called_once_with(
            self.pool['lb_method'], 'LISTENER_ID', self.pool['protocol'],
            self.pool['admin_state_up'])
        self.lb_driver._wait_for_lb_ready.assert_called_with('LB_ID')
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID', listener='LISTENER_ID', pool='POOL_ID')

        # Exception happens in pool_create
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, True, False]
        self.nc.pool_create.side_effect = exception.InternalError(
            code=500, message='CREATE FAILED')
        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating lb pool: CREATE FAILED.')
        self.assertEqual(msg, res)

    def test_lb_create_healthmonitor_creation_failed(self):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        pool_obj = mock.Mock()
        hm_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        listener_obj.id = 'LISTENER_ID'
        pool_obj.id = 'POOL_ID'
        subnet_obj = mock.Mock()
        subnet_obj.name = 'subnet1'
        subnet_obj.id = 'SUBNET_ID'
        subnet_obj.network_id = 'NETWORK_ID'
        hm_obj.id = 'HEALTHMONITOR_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, True,
                                                         True, False]
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.nc.pool_create.return_value = pool_obj
        self.nc.healthmonitor_create.return_value = hm_obj
        self.nc.subnet_get.return_value = subnet_obj
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating health monitor (%s).') % 'HEALTHMONITOR_ID'
        self.assertEqual(msg, res)
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID', listener='LISTENER_ID', pool='POOL_ID',
            healthmonitor='HEALTHMONITOR_ID')

        # Exception happens in healthmonitor_create
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, True, True]
        self.nc.healthmonitor_create.side_effect = exception.InternalError(
            code=500, message='CREATE FAILED')
        status, res = self.lb_driver.lb_create(self.vip, self.pool, self.hm)
        self.assertFalse(status)
        msg = _('Failed in creating lb health monitor: CREATE FAILED.')
        self.assertEqual(msg, res)

    def test_lb_delete(self):
        kwargs = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True

        status, res = self.lb_driver.lb_delete(**kwargs)
        self.assertTrue(status)
        self.assertEqual('LB deletion succeeded', res)
        self.nc.loadbalancer_delete.assert_called_once_with('LB_ID')
        self.nc.listener_delete.assert_called_once_with('LISTENER_ID')
        self.nc.pool_delete.assert_called_once_with('POOL_ID')
        self.nc.healthmonitor_delete.assert_called_once_with('HM_ID')
        calls = [mock.call('LB_ID') for i in range(1, 4)]
        self.lb_driver._wait_for_lb_ready.assert_has_calls(
            calls, any_order=False)

    def test_lb_healthmonitor_delete_internalerror(self):
        kwargs = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.nc.healthmonitor_delete.side_effect = exception.InternalError(
            code=500, message='DELETE FAILED')
        status, res = self.lb_driver.lb_delete(**kwargs)
        self.assertFalse(status)
        msg = _('Failed in deleting healthmonitor: DELETE FAILED.')
        self.assertEqual(msg, res)

    def test_lb_pool_delete_internalerror(self):
        kwargs = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.nc.pool_delete.side_effect = exception.InternalError(
            code=500, message='DELETE FAILED')
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True
        status, res = self.lb_driver.lb_delete(**kwargs)
        self.assertFalse(status)
        msg = _('Failed in deleting lb pool: DELETE FAILED.')
        self.assertEqual(msg, res)

    def test_lb_listener_delete_internalerror(self):
        kwargs = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.nc.listener_delete.side_effect = exception.InternalError(
            code=500, message='DELETE FAILED')
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True
        status, res = self.lb_driver.lb_delete(**kwargs)
        self.assertFalse(status)
        msg = _('Failed in deleting listener: DELETE FAILED.')
        self.assertEqual(msg, res)

    def test_lb_delete_no_physical_object(self):
        kwargs = {'loadbalancer': 'LB_ID'}
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True

        status, res = self.lb_driver.lb_delete(**kwargs)
        self.assertTrue(status)
        self.assertEqual('LB deletion succeeded', res)
        self.nc.loadbalancer_delete.assert_called_once_with('LB_ID')
        self.assertEqual(0, self.nc.healthmonitor_delete.call_count)
        self.assertEqual(0, self.nc.pool_delete.call_count)
        self.assertEqual(0, self.nc.listener_delete.call_count)
        self.lb_driver._wait_for_lb_ready.assert_called_once_with(
            'LB_ID', ignore_not_found=True)

    @mock.patch.object(oslo_context, 'get_current')
    def test_member_add(self, mock_get_current):
        node = mock.Mock()
        lb_id = 'LB_ID'
        pool_id = 'POOL_ID'
        port = '80'
        subnet = 'subnet1'
        subnet_obj = mock.Mock()
        subnet_obj.name = 'subnet1'
        subnet_obj.id = 'SUBNET_ID'
        subnet_obj.network_id = 'NETWORK_ID'
        network_obj = mock.Mock()
        network_obj.name = 'network1'
        network_obj.id = 'NETWORK_ID'
        member = mock.Mock()
        member.id = 'MEMBER_ID'
        node_detail = {
            'name': 'node-01',
            'addresses': {
                'network1': ['ipaddr_net1'],
                'network2': ['ipaddr_net2']
            }
        }
        node.get_details.return_value = node_detail

        self.nc.subnet_get.return_value = subnet_obj
        self.nc.network_get.return_value = network_obj
        self.nc.pool_member_create.return_value = member
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True

        res = self.lb_driver.member_add(node, lb_id, pool_id, port, subnet)
        self.assertEqual('MEMBER_ID', res)
        self.nc.subnet_get.assert_called_once_with(subnet)
        self.nc.network_get.assert_called_once_with('NETWORK_ID')
        self.nc.pool_member_create.assert_called_once_with(
            pool_id, 'ipaddr_net1', port, 'SUBNET_ID')

        # Exception happens in subnet_get
        self.nc.subnet_get.side_effect = exception.InternalError(
            code=500, message="Can't find subnet1")
        res = self.lb_driver.member_add(node, lb_id, pool_id, port, subnet)
        self.assertIsNone(res)

        # Exception happens in network_get
        self.nc.subnet_get.side_effect = None
        self.nc.subnet_get.return_value = subnet_obj
        self.nc.network_get.side_effect = exception.InternalError(
            code=500, message="Can't find NETWORK_ID")
        res = self.lb_driver.member_add(node, lb_id, pool_id, port, subnet)
        self.assertIsNone(res)

        # Exception happens in pool_member_create
        self.nc.subnet_get.side_effect = None
        self.nc.subnet_get.return_value = subnet_obj
        self.nc.network_get.side_effect = None
        self.nc.network_get.return_value = network_obj
        self.nc.pool_member_create.side_effect = exception.InternalError(
            code=500, message="CREATE FAILED")
        res = self.lb_driver.member_add(node, lb_id, pool_id, port, subnet)
        self.assertIsNone(res)

    @mock.patch.object(oslo_context, 'get_current')
    def test_member_add_node_not_in_subnet(self, mock_get_current):
        node = mock.Mock()
        lb_id = 'LB_ID'
        pool_id = 'POOL_ID'
        port = '80'
        subnet = 'subnet1'
        network_obj = mock.Mock()
        network_obj.name = 'network3'
        network_obj.id = 'NETWORK_ID'
        node_detail = {
            'name': 'node-01',
            'addresses': {
                'network1': ['ipaddr_net1'],
                'network2': ['ipaddr_net2']
            }
        }
        node.get_details.return_value = node_detail

        self.nc.network_get.return_value = network_obj
        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True

        res = self.lb_driver.member_add(node, lb_id, pool_id, port, subnet)
        self.assertIsNone(res)

    def test_member_remove_succeeded(self):
        lb_id = 'LB_ID'
        pool_id = 'POOL_ID'
        member_id = 'MEMBER_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True

        res = self.lb_driver.member_remove(lb_id, pool_id, member_id)
        self.assertTrue(res)
        self.nc.pool_member_delete.assert_called_once_with(pool_id, member_id)
        self.lb_driver._wait_for_lb_ready.assert_called_once_with(lb_id)

    def test_member_remove_failed(self):
        lb_id = 'LB_ID'
        pool_id = 'POOL_ID'
        member_id = 'MEMBER_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True
        self.nc.pool_member_delete.side_effect = exception.InternalError(
            code=500, message='')
        res = self.lb_driver.member_remove(lb_id, pool_id, member_id)
        self.assertFalse(res)
        self.nc.pool_member_delete.assert_called_once_with(pool_id, member_id)

        self.nc.pool_member_delete.side_effect = None
        self.lb_driver._wait_for_lb_ready.return_value = False
        res = self.lb_driver.member_remove(lb_id, pool_id, member_id)
        self.assertIsNone(res)
        self.lb_driver._wait_for_lb_ready.assert_called_once_with(lb_id)
