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
from oslo_utils import uuidutils

from senlin.drivers.os import neutron_v2
from senlin.drivers import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNeutronV2Driver(base.SenlinTestCase):

    def setUp(self):
        super(TestNeutronV2Driver, self).setUp()
        self.context = utils.dummy_context()
        self.conn_params = self.context.to_dict()
        self.conn = mock.Mock()
        with mock.patch.object(sdk, 'create_connection') as mock_creare_conn:
            mock_creare_conn.return_value = self.conn
            self.nc = neutron_v2.NeutronClient(self.context)

    @mock.patch.object(sdk, 'create_connection')
    def test_init(self, mock_create_connection):
        params = self.conn_params
        neutron_v2.NeutronClient(params)
        mock_create_connection.assert_called_once_with(params)

    def test_network_get_with_uuid(self):
        net_id = uuidutils.generate_uuid()
        network_obj = mock.Mock()

        self.conn.network.find_network.return_value = network_obj
        res = self.nc.network_get(net_id)
        self.conn.network.find_network.assert_called_once_with(net_id, False)
        self.assertEqual(network_obj, res)

    def test_network_get_with_name(self):
        net_id = 'network_identifier'
        net1 = mock.Mock()
        net2 = mock.Mock()
        self.conn.network.networks.return_value = [net1, net2]

        res = self.nc.network_get(net_id)
        self.assertEqual(0, self.conn.network.find_network.call_count)
        self.conn.network.networks.assert_called_once_with(name=net_id)
        self.assertEqual(net1, res)

    def test_port_find(self):
        port_id = 'port_identifier'
        port_obj = mock.Mock()

        self.conn.network.find_port.return_value = port_obj
        res = self.nc.port_find(port_id)
        self.conn.network.find_port.assert_called_once_with(port_id, False)
        self.assertEqual(port_obj, res)

    def test_security_group_find(self):
        sg_id = 'sg_identifier'
        sg_obj = mock.Mock()

        self.conn.network.find_security_group.return_value = sg_obj
        res = self.nc.security_group_find(sg_id)
        self.conn.network.find_security_group.assert_called_once_with(
            sg_id, False)
        self.assertEqual(sg_obj, res)

    def test_subnet_get(self):
        subnet_id = 'subnet_identifier'
        subnet_obj = mock.Mock()

        self.conn.network.find_subnet.return_value = subnet_obj
        res = self.nc.subnet_get(subnet_id)
        self.conn.network.find_subnet.assert_called_once_with(subnet_id, False)
        self.assertEqual(subnet_obj, res)

    def test_port_create(self):
        port_attr = {
            'network_id': 'foo'
        }
        self.nc.port_create(**port_attr)
        self.conn.network.create_port.assert_called_once_with(
            network_id='foo')

    def test_port_delete(self):
        self.nc.port_delete(port='foo')
        self.conn.network.delete_port.assert_called_once_with(
            port='foo', ignore_missing=True)

    def test_port_update(self):
        attr = {
            'name': 'new_name'
        }
        self.nc.port_update('fake_port', **attr)
        self.conn.network.update_port.assert_called_once_with(
            'fake_port', **attr)

    def test_floatingip_find(self):
        floatingip_id = 'fake_id'
        fip_obj = mock.Mock()

        self.conn.network.find_ip.return_value = fip_obj
        res = self.nc.floatingip_find(floatingip_id)
        self.conn.network.find_ip.assert_called_once_with(
            floatingip_id, ignore_missing=False)
        self.assertEqual(fip_obj, res)

    def test_floatingip_list_by_port_id(self):
        port_id = 'port_id'
        fip_obj_iter = iter([mock.Mock()])

        self.conn.network.ips.return_value = fip_obj_iter
        res = self.nc.floatingip_list(port=port_id)
        self.conn.network.ips.assert_called_once_with(port_id=port_id)
        self.assertEqual(1, len(res))

    def test_floatingip_create(self):
        attr = {
            'network_id': 'foo'
        }
        self.nc.floatingip_create(**attr)
        self.conn.network.create_ip.assert_called_once_with(
            network_id='foo')

    def test_floatingip_delete(self):
        self.nc.floatingip_delete(floating_ip='foo')
        self.conn.network.delete_ip.assert_called_once_with(
            'foo', ignore_missing=True)

    def test_floatingip_update(self):
        attr = {
            'port_id': 'fake_port'
        }
        self.nc.floatingip_update('fake_floatingip', **attr)
        self.conn.network.update_ip.assert_called_once_with(
            'fake_floatingip', **attr)
