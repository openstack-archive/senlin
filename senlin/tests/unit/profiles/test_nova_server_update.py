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

import copy

import mock
import six

from senlin.common import exception as exc
from senlin.profiles import base as profiles_base
from senlin.profiles.os.nova import server
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNovaServerUpdate(base.SenlinTestCase):
    def setUp(self):
        super(TestNovaServerUpdate, self).setUp()

        self.context = utils.dummy_context()
        self.spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'context': {},
                'adminPass': 'adminpass',
                'auto_disk_config': True,
                'availability_zone': 'FAKE_AZ',
                'block_device_mapping': [{
                    'device_name': 'FAKE_NAME',
                    'volume_size': 1000,
                }],
                'config_drive': False,
                'flavor': 'FLAV',
                'image': 'FAKE_IMAGE',
                'key_name': 'FAKE_KEYNAME',
                "metadata": {"meta var": "meta val"},
                'name': 'FAKE_SERVER_NAME',
                'networks': [{
                    'port': 'FAKE_PORT',
                    'fixed-ip': 'FAKE_IP',
                    'network': 'FAKE_NET',
                }],
                'personality': [{
                    'path': '/etc/motd',
                    'contents': 'foo',
                }],
                'scheduler_hints': {
                    'same_host': 'HOST_ID',
                },
                'security_groups': ['HIGH_SECURITY_GROUP'],
                'user_data': 'FAKE_USER_DATA',
            }
        }

    def test__update_name(self):
        obj = mock.Mock(physical_id='PHY_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['name'] = 'TEST_SERVER'
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_name(obj, new_profile)

        self.assertIsNone(res)
        cc.server_update.assert_called_once_with('PHY_ID', name='TEST_SERVER')

    def test__update_name_to_None(self):
        obj = mock.Mock(physical_id='PHY_ID')
        obj.name = 'NODE_NAME'
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        del new_spec['properties']['name']
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_name(obj, new_profile)

        self.assertIsNone(res)
        cc.server_update.assert_called_once_with('PHY_ID', name='NODE_NAME')

    def test__update_name_no_change(self):
        obj = mock.Mock(physical_id='PHY_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_name(obj, new_profile)

        self.assertIsNone(res)
        self.assertEqual(0, cc.server_update.call_count)

    def test__update_name_nova_failure(self):
        obj = mock.Mock(physical_id='PHY_ID')
        obj.name = 'NODE_NAME'
        cc = mock.Mock()
        cc.server_update.side_effect = exc.InternalError(message='BOOM')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['name'] = 'TEST_SERVER'
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_name,
                               obj, new_profile)

        self.assertEqual('Failed in updating server PHY_ID: BOOM.',
                         six.text_type(ex))
        cc.server_update.assert_called_once_with('PHY_ID', name='TEST_SERVER')

    def test__update_metadata(self):
        obj = mock.Mock(id='NODE_ID', physical_id='NOVA_ID',
                        cluster_id='CLUSTER_ID', index=456)
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['metadata'] = {'new_key': 'new_value'}
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_metadata(obj, new_profile)

        self.assertIsNone(res)
        cc.server_metadata_update.assert_called_once_with(
            'NOVA_ID',
            {
                'new_key': 'new_value',
                'cluster_node_id': 'NODE_ID',
                'cluster_id': 'CLUSTER_ID',
                'cluster_node_index': '456',
            }
        )

    def test___update_metadata_no_change(self):
        obj = mock.Mock(id='NODE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_metadata(obj, new_profile)

        self.assertIsNone(res)
        self.assertEqual(0, cc.server_metadata_update.call_count)

    def test__update_metadata_nova_failure(self):
        obj = mock.Mock(id='NODE_ID', physical_id='NOVA_ID', cluster_id='')
        err = exc.InternalError(code=500, message='Nova Error')
        cc = mock.Mock()
        cc.server_metadata_update.side_effect = err
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        # new profile with new metadata
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['metadata'] = {'fooa': 'baaar'}
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_metadata,
                               obj, new_profile)

        self.assertEqual('Failed in updating server NOVA_ID: Nova Error.',
                         six.text_type(ex))
        cc.server_metadata_update.assert_called_once_with(
            'NOVA_ID', {'fooa': 'baaar', 'cluster_node_id': 'NODE_ID'}
        )

    def test__update_flavor(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        profile._update_flavor(obj, 'old_flavor', 'new_flavor')

        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update')
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_confirm.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.has_calls([
            mock.call('NOVA_ID', 'VERIFY_RESIZE'),
            mock.call('NOVA_ID', 'ACTIVE')])

    def test__update_flavor_failed_validation(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        err = exc.EResourceUpdate(type='server', id='NOVA_ID', message='BOOM')
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=err)

        self.assertRaises(exc.EResourceUpdate,
                          profile._update_flavor,
                          obj, 'old_flavor', 'new_flavor')

        mock_validate.assert_called_once_with(obj, 'old_flavor', 'update')

    def test__update_flavor_failed_validation_2(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        result = [
            mock.Mock(),
            exc.EResourceUpdate(type='server', id='NOVA_ID', message='BOOM')
        ]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=result)

        self.assertRaises(exc.EResourceUpdate,
                          profile._update_flavor,
                          obj, 'old_flavor', 'new_flavor')

        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])

    def test__update_flavor_same(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id=123), mock.Mock(id=123)]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        res = profile._update_flavor(obj, 'old_flavor', 'new_flavor')

        self.assertIsNone(res)
        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        self.assertEqual(0, cc.server_resize.call_count)

    def test__update_flavor_resize_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        cc.server_resize.side_effect = [
            exc.InternalError(code=500, message='Resize failed')]
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, 'old_flavor', 'new_flavor')

        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_revert.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'ACTIVE')
        self.assertEqual('Failed in updating server NOVA_ID: Resize failed.',
                         six.text_type(ex))

    def test__update_flavor_first_wait_for_server_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        cc.wait_for_server.side_effect = [
            exc.InternalError(code=500, message='TIMEOUT'),
            None
        ]

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)
        # do it
        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, 'old_flavor', 'new_flavor')

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.wait_for_server.has_calls([
            mock.call('NOVA_ID', 'VERIFY_RESIZE'),
            mock.call('NOVA_ID', 'ACTIVE')])
        cc.server_resize_revert.assert_called_once_with('NOVA_ID')
        self.assertEqual('Failed in updating server NOVA_ID: TIMEOUT.',
                         six.text_type(ex))

    def test__update_flavor_resize_failed_revert_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        err_resize = exc.InternalError(code=500, message='Resize')
        cc.server_resize.side_effect = err_resize
        err_revert = exc.InternalError(code=500, message='Revert')
        cc.server_resize_revert.side_effect = err_revert
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        # do it
        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, 'old_flavor', 'new_flavor')

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_revert.assert_called_once_with('NOVA_ID')
        # the wait_for_server wasn't called
        self.assertEqual(0, cc.wait_for_server.call_count)
        self.assertEqual('Failed in updating server NOVA_ID: Revert.',
                         six.text_type(ex))

    def test__update_flavor_confirm_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        err_confirm = exc.InternalError(code=500, message='Confirm')
        cc.server_resize_confirm.side_effect = err_confirm
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        # do it
        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, 'old_flavor', 'new_flavor')

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_confirm.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'VERIFY_RESIZE')
        self.assertEqual('Failed in updating server NOVA_ID: Confirm.',
                         six.text_type(ex))

    def test__update_flavor_wait_confirm_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        err_wait = exc.InternalError(code=500, message='Wait')
        cc.wait_for_server.side_effect = [None, err_wait]
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        # do it
        ex = self.assertRaises(exc.InternalError,
                               profile._update_flavor,
                               obj, 'old_flavor', 'new_flavor')

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'old_flavor', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_confirm.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.assert_has_calls([
            mock.call('NOVA_ID', 'VERIFY_RESIZE'),
            mock.call('NOVA_ID', 'ACTIVE')
        ])
        self.assertEqual('Failed in updating server NOVA_ID: Wait.',
                         six.text_type(ex))

    def test__update_image(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        mock_old_image = mock.Mock(id='123')
        mock_new_image = mock.Mock(id='456')
        cc = mock.Mock()
        cc.image_find.side_effect = [mock_old_image, mock_new_image]

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._update_image(obj, 'old_image', 'new_image', 'adminpass')
        cc.image_find.has_calls([
            mock.call('old_image'), mock.call('new_image')
        ])
        cc.server_rebuild.assert_called_once_with('FAKE_ID', '456',
                                                  'FAKE_SERVER_NAME',
                                                  'adminpass')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test__update_image_old_image_is_none(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        cc = mock.Mock()
        mock_server = mock.Mock()
        mock_server.image = {
            'id': '123',
            'link': {
                'href': 'http://openstack.example.com/openstack/images/123',
                'rel': 'bookmark'
            }
        }
        cc.server_get.return_value = mock_server
        mock_image = mock.Mock(id='456')
        cc.image_find.return_value = mock_image

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._update_image(obj, None, 'new_image', 'adminpass')
        cc.image_find.assert_called_once_with('new_image')
        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.server_rebuild.assert_called_once_with('FAKE_ID', '456',
                                                  'FAKE_SERVER_NAME',
                                                  'adminpass')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test__update_image_new_image_is_none(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        cc = mock.Mock()
        mock_image = mock.Mock(id='123')
        cc.image_find.return_value = mock_image

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        ex = self.assertRaises(exc.InternalError,
                               profile._update_image,
                               obj, 'old_image', None, 'adminpass')
        msg = ("Updating Nova server with image set to None is not "
               "supported by Nova.")
        self.assertEqual(msg, six.text_type(ex))
        cc.image_find.assert_called_once_with('old_image')

    def test__update_network(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        cc = mock.Mock()
        nc = mock.Mock()
        server_obj = mock.Mock()
        net1 = mock.Mock(id='net1')
        net2 = mock.Mock(id='net2')
        existing_ports = [
            {
                'port_id': 'port1',
                'net_id': 'net1',
                'fixed_ips': [{'subnet_id': 'subnet1', 'ip_address': 'ip1'}]
            },
            {
                'port_id': 'port2',
                'net_id': 'net1',
                'fixed_ips': [{'subnet_id': 'subnet1',
                               'ip_address': 'ip-random2'}]
            },
            {
                'port_id': 'port3',
                'net_id': 'net2',
                'fixed_ips': [{'subnet_id': 'subnet2', 'ip_address': 'ip3'}]
            },
        ]
        deleted_networks = [
            {'fixed-ip': 'ip1', 'network': 'net1', 'port': None},
            {'fixed-ip': None, 'network': 'net1', 'port': None},
            {'fixed-ip': None, 'network': None, 'port': 'port3'}
        ]
        created_networks = [
            {'fixed-ip': 'ip2', 'network': 'net1', 'port': None},
            {'fixed-ip': None, 'network': 'net2', 'port': None},
            {'fixed-ip': None, 'network': None, 'port': 'port4'}
        ]
        cc.server_get.return_value = server_obj
        cc.server_interface_list.return_value = existing_ports
        nc.network_get.side_effect = [net1, net1, net1, net2]

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc
        profile._update_network(obj, created_networks, deleted_networks)
        calls = [mock.call('port1', server_obj),
                 mock.call('port3', server_obj),
                 mock.call('port2', server_obj)]
        cc.server_interface_delete.assert_has_calls(calls)
        calls = [
            mock.call(
                server_obj, net_id='net1', fixed_ips=[{'ip_address': 'ip2'}]),
            mock.call(server_obj, net_id='net2'),
            mock.call(server_obj, port_id='port4'),
        ]
        cc.server_interface_create.assert_has_calls(calls)

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_image')
    def test_do_update_image_succeeded(self, mock_update_image,
                                       mock_update_flavor):
        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'FAKE_IMAGE_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_image.assert_called_with(obj, 'FAKE_IMAGE',
                                             'FAKE_IMAGE_NEW',
                                             'adminpass')

    # TODO(Yanyan Hu): remove this mock after admin_pass update
    # is completely supported.
    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(profiles_base.Profile, 'validate_for_update')
    @mock.patch.object(server.ServerProfile, '_update_image')
    def test_do_update_image_with_passwd(self, mock_update_image,
                                         mock_validate, mock_update_flavor):
        obj = mock.Mock(physical_id='FAKE_ID')
        mock_validate.return_value = True
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'FAKE_IMAGE_NEW'
        new_spec['properties']['adminPass'] = 'adminpass2'
        new_profile = server.ServerProfile('t', new_spec)
        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_image.assert_called_with(obj, 'FAKE_IMAGE',
                                             'FAKE_IMAGE_NEW',
                                             'adminpass2')

        del new_spec['properties']['adminPass']
        new_profile = server.ServerProfile('t', new_spec)
        self.assertIsNone(new_profile.properties['adminPass'])
        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_image.assert_called_with(obj, 'FAKE_IMAGE',
                                             'FAKE_IMAGE_NEW',
                                             'adminpass')

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_update_metadata')
    @mock.patch.object(server.ServerProfile, '_update_image')
    def test_do_update_image_failed(self, mock_update_image, mock_update_meta,
                                    mock_update_name, mock_update_flavor):
        ex = exc.InternalError(code=404, message='Image Not Found')
        mock_update_image.side_effect = ex
        obj = mock.Mock(physical_id='FAKE_ID')

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'FAKE_IMAGE_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               obj, new_profile)

        mock_update_image.assert_called_with(
            obj, 'FAKE_IMAGE', 'FAKE_IMAGE_NEW', 'adminpass')
        self.assertEqual('Failed in updating server FAKE_ID: Image Not Found.',
                         six.text_type(ex))

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    def test_do_update_update_flavor_succeeded(self, mock_update_flavor):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'FAKE_FLAVOR_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_flavor.assert_called_with(obj, 'FLAV', 'FAKE_FLAVOR_NEW')

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    def test_do_update__update_flavor_failed(self, mock_update_flavor):
        ex = exc.EResourceUpdate(type='server', id='NOVA_ID',
                                 message='Flavor Not Found')
        mock_update_flavor.side_effect = ex
        obj = mock.Mock(physical_id='NOVA_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'FAKE_FLAVOR_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               obj, new_profile)

        mock_update_flavor.assert_called_with(obj, 'FLAV', 'FAKE_FLAVOR_NEW')
        self.assertEqual('Failed in updating server NOVA_ID: '
                         'Flavor Not Found.',
                         six.text_type(ex))

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_network_successful_no_definition_overlap(
            self, mock_update_network, mock_update_flavor):
        mock_update_network.return_value = True
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        networks_delete = [{
            'port': 'FAKE_PORT',
            'fixed-ip': 'FAKE_IP',
            'network': 'FAKE_NET',
        }]
        new_networks = [{
            'port': 'FAKE_PORT_NEW',
            'fixed-ip': 'FAKE_IP_NEW',
            'network': 'FAKE_NET_NEW',
        }]
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['networks'] = new_networks
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_network.assert_called_with(obj, new_networks,
                                               networks_delete)

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_network_successful_definition_overlap(
            self, mock_update_network, mock_update_flavor):

        mock_update_network.return_value = True
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        networks_delete = [{
            'port': 'FAKE_PORT',
            'fixed-ip': 'FAKE_IP',
            'network': 'FAKE_NET',
        }]
        new_networks = [{
            'port': 'FAKE_PORT_NEW',
            'fixed-ip': 'FAKE_IP_NEW',
            'network': 'FAKE_NET_NEW',
        }]
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['networks'] = [new_networks[0],
                                              networks_delete[0]]
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_network.assert_called_with(obj, new_networks, [])

    def test_do_update_without_profile(self):
        profile = server.ServerProfile('t', self.spec)
        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'
        new_profile = None
        res = profile.do_update(obj, new_profile)
        self.assertFalse(res)

    def test_do_update_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        node_obj = mock.Mock(physical_id=None)
        new_profile = mock.Mock()

        # Test path where server doesn't exist
        res = profile.do_update(node_obj, new_profile)

        self.assertFalse(res)
