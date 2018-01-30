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

import mock

from senlin.drivers.os import octavia_v2
from senlin.drivers import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestOctaviaV2Driver(base.SenlinTestCase):

    def setUp(self):
        super(TestOctaviaV2Driver, self).setUp()
        self.context = utils.dummy_context()
        self.conn_params = self.context.to_dict()
        self.conn = mock.Mock()
        with mock.patch.object(sdk, 'create_connection') as mock_creare_conn:
            mock_creare_conn.return_value = self.conn
            self.oc = octavia_v2.OctaviaClient(self.context)

    @mock.patch.object(sdk, 'create_connection')
    def test_init(self, mock_create_connection):
        params = self.conn_params
        octavia_v2.OctaviaClient(params)
        mock_create_connection.assert_called_once_with(params)

    def test_loadbalancer_get(self):
        lb_id = 'loadbalancer_identifier'
        loadbalancer_obj = mock.Mock()

        self.conn.load_balancer.find_load_balancer.return_value =\
            loadbalancer_obj
        res = self.oc.loadbalancer_get(lb_id)
        self.conn.load_balancer.find_load_balancer.assert_called_once_with(
            lb_id, False)
        self.assertEqual(loadbalancer_obj, res)

    def test_loadbalancer_create(self):
        vip_subnet_id = 'ID1'
        lb_obj = mock.Mock()

        # All input parameters are provided
        kwargs = {
            'vip_address': '192.168.0.100',
            'name': 'test-loadbalancer',
            'description': 'This is a loadbalancer',
            'admin_state_up': True
        }

        self.conn.load_balancer.create_load_balancer.return_value = lb_obj
        self.assertEqual(lb_obj, self.oc.loadbalancer_create(vip_subnet_id,
                                                             **kwargs))
        self.conn.load_balancer.create_load_balancer.assert_called_once_with(
            vip_subnet_id=vip_subnet_id, **kwargs)

        # Use default input parameters
        kwargs = {
            'admin_state_up': True
        }
        self.assertEqual(lb_obj, self.oc.loadbalancer_create(vip_subnet_id))
        self.conn.load_balancer.create_load_balancer.assert_called_with(
            vip_subnet_id=vip_subnet_id, **kwargs)

    def test_loadbalancer_delete(self):
        lb_id = 'ID1'

        self.oc.loadbalancer_delete(lb_id, ignore_missing=False)
        self.conn.load_balancer.delete_load_balancer.assert_called_once_with(
            lb_id, ignore_missing=False)

        self.oc.loadbalancer_delete(lb_id)
        self.conn.load_balancer.delete_load_balancer.assert_called_with(
            lb_id, ignore_missing=True)

    def test_listener_create(self):
        loadbalancer_id = 'ID1'
        protocol = 'HTTP'
        protocol_port = 80
        listener_obj = mock.Mock()

        # All input parameters are provided
        kwargs = {
            'connection_limit': 100,
            'admin_state_up': True,
            'name': 'test-listener',
            'description': 'This is a listener',
        }

        self.conn.load_balancer.create_listener.return_value = listener_obj
        self.assertEqual(listener_obj, self.oc.listener_create(
            loadbalancer_id, protocol, protocol_port, **kwargs))
        self.conn.load_balancer.create_listener.assert_called_once_with(
            loadbalancer_id=loadbalancer_id, protocol=protocol,
            protocol_port=protocol_port, **kwargs)

        # Use default input parameters
        kwargs = {
            'admin_state_up': True
        }
        self.assertEqual(listener_obj, self.oc.listener_create(
            loadbalancer_id, protocol, protocol_port))
        self.conn.load_balancer.create_listener.assert_called_with(
            loadbalancer_id=loadbalancer_id, protocol=protocol,
            protocol_port=protocol_port, **kwargs)

    def test_listener_delete(self):
        listener_id = 'ID1'

        self.oc.listener_delete(listener_id, ignore_missing=False)
        self.conn.load_balancer.delete_listener.assert_called_once_with(
            listener_id, ignore_missing=False)

        self.oc.listener_delete(listener_id)
        self.conn.load_balancer.delete_listener.assert_called_with(
            listener_id, ignore_missing=True)

    def test_pool_create(self):
        lb_algorithm = 'ROUND_ROBIN'
        listener_id = 'ID1'
        protocol = 'HTTP'
        pool_obj = mock.Mock()

        # All input parameters are provided
        kwargs = {
            'admin_state_up': True,
            'name': 'test-pool',
            'description': 'This is a pool',
        }

        self.conn.load_balancer.create_pool.return_value = pool_obj
        self.assertEqual(pool_obj, self.oc.pool_create(
            lb_algorithm, listener_id, protocol, **kwargs))
        self.conn.load_balancer.create_pool.assert_called_once_with(
            lb_algorithm=lb_algorithm, listener_id=listener_id,
            protocol=protocol, **kwargs)

        # Use default input parameters
        kwargs = {
            'admin_state_up': True
        }
        self.assertEqual(pool_obj, self.oc.pool_create(
            lb_algorithm, listener_id, protocol))
        self.conn.load_balancer.create_pool.assert_called_with(
            lb_algorithm=lb_algorithm, listener_id=listener_id,
            protocol=protocol, **kwargs)

    def test_pool_delete(self):
        pool_id = 'ID1'

        self.oc.pool_delete(pool_id, ignore_missing=False)
        self.conn.load_balancer.delete_pool.assert_called_once_with(
            pool_id, ignore_missing=False)

        self.oc.pool_delete(pool_id)
        self.conn.load_balancer.delete_pool.assert_called_with(
            pool_id, ignore_missing=True)

    def test_pool_member_create(self):
        pool_id = 'ID1'
        address = '192.168.1.100'
        protocol_port = 80
        subnet_id = 'ID2'
        weight = 50
        member_obj = mock.Mock()

        # All input parameters are provided
        kwargs = {
            'weight': weight,
            'admin_state_up': True,
        }

        self.conn.load_balancer.create_member.return_value = member_obj
        self.assertEqual(member_obj, self.oc.pool_member_create(
            pool_id, address, protocol_port, subnet_id, **kwargs))
        self.conn.load_balancer.create_member.assert_called_once_with(
            pool_id, address=address, protocol_port=protocol_port,
            subnet_id=subnet_id, **kwargs)

        # Use default input parameters
        kwargs = {
            'admin_state_up': True
        }
        self.assertEqual(member_obj, self.oc.pool_member_create(
            pool_id, address, protocol_port, subnet_id))
        self.conn.load_balancer.create_member.assert_called_with(
            pool_id, address=address, protocol_port=protocol_port,
            subnet_id=subnet_id, **kwargs)

    def test_pool_member_delete(self):
        pool_id = 'ID1'
        member_id = 'ID2'

        self.oc.pool_member_delete(pool_id, member_id, ignore_missing=False)
        self.conn.load_balancer.delete_member.assert_called_once_with(
            member_id, pool_id, ignore_missing=False)

        self.oc.pool_member_delete(pool_id, member_id)
        self.conn.load_balancer.delete_member.assert_called_with(
            member_id, pool_id, ignore_missing=True)

    def test_healthmonitor_create(self):
        hm_type = 'HTTP'
        delay = 30
        timeout = 10
        max_retries = 5
        pool_id = 'ID1'
        hm_obj = mock.Mock()

        # All input parameters are provided
        kwargs = {
            'http_method': 'test-method',
            'admin_state_up': True,
            'url_path': '/test_page',
            'expected_codes': [200, 201, 202],
        }

        self.conn.load_balancer.create_health_monitor.return_value = hm_obj
        res = self.oc.healthmonitor_create(hm_type, delay, timeout,
                                           max_retries, pool_id, **kwargs)
        self.assertEqual(hm_obj, res)
        self.conn.load_balancer.create_health_monitor.assert_called_once_with(
            type=hm_type, delay=delay, timeout=timeout,
            max_retries=max_retries, pool_id=pool_id, **kwargs)

        # Use default input parameters
        res = self.oc.healthmonitor_create(hm_type, delay, timeout,
                                           max_retries, pool_id,
                                           admin_state_up=True)
        self.assertEqual(hm_obj, res)
        self.conn.load_balancer.create_health_monitor.assert_called_with(
            type=hm_type, delay=delay, timeout=timeout,
            max_retries=max_retries, pool_id=pool_id,
            admin_state_up=True)

        # hm_type other than HTTP, then other params ignored
        res = self.oc.healthmonitor_create('TCP', delay, timeout,
                                           max_retries, pool_id, **kwargs)
        self.assertEqual(hm_obj, res)
        self.conn.load_balancer.create_health_monitor.assert_called_with(
            type='TCP', delay=delay, timeout=timeout,
            max_retries=max_retries, pool_id=pool_id,
            admin_state_up=True)

    def test_healthmonitor_delete(self):
        healthmonitor_id = 'ID1'

        self.oc.healthmonitor_delete(healthmonitor_id, ignore_missing=False)
        self.conn.load_balancer.delete_health_monitor.assert_called_once_with(
            healthmonitor_id, ignore_missing=False)

        self.oc.healthmonitor_delete(healthmonitor_id)
        self.conn.load_balancer.delete_health_monitor.assert_called_with(
            healthmonitor_id, ignore_missing=True)
