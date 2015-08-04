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

from senlin.common.i18n import _
from senlin.drivers.openstack import lbaas
from senlin.drivers.openstack import neutron_v2
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNeutronLBaaSDriver(base.SenlinTestCase):

    def setUp(self):
        super(TestNeutronLBaaSDriver, self).setUp()
        self.context = utils.dummy_context()
        self.lb_driver = lbaas.LoadBalancerDriver(self.context)
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

    def test_init(self):
        res = lbaas.LoadBalancerDriver(self.context)
        self.assertEqual(self.context, res.ctx)
        self.assertIsNone(res._nc)

    @mock.patch.object(neutron_v2, 'NeutronClient')
    def test_nc_initialize(self, mock_neutron_client):
        fake_nc = mock.Mock()
        mock_neutron_client.return_value = fake_nc
        lb_driver = lbaas.LoadBalancerDriver(self.context)
        self.assertIsNone(lb_driver._nc)

        # Create a new NeutronClient
        res = lb_driver.nc()
        mock_neutron_client.assert_called_once_with(self.context)
        self.assertEqual(fake_nc, res)

        # Use the existing NeutronClient stored in self._nc
        fake_nc_new = mock.Mock()
        mock_neutron_client.return_value = fake_nc_new
        res1 = lb_driver.nc()
        mock_neutron_client.assert_called_once_with(self.context)
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

    def test_lb_create_succeed(self):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        pool_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        listener_obj.id = 'LISTENER_ID'
        pool_obj.id = 'POOL_ID'
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.nc.pool_create.return_value = pool_obj

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.return_value = True
        status, res = self.lb_driver.lb_create(self.vip, self.pool)

        self.assertTrue(status)
        self.nc.loadbalancer_create.assert_called_once_with(
            self.vip['subnet'], self.vip['address'],
            self.vip['admin_state_up'])
        self.assertEqual('LB_ID', res['loadbalancer'])
        self.nc.listener_create.assert_called_once_with(
            'LB_ID', self.vip['protocol'], self.vip['protocol_port'],
            self.vip['connection_limit'], self.vip['admin_state_up'])
        self.assertEqual('LISTENER_ID', res['listener'])
        self.nc.pool_create.assert_called_once_with(
            self.pool['lb_method'], 'LISTENER_ID', self.pool['protocol'],
            self.pool['admin_state_up'])
        self.assertEqual('POOL_ID', res['pool'])
        self.lb_driver._wait_for_lb_ready.assert_called_with('LB_ID')
        calls = [mock.call('LB_ID'), mock.call('LB_ID'),
                 mock.call('LB_ID')]
        self.lb_driver._wait_for_lb_ready.assert_has_calls(
            calls, any_order=False)

    def test_lb_create_loadbalancer_creation_failed(self):
        lb_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        self.nc.loadbalancer_create.return_value = lb_obj

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [False]
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool)
        self.assertFalse(status)
        msg = _('Failed in creating load balancer (%s).') % 'LB_ID'
        self.assertEqual(msg, res)
        self.nc.loadbalancer_create.assert_called_once_with(
            self.vip['subnet'], self.vip['address'],
            self.vip['admin_state_up'])
        self.lb_driver._wait_for_lb_ready.assert_called_once_with('LB_ID')
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID')

    @mock.patch.object(eventlet, 'sleep')
    def test_lb_create_listener_creation_failed(self, mock_sleep):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        listener_obj.id = 'LISTENER_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, False]
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool)
        self.assertFalse(status)
        msg = _('Failed in creating listener (%s).') % 'LISTENER_ID'
        self.assertEqual(msg, res)
        self.nc.loadbalancer_create.assert_called_once_with(
            self.vip['subnet'], self.vip['address'],
            self.vip['admin_state_up'])
        self.nc.listener_create.assert_called_once_with(
            'LB_ID', self.vip['protocol'], self.vip['protocol_port'],
            self.vip['connection_limit'], self.vip['admin_state_up'])
        self.lb_driver._wait_for_lb_ready.assert_called_with('LB_ID')
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID', listener='LISTENER_ID')

    def test_lb_create_pool_creation_failed(self):
        lb_obj = mock.Mock()
        listener_obj = mock.Mock()
        pool_obj = mock.Mock()
        lb_obj.id = 'LB_ID'
        listener_obj.id = 'LISTENER_ID'
        pool_obj.id = 'POOL_ID'

        self.lb_driver._wait_for_lb_ready = mock.Mock()
        self.lb_driver._wait_for_lb_ready.side_effect = [True, True, False]
        self.nc.loadbalancer_create.return_value = lb_obj
        self.nc.listener_create.return_value = listener_obj
        self.nc.pool_create.return_value = pool_obj
        self.lb_driver.lb_delete = mock.Mock()

        status, res = self.lb_driver.lb_create(self.vip, self.pool)
        self.assertFalse(status)
        msg = _('Failed in creating pool (%s).') % 'POOL_ID'
        self.assertEqual(msg, res)
        self.nc.loadbalancer_create.assert_called_once_with(
            self.vip['subnet'], self.vip['address'],
            self.vip['admin_state_up'])
        self.nc.listener_create.assert_called_once_with(
            'LB_ID', self.vip['protocol'], self.vip['protocol_port'],
            self.vip['connection_limit'], self.vip['admin_state_up'])
        self.nc.pool_create.assert_called_once_with(
            self.pool['lb_method'], 'LISTENER_ID', self.pool['protocol'],
            self.pool['admin_state_up'])
        self.lb_driver._wait_for_lb_ready.assert_called_with('LB_ID')
        self.lb_driver.lb_delete.assert_called_once_with(
            loadbalancer='LB_ID', listener='LISTENER_ID', pool='POOL_ID')

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
