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
from oslo_config import cfg

from senlin.drivers.openstack import nova_v2
from senlin.drivers.openstack import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNovaV2(base.SenlinTestCase):

    def setUp(self):
        super(TestNovaV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.mock_conn = mock.Mock()
        self.mock_create = self.patchobject(
            sdk, 'create_connection',
            return_value=self.mock_conn)
        self.compute = self.mock_conn.compute

    def test_init(self):
        d = nova_v2.NovaClient(self.conn_params)
        self.mock_create.assert_called_once_with(self.conn_params)
        self.assertEqual(self.mock_conn, d.conn)

    def test_flavor_create(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.flavor_create(name='foo')
        self.compute.create_flavor.assert_called_once_with(name='foo')

    def test_flavor_get(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.flavor_get('foo')
        self.compute.get_flavor.assert_called_once_with('foo')

    def test_flavor_find(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.flavor_find('foo')
        self.compute.find_flavor.assert_called_once_with('foo', False)
        self.compute.find_flavor.reset_mock()

        d.flavor_find('foo', True)
        self.compute.find_flavor.assert_called_once_with('foo', True)
        self.compute.find_flavor.reset_mock()

        d.flavor_find('foo', False)
        self.compute.find_flavor.assert_called_once_with('foo', False)

    def test_flavor_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.flavor_list()
        self.compute.flavors.assert_called_once_with(True)
        self.compute.flavors.reset_mock()

        d.flavor_list(k='v')
        self.compute.flavors.assert_called_once_with(True, k='v')
        self.compute.flavors.reset_mock()

        d.flavor_list(False)
        self.compute.flavors.assert_called_once_with(False)
        self.compute.flavors.reset_mock()

        d.flavor_list(False, foo='bar')
        self.compute.flavors.assert_called_once_with(False, foo='bar')

    def test_flavor_update(self):
        d = nova_v2.NovaClient(self.conn_params)
        attrs = {'mem': 2}
        d.flavor_update('fakeid', **attrs)
        self.compute.update_flavor.assert_called_once_with('fakeid', **attrs)

    def test_flavor_delete(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.flavor_delete('foo', True)
        self.compute.delete_flavor.assert_called_once_with('foo', True)
        self.compute.delete_flavor.reset_mock()

        d.flavor_delete('foo', False)
        self.compute.delete_flavor.assert_called_once_with('foo', False)
        self.compute.delete_flavor.reset_mock()

        d.flavor_delete('foo')
        self.compute.delete_flavor.assert_called_once_with('foo', True)

    def test_image_get(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.image_get('foo')
        self.compute.get_image.assert_called_once_with('foo')

    def test_image_find(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.image_find('foo')
        self.compute.find_image.assert_called_once_with('foo', False)
        self.compute.find_image.reset_mock()

        d.image_find('foo', True)
        self.compute.find_image.assert_called_once_with('foo', True)
        self.compute.find_image.reset_mock()

        d.image_find('foo', False)
        self.compute.find_image.assert_called_once_with('foo', False)

    def test_image_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.image_list()
        self.compute.images.assert_called_once_with(True)
        self.compute.images.reset_mock()

        d.image_list(k='v')
        self.compute.images.assert_called_once_with(True, k='v')
        self.compute.images.reset_mock()

        d.image_list(False)
        self.compute.images.assert_called_once_with(False)
        self.compute.images.reset_mock()

        d.image_list(False, foo='bar')
        self.compute.images.assert_called_once_with(False, foo='bar')

    def test_image_delete(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.image_delete('foo', True)
        self.compute.delete_image.assert_called_once_with('foo', True)
        self.compute.delete_image.reset_mock()

        d.image_delete('foo', False)
        self.compute.delete_image.assert_called_once_with('foo', False)
        self.compute.delete_image.reset_mock()

        d.image_delete('foo')
        self.compute.delete_image.assert_called_once_with('foo', True)

    def test_keypair_create(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.keypair_create(name='foo')
        self.compute.create_keypair.assert_called_once_with(name='foo')

    def test_keypair_get(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.keypair_get('foo')
        self.compute.get_keypair.assert_called_once_with('foo')

    def test_keypair_get_by_name(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.keypair_get_by_name('foo')
        self.compute.find_keypair.assert_called_once_with('foo', False)
        self.compute.find_keypair.reset_mock()

        d.keypair_get_by_name('foo', True)
        self.compute.find_keypair.assert_called_once_with('foo', True)
        self.compute.find_keypair.reset_mock()

        d.keypair_get_by_name('foo', False)
        self.compute.find_keypair.assert_called_once_with('foo', False)

    def test_keypair_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.keypair_list()
        self.compute.keypairs.assert_called_once_with()
        self.compute.keypairs.reset_mock()

        d.keypair_list(k='v')
        self.compute.keypairs.assert_called_once_with(k='v')
        self.compute.keypairs.reset_mock()

    def test_keypair_update(self):
        d = nova_v2.NovaClient(self.conn_params)
        attrs = {'mem': 2}
        d.keypair_update('fakeid', **attrs)
        self.compute.update_keypair.assert_called_once_with('fakeid', **attrs)

    def test_keypair_delete(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.keypair_delete('foo', True)
        self.compute.delete_keypair.assert_called_once_with('foo', True)
        self.compute.delete_keypair.reset_mock()

        d.keypair_delete('foo', False)
        self.compute.delete_keypair.assert_called_once_with('foo', False)
        self.compute.delete_keypair.reset_mock()

        d.keypair_delete('foo')
        self.compute.delete_keypair.assert_called_once_with('foo', True)

    def test_server_create(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_create(name='foo')
        self.compute.create_server.assert_called_once_with(name='foo')

    def test_wait_for_server(self):
        self.compute.find_server.return_value = 'foo'

        d = nova_v2.NovaClient(self.conn_params)
        d.wait_for_server('foo', 'STATUS1', ['STATUS2'], 5, 10)
        self.compute.wait_for_server.assert_called_once_with(
            'foo', status='STATUS1', failures=['STATUS2'], interval=5, wait=10)

    def test_wait_for_server_default_value(self):
        self.compute.find_server.return_value = 'foo'

        d = nova_v2.NovaClient(self.conn_params)
        d.wait_for_server('foo', timeout=10)
        self.compute.wait_for_server.assert_called_once_with(
            'foo', status='ACTIVE', failures=['ERROR'], interval=2, wait=10)

    def test_wait_for_server_with_default_timeout(self):
        self.compute.find_server.return_value = 'foo'
        timeout = cfg.CONF.default_action_timeout

        d = nova_v2.NovaClient(self.conn_params)
        d.wait_for_server('foo')
        self.compute.wait_for_server.assert_called_once_with(
            'foo', status='ACTIVE', failures=['ERROR'], interval=2,
            wait=timeout)

    def test_server_get(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_get('foo')
        self.compute.get_server.assert_called_once_with('foo')

    def test_server_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_list()
        self.compute.servers.assert_called_once_with(True)
        self.compute.servers.reset_mock()

        d.server_list(k='v')
        self.compute.servers.assert_called_once_with(True, k='v')
        self.compute.servers.reset_mock()

        d.server_list(False)
        self.compute.servers.assert_called_once_with(False)
        self.compute.servers.reset_mock()

        d.server_list(False, k='v')
        self.compute.servers.assert_called_once_with(False, k='v')

    def test_server_update(self):
        d = nova_v2.NovaClient(self.conn_params)
        attrs = {'mem': 2}
        d.server_update('fakeid', **attrs)
        self.compute.update_server.assert_called_once_with('fakeid', **attrs)

    def test_server_delete(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_delete('foo', True)
        self.compute.delete_server.assert_called_once_with('foo', True)

    def test_server_rebuild(self):
        d = nova_v2.NovaClient(self.conn_params)
        attrs = {
            'personality': '123',
            'metadata': {'k1': 'v1'}
        }
        d.server_rebuild('fakeid', 'new_image', 'new_name', 'new_pass',
                         **attrs)
        self.compute.rebuild_server.assert_called_once_with(
            'fakeid', 'new_image', name='new_name',
            admin_password='new_pass', **attrs)

    def test_server_resize(self):
        d = nova_v2.NovaClient(self.conn_params)

        res = d.server_resize('fakeid', 'new_flavor')

        self.assertEqual(d.conn.compute.resize_server.return_value, res)
        d.conn.compute.resize_server.assert_called_once_with(
            'fakeid', 'new_flavor')

    def test_server_resize_confirm(self):
        d = nova_v2.NovaClient(self.conn_params)

        res = d.server_resize_confirm('fakeid')

        self.assertEqual(d.conn.compute.confirm_resize_server.return_value,
                         res)
        d.conn.compute.confirm_resize_server.assert_called_once_with('fakeid')

    def test_server_resize_revert(self):
        d = nova_v2.NovaClient(self.conn_params)

        res = d.server_resize_revert('fakeid')

        self.assertEqual(d.conn.compute.revert_resize_server.return_value, res)
        d.conn.compute.revert_resize_server.assert_called_once_with('fakeid')

    def test_wait_for_server_delete(self):
        self.compute.find_server.return_value = 'FOO'

        d = nova_v2.NovaClient(self.conn_params)
        d.wait_for_server_delete('foo', 120)
        self.compute.find_server.assert_called_once_with('foo', True)
        self.compute.wait_for_delete.assert_called_once_with('FOO', wait=120)

    def test_wait_for_server_delete_with_default_timeout(self):
        cfg.CONF.set_override('default_action_timeout', 360, enforce_type=True)
        self.compute.find_server.return_value = 'FOO'

        d = nova_v2.NovaClient(self.conn_params)
        d.wait_for_server_delete('foo')
        self.compute.find_server.assert_called_once_with('foo', True)
        self.compute.wait_for_delete.assert_called_once_with('FOO', wait=360)

    def test_wait_for_server_delete_server_doesnt_exist(self):
        self.compute.find_server.return_value = None

        d = nova_v2.NovaClient(self.conn_params)
        res = d.wait_for_server_delete('foo')
        self.assertIsNone(res)

    def test_server_interface_create(self):
        server = mock.Mock()
        d = nova_v2.NovaClient(self.conn_params)
        d.server_interface_create(server, name='foo')
        self.compute.create_server_interface.assert_called_once_with(
            server, name='foo')

    def test_server_interface_get(self):
        server = mock.Mock()
        d = nova_v2.NovaClient(self.conn_params)
        d.server_interface_get(server, 'foo')
        self.compute.get_server_interface.assert_called_once_with(server,
                                                                  'foo')

    def test_server_interface_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        server = mock.Mock()
        d.server_interface_list(server)
        self.compute.server_interfaces.assert_called_once_with(server)
        self.compute.server_interfaces.reset_mock()

        d.server_interface_list(server, k='v')
        self.compute.server_interfaces.assert_called_once_with(server, k='v')
        self.compute.server_interfaces.reset_mock()

    def test_server_interface_delete(self):
        server = mock.Mock()
        d = nova_v2.NovaClient(self.conn_params)
        d.server_interface_delete('foo', server, True)
        self.compute.delete_server_interface.assert_called_once_with(
            'foo', server, True)
        self.compute.delete_server_interface.reset_mock()

        d.server_interface_delete('foo', server, False)
        self.compute.delete_server_interface.assert_called_once_with(
            'foo', server, False)
        self.compute.delete_server_interface.reset_mock()

        d.server_interface_delete('foo', server)
        self.compute.delete_server_interface.assert_called_once_with(
            'foo', server, True)

    def test_server_ip_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_ip_list()
        self.compute.server_ips.assert_called_once_with()
        self.compute.server_ips.reset_mock()

        d.server_ip_list(k='v')
        self.compute.server_ips.assert_called_once_with(k='v')

    def test_server_metadata_create(self):
        server = mock.Mock()
        d = nova_v2.NovaClient(self.conn_params)
        d.server_metadata_create(server, {'k1': 'v1'})
        self.compute.set_server_metadata.assert_called_once_with(
            server, k1='v1')

    def test_server_metadata_get(self):
        server = mock.Mock()
        res_server = mock.Mock()
        res_server.metadata = {
            'k1': 'v1'
        }
        self.compute.get_server_metadata.return_value = res_server

        d = nova_v2.NovaClient(self.conn_params)
        res = d.server_metadata_get(server)
        self.compute.get_server_metadata.assert_called_once_with(server)
        self.assertEqual({'k1': 'v1'}, res)

    def test_server_metadata_update(self):
        server = mock.Mock()
        res_server = mock.Mock()
        res_server.metadata = {
            'k1': 'v1'
        }
        self.compute.get_server_metadata.return_value = res_server

        d = nova_v2.NovaClient(self.conn_params)
        d.server_metadata_update(server, {'k2': 'v2'})
        self.compute.delete_server_metadata.assert_called_once_with(
            server, ['k1'])
        self.compute.set_server_metadata.assert_called_once_with(
            server, k2='v2')

    def test_server_metadata_delete(self):
        server = mock.Mock()
        d = nova_v2.NovaClient(self.conn_params)
        d.server_metadata_delete(server, 'k1')
        self.compute.delete_server_metadata.assert_called_once_with(
            server, 'k1')

    def test_validate_azs(self):
        nc = nova_v2.NovaClient(self.conn_params)

        fake_azs = [
            {'zoneState': {'available': 1}, 'zoneName': 'AZ1'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ2'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ3'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ4'}
        ]

        self.patchobject(nc, 'availability_zone_list', return_value=fake_azs)

        result = nc.validate_azs(['AZ1', 'AZ2', 'AZ5'])
        self.assertEqual(['AZ1', 'AZ2'], result)

    def test_server_group_create(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_group_create(name='sg')
        self.compute.create_server_group.assert_called_once_with(name='sg')

    def test_server_group_delete(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_group_delete('sg', True)
        self.compute.delete_server_group.assert_called_once_with(
            'sg', ignore_missing=True)
        self.compute.delete_server_group.reset_mock()

        d.server_group_delete('sg', False)
        self.compute.delete_server_group.assert_called_once_with(
            'sg', ignore_missing=False)
        self.compute.delete_server_group.reset_mock()

        d.server_group_delete('sg')
        self.compute.delete_server_group.assert_called_once_with(
            'sg', ignore_missing=True)

    def test_server_group_find(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_group_find('sg')
        self.compute.find_server_group.assert_called_once_with(
            'sg', ignore_missing=True)
        self.compute.find_server_group.reset_mock()

        d.server_group_find('sg', True)
        self.compute.find_server_group.assert_called_once_with(
            'sg', ignore_missing=True)
        self.compute.find_server_group.reset_mock()

        d.server_group_find('sg', False)
        self.compute.find_server_group.assert_called_once_with(
            'sg', ignore_missing=False)

    def test_server_group_get(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_group_get('sg')
        self.compute.get_server_group.assert_called_once_with('sg')

    def test_server_group_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.server_group_list()
        self.compute.server_groups.assert_called_once_with()
        self.compute.server_groups.reset_mock()

        d.server_group_list(name='sg')
        self.compute.server_groups.assert_called_once_with(name='sg')
        self.compute.server_groups.reset_mock()

    def test_hypervisor_list(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.hypervisor_list()
        self.compute.hypervisors.assert_called_once_with()
        self.compute.hypervisors.reset_mock()

        d.hypervisor_list(k='v')
        self.compute.hypervisors.assert_called_once_with(k='v')
        self.compute.hypervisors.reset_mock()

    def test_hypervisor_find(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.hypervisor_find('k')
        self.compute.find_hypervisor.assert_called_once_with(
            'k', ignore_missing=True)
        self.compute.find_hypervisor.reset_mock()

        d.hypervisor_find('k', True)
        self.compute.find_hypervisor.assert_called_once_with(
            'k', ignore_missing=True)
        self.compute.find_hypervisor.reset_mock()

        d.hypervisor_find('k', False)
        self.compute.find_hypervisor.assert_called_once_with(
            'k', ignore_missing=False)

    def test_hypervisor_get(self):
        d = nova_v2.NovaClient(self.conn_params)
        d.hypervisor_get('k')
        self.compute.get_hypervisor.assert_called_once_with('k')
