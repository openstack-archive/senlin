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

import base64

import mock
from oslo_utils import encodeutils
import six

from senlin.common import exception as exc
from senlin.profiles import base as profiles_base
from senlin.profiles.os.nova import server
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNovaServerBasic(base.SenlinTestCase):

    def setUp(self):
        super(TestNovaServerBasic, self).setUp()

        self.context = utils.dummy_context()
        self.spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'context': {},
                'admin_pass': 'adminpass',
                'auto_disk_config': True,
                'availability_zone': 'FAKE_AZ',
                'config_drive': False,
                'flavor': 'FLAV',
                'image': 'FAKE_IMAGE',
                'key_name': 'FAKE_KEYNAME',
                "metadata": {"meta var": "meta val"},
                'name': 'FAKE_SERVER_NAME',
                'networks': [{
                    'port': 'FAKE_PORT',
                    'fixed_ip': 'FAKE_IP',
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

    def test_init(self):
        profile = server.ServerProfile('t', self.spec)

        self.assertIsNone(profile.server_id)

    def test__build_metadata(self):
        obj = mock.Mock(id='NODE_ID', cluster_id='')
        profile = server.ServerProfile('t', self.spec)

        res = profile._build_metadata(obj, None)

        self.assertEqual({'cluster_node_id': 'NODE_ID'}, res)

    def test__build_metadata_with_inputs(self):
        obj = mock.Mock(id='NODE_ID', cluster_id='')
        profile = server.ServerProfile('t', self.spec)

        res = profile._build_metadata(obj, {'foo': 'bar'})

        self.assertEqual({'cluster_node_id': 'NODE_ID', 'foo': 'bar'}, res)

    def test__build_metadata_for_cluster_node(self):
        obj = mock.Mock(id='NODE_ID', cluster_id='CLUSTER_ID', index=123)
        profile = server.ServerProfile('t', self.spec)

        res = profile._build_metadata(obj, None)

        self.assertEqual(
            {
                'cluster_id': 'CLUSTER_ID',
                'cluster_node_id': 'NODE_ID',
                'cluster_node_index': '123'
            },
            res
        )

    def _stubout_profile(self, profile, mock_image=False, mock_flavor=False,
                         mock_keypair=False, mock_net=False):
        if mock_image:
            image = mock.Mock(id='FAKE_IMAGE_ID')
            self.patchobject(profile, '_validate_image', return_value=image)

        if mock_flavor:
            flavor = mock.Mock(id='FAKE_FLAVOR_ID')
            self.patchobject(profile, '_validate_flavor', return_value=flavor)

        if mock_keypair:
            keypair = mock.Mock()
            keypair.name = 'FAKE_KEYNAME'
            self.patchobject(profile, '_validate_keypair',
                             return_value=keypair)
        if mock_net:
            fake_net = {
                'fixed_ip': 'FAKE_IP',
                'port': 'FAKE_PORT',
                'uuid': 'FAKE_NETWORK_ID',
            }
            self.patchobject(profile, '_validate_network',
                             return_value=fake_net)

    def test_do_create(self):
        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)
        mock_zone_info = self.patchobject(profile, '_update_zone_info')
        node_obj = mock.Mock(id='FAKE_NODE_ID', index=123,
                             cluster_id='FAKE_CLUSTER_ID',
                             data={
                                'placement': {
                                    'zone': 'AZ1',
                                    'servergroup': 'SERVER_GROUP_1'
                                }
                             })
        node_obj.name = 'TEST_SERVER'
        fake_server = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = fake_server

        # do it
        server_id = profile.do_create(node_obj)

        # assertion
        attrs = dict(
            adminPass='adminpass',
            availability_zone='AZ1',
            config_drive=False,
            flavorRef='FAKE_FLAVOR_ID',
            imageRef='FAKE_IMAGE_ID',
            key_name='FAKE_KEYNAME',
            metadata={
                'cluster_id': 'FAKE_CLUSTER_ID',
                'cluster_node_id': 'FAKE_NODE_ID',
                'cluster_node_index': '123',
                'meta var': 'meta val'
            },
            name='FAKE_SERVER_NAME',
            networks=[{
                'fixed_ip': 'FAKE_IP',
                'port': 'FAKE_PORT',
                'uuid': 'FAKE_NETWORK_ID',
            }],
            personality=[{
                'path': '/etc/motd',
                'contents': 'foo'
            }],
            scheduler_hints={
                'same_host': 'HOST_ID',
                'group': 'SERVER_GROUP_1',
            },
            security_groups=[{'name': 'HIGH_SECURITY_GROUP'}],
            user_data='FAKE_USER_DATA',
        )

        ud = encodeutils.safe_encode('FAKE_USER_DATA')
        attrs['user_data'] = encodeutils.safe_decode(base64.b64encode(ud))
        attrs['OS-DCF:diskConfig'] = 'AUTO'

        cc.server_create.assert_called_once_with(**attrs)
        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    def test_do_create_invalid_image(self):
        profile = server.ServerProfile('s2', self.spec)
        err = exc.EResourceCreation(type='server', message='boom')
        mock_image = self.patchobject(profile, '_validate_image',
                                      side_effect=err)
        node_obj = mock.Mock()

        self.assertRaises(exc.EResourceCreation, profile.do_create, node_obj)

        mock_image.assert_called_once_with(node_obj, 'FAKE_IMAGE', 'create')

    def test_do_create_invalid_flavor(self):
        profile = server.ServerProfile('s2', self.spec)
        self._stubout_profile(profile, mock_image=True)
        err = exc.EResourceCreation(type='server', message='boom')
        mock_flavor = self.patchobject(profile, '_validate_flavor',
                                       side_effect=err)
        node_obj = mock.Mock()

        self.assertRaises(exc.EResourceCreation, profile.do_create, node_obj)

        mock_flavor.assert_called_once_with(node_obj, 'FLAV', 'create')

    def test_do_create_invalid_keypair(self):
        profile = server.ServerProfile('s2', self.spec)
        self._stubout_profile(profile, mock_image=True, mock_flavor=True)
        err = exc.EResourceCreation(type='server', message='boom')
        mock_kp = self.patchobject(profile, '_validate_keypair',
                                   side_effect=err)
        node_obj = mock.Mock()

        self.assertRaises(exc.EResourceCreation, profile.do_create, node_obj)

        mock_kp.assert_called_once_with(node_obj, 'FAKE_KEYNAME', 'create')

    def test_do_create_invalid_network(self):
        cc = mock.Mock()
        nc = mock.Mock()
        node_obj = mock.Mock(id='FAKE_NODE_ID', data={}, index=123,
                             cluster_id='FAKE_CLUSTER_ID')
        spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAV',
                'image': 'FAKE_IMAGE',
                'key_name': 'FAKE_KEYNAME',
                'name': 'FAKE_SERVER_NAME',
                'networks': [{
                    'network': 'FAKE_NET'
                }]
            }
        }

        profile = server.ServerProfile('s2', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True)
        err = exc.EResourceCreation(type='server', message='FOO')
        mock_net = self.patchobject(profile, '_validate_network',
                                    side_effect=err)

        self.assertRaises(exc.EResourceCreation,
                          profile.do_create,
                          node_obj)
        mock_net.assert_called_once_with(
            node_obj, {'network': 'FAKE_NET', 'port': None, 'fixed_ip': None},
            'create')

    def test_do_create_server_attrs_not_defined(self):
        cc = mock.Mock()
        nc = mock.Mock()
        node_obj = mock.Mock(id='FAKE_NODE_ID', data={}, index=123,
                             cluster_id='FAKE_CLUSTER_ID')

        # Assume image/scheduler_hints/user_data were not defined in spec file
        spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAV',
                'name': 'FAKE_SERVER_NAME',
                'security_groups': ['HIGH_SECURITY_GROUP'],
            }
        }
        profile = server.ServerProfile('t', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)
        mock_zone_info = self.patchobject(profile, '_update_zone_info')
        fake_server = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = fake_server

        # do it
        server_id = profile.do_create(node_obj)

        # assertions
        attrs = {
            'OS-DCF:diskConfig': 'AUTO',
            'flavorRef': 'FAKE_FLAVOR_ID',
            'name': 'FAKE_SERVER_NAME',
            'metadata': {
                'cluster_id': 'FAKE_CLUSTER_ID',
                'cluster_node_id': 'FAKE_NODE_ID',
                'cluster_node_index': '123',
            },
            'security_groups': [{'name': 'HIGH_SECURITY_GROUP'}]
        }

        cc.server_create.assert_called_once_with(**attrs)
        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    def test_do_create_obj_name_cluster_id_is_none(self):
        cc = mock.Mock()
        nc = mock.Mock()
        spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAV',
                'name': 'FAKE_SERVER_NAME',
                'security_groups': ['HIGH_SECURITY_GROUP'],
            }
        }
        profile = server.ServerProfile('t', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)
        mock_zone_info = self.patchobject(profile, '_update_zone_info')
        node_obj = mock.Mock(id='FAKE_NODE_ID', cluster_id='', data={},
                             index=None)
        node_obj.name = None
        fake_server = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = fake_server

        server_id = profile.do_create(node_obj)

        attrs = {
            'OS-DCF:diskConfig': 'AUTO',
            'flavorRef': 'FAKE_FLAVOR_ID',
            'name': 'FAKE_SERVER_NAME',
            'metadata': {'cluster_node_id': 'FAKE_NODE_ID'},
            'security_groups': [{'name': 'HIGH_SECURITY_GROUP'}]
        }

        cc.server_create.assert_called_once_with(**attrs)
        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    def test_do_create_name_property_is_not_defined(self):
        cc = mock.Mock()
        nc = mock.Mock()
        spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAV',
                'security_groups': ['HIGH_SECURITY_GROUP'],
            }
        }
        profile = server.ServerProfile('t', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)
        mock_zone_info = self.patchobject(profile, '_update_zone_info')

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})
        node_obj.name = 'TEST-SERVER'
        fake_server = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = fake_server

        # do it
        server_id = profile.do_create(node_obj)

        # assertions
        attrs = {
            'OS-DCF:diskConfig': 'AUTO',
            'flavorRef': 'FAKE_FLAVOR_ID',
            'name': 'TEST-SERVER',
            'metadata': {'cluster_node_id': 'NODE_ID'},
            'security_groups': [{'name': 'HIGH_SECURITY_GROUP'}]
        }

        cc.server_create.assert_called_once_with(**attrs)
        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    def test_do_create_bdm_v2(self):
        cc = mock.Mock()
        nc = mock.Mock()
        bdm_v2 = [
            {
                'volume_size': 1,
                'uuid': '6ce0be68',
                'source_type': 'image',
                'destination_type': 'volume',
                'boot_index': 0,
            },
            {
                'volume_size': 2,
                'source_type': 'blank',
                'destination_type': 'volume',
            }
        ]
        spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAV',
                'name': 'FAKE_SERVER_NAME',
                'security_groups': ['HIGH_SECURITY_GROUP'],
                'block_device_mapping_v2': bdm_v2,
            }
        }
        profile = server.ServerProfile('t', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)
        mock_zone_info = self.patchobject(profile, '_update_zone_info')
        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})
        node_obj.name = None
        fake_server = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = fake_server

        # do it
        server_id = profile.do_create(node_obj)

        # assertions
        expected_volume = {
            'guest_format': None,
            'boot_index': 0,
            'uuid': '6ce0be68',
            'volume_size': 1,
            'device_name': None,
            'disk_bus': None,
            'source_type': 'image',
            'device_type': None,
            'destination_type': 'volume',
            'delete_on_termination': None
        }
        self.assertEqual(expected_volume,
                         profile.properties['block_device_mapping_v2'][0])
        attrs = {
            'OS-DCF:diskConfig': 'AUTO',
            'flavorRef': 'FAKE_FLAVOR_ID',
            'name': 'FAKE_SERVER_NAME',
            'metadata': {'cluster_node_id': 'NODE_ID'},
            'security_groups': [{'name': 'HIGH_SECURITY_GROUP'}],
            'block_device_mapping_v2': bdm_v2
        }
        cc.server_create.assert_called_once_with(**attrs)
        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    def test_do_create_wait_server_timeout(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)

        node_obj = mock.Mock(id='FAKE_NODE_ID', index=123,
                             cluster_id='FAKE_CLUSTER_ID',
                             data={
                                'placement': {
                                    'zone': 'AZ1',
                                    'servergroup': 'SERVER_GROUP_1'
                                }
                             })
        node_obj.name = 'TEST_SERVER'
        server_obj = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = server_obj

        err = exc.InternalError(code=500, message='TIMEOUT')
        cc.wait_for_server.side_effect = err
        ex = self.assertRaises(exc.EResourceCreation, profile.do_create,
                               node_obj)

        self.assertEqual('Failed in creating server: TIMEOUT.',
                         six.text_type(ex))
        cc.wait_for_server.assert_called_once_with('FAKE_ID')

    def test_do_create_failed(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=True)
        mock_zone_info = self.patchobject(profile, '_update_zone_info')
        node_obj = mock.Mock(id='FAKE_NODE_ID', index=123,
                             cluster_id='FAKE_CLUSTER_ID',
                             data={
                                'placement': {
                                    'zone': 'AZ1',
                                    'servergroup': 'SERVER_GROUP_1'
                                }
                             })
        node_obj.name = 'TEST_SERVER'
        cc.server_create.side_effect = exc.InternalError(
            code=500, message="creation failed.")

        # do it
        ex = self.assertRaises(exc.EResourceCreation, profile.do_create,
                               node_obj)

        # assertions
        self.assertEqual('Failed in creating server: creation failed.',
                         six.text_type(ex))
        self.assertEqual(0, cc.wait_for_server.call_count)
        self.assertEqual(0, mock_zone_info.call_count)

    def test_do_delete_ok(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_delete.return_value = None
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_delete(test_server)

        self.assertTrue(res)
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with('FAKE_ID')

    def test_do_delete_ignore_missing_force(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_delete(test_server, ignore_missing=False, force=True)

        self.assertTrue(res)
        cc.server_force_delete.assert_called_once_with('FAKE_ID', False)
        cc.wait_for_server_delete.assert_called_once_with('FAKE_ID')

    def test_do_delete_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)
        test_server = mock.Mock(physical_id=None)

        res = profile.do_delete(test_server)

        self.assertTrue(res)

    def test_do_delete_with_delete_failure(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        err = exc.InternalError(code=500, message='Nova Error')
        cc.server_delete.side_effect = err
        obj = mock.Mock(physical_id='FAKE_ID')

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, obj)

        self.assertEqual("Failed in deleting server 'FAKE_ID': "
                         "Nova Error.", six.text_type(ex))
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        self.assertEqual(0, cc.wait_for_server_delete.call_count)

    def test_do_delete_with_force_delete_failure(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        err = exc.InternalError(code=500, message='Nova Error')
        cc.server_force_delete.side_effect = err
        obj = mock.Mock(physical_id='FAKE_ID')

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, obj, force=True)

        self.assertEqual("Failed in deleting server 'FAKE_ID': "
                         "Nova Error.", six.text_type(ex))
        cc.server_force_delete.assert_called_once_with('FAKE_ID', True)
        self.assertEqual(0, cc.wait_for_server_delete.call_count)

    def test_do_delete_wait_for_server_timeout(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        obj = mock.Mock(physical_id='FAKE_ID')
        err = exc.InternalError(code=500, message='TIMEOUT')
        cc.wait_for_server_delete.side_effect = err

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, obj)

        self.assertEqual("Failed in deleting server 'FAKE_ID': TIMEOUT.",
                         six.text_type(ex))
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with('FAKE_ID')

    def test_do_get_details(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        # Test normal path
        nova_server = mock.Mock()
        nova_server.to_dict.return_value = {
            'OS-DCF:diskConfig': 'MANUAL',
            'OS-EXT-AZ:availability_zone': 'nova',
            'OS-EXT-STS:power_state': 1,
            'OS-EXT-STS:task_state': None,
            'OS-EXT-STS:vm_state': 'active',
            'OS-SRV-USG:launched_at': 'TIMESTAMP1',
            'OS-SRV-USG:terminated_at': None,
            'accessIPv4': 'FAKE_IPV4',
            'accessIPv6': 'FAKE_IPV6',
            'addresses': {
                'private': [{
                    'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:5e:00:81',
                    'version': 4,
                    'addr': '10.0.0.3',
                    'OS-EXT-IPS:type': 'fixed'
                }]
            },
            'config_drive': True,
            'created': 'CREATED_TIMESTAMP',
            'flavor': {
                'id': '1',
                'links': [{
                    'href': 'http://url_flavor',
                    'rel': 'bookmark'
                }]
            },
            'hostId': 'FAKE_HOST_ID',
            'id': 'FAKE_ID',
            'image': {
                'id': 'FAKE_IMAGE',
                'links': [{
                    'href': 'http://url_image',
                    'rel': 'bookmark'
                }],
            },
            'key_name': 'FAKE_KEY',
            'links': [{
                'href': 'http://url1',
                'rel': 'self'
            }, {
                'href': 'http://url2',
                'rel': 'bookmark'
            }],
            'metadata': {},
            'name': 'FAKE_NAME',
            'os-extended-volumes:volumes_attached': [],
            'progress': 0,
            'security_groups': [{'name': 'default'}],
            'status': 'FAKE_STATUS',
            'tenant_id': 'FAKE_TENANT',
            'updated': 'UPDATE_TIMESTAMP',
            'user_id': 'FAKE_USER_ID',
        }
        cc.server_get.return_value = nova_server
        res = profile.do_get_details(node_obj)
        expected = {
            'OS-DCF:diskConfig': 'MANUAL',
            'OS-EXT-AZ:availability_zone': 'nova',
            'OS-EXT-STS:power_state': 1,
            'OS-EXT-STS:task_state': '-',
            'OS-EXT-STS:vm_state': 'active',
            'OS-SRV-USG:launched_at': 'TIMESTAMP1',
            'OS-SRV-USG:terminated_at': '-',
            'accessIPv4': 'FAKE_IPV4',
            'accessIPv6': 'FAKE_IPV6',
            'config_drive': True,
            'created': 'CREATED_TIMESTAMP',
            'flavor': '1',
            'hostId': 'FAKE_HOST_ID',
            'id': 'FAKE_ID',
            'image': 'FAKE_IMAGE',
            'key_name': 'FAKE_KEY',
            'metadata': {},
            'name': 'FAKE_NAME',
            'os-extended-volumes:volumes_attached': [],
            'addresses': {
                'private': [{
                    'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:5e:00:81',
                    'version': 4,
                    'addr': '10.0.0.3',
                    'OS-EXT-IPS:type': 'fixed'
                }]
            },
            'progress': 0,
            'security_groups': 'default',
            'updated': 'UPDATE_TIMESTAMP',
            'status': 'FAKE_STATUS',
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_with_no_network_or_sg(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        # Test normal path
        nova_server = mock.Mock()
        nova_server.to_dict.return_value = {
            'addresses': {},
            'flavor': {
                'id': 'FAKE_FLAVOR',
            },
            'id': 'FAKE_ID',
            'image': {
                'id': 'FAKE_IMAGE',
            },
            'security_groups': [],
        }
        cc.server_get.return_value = nova_server
        res = profile.do_get_details(node_obj)
        expected = {
            'flavor': 'FAKE_FLAVOR',
            'id': 'FAKE_ID',
            'image': 'FAKE_IMAGE',
            'addresses': {},
            'security_groups': '',
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_with_more_network_or_sg(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        # Test normal path
        nova_server = mock.Mock()
        nova_server.to_dict.return_value = {
            'addresses': {
                'private': [{
                    'version': 4,
                    'addr': '10.0.0.3',
                }, {
                    'version': 4,
                    'addr': '192.168.43.3'
                }],
                'public': [{
                    'version': 4,
                    'addr': '172.16.5.3',
                }]
            },
            'flavor': {
                'id': 'FAKE_FLAVOR',
            },
            'id': 'FAKE_ID',
            'image': {
                'id': 'FAKE_IMAGE',
            },
            'security_groups': [{
                'name': 'default',
            }, {
                'name': 'webserver',
            }],
        }
        cc.server_get.return_value = nova_server
        res = profile.do_get_details(node_obj)
        expected = {
            'flavor': 'FAKE_FLAVOR',
            'id': 'FAKE_ID',
            'image': 'FAKE_IMAGE',
            'addresses': {
                'private': [{
                    'version': 4,
                    'addr': '10.0.0.3',
                }, {
                    'version': 4,
                    'addr': '192.168.43.3'
                }],
                'public': [{
                    'version': 4,
                    'addr': '172.16.5.3',
                }]
            },
            'security_groups': ['default', 'webserver'],
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_no_physical_id(self):
        # Test path for server not created
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='')
        self.assertEqual({}, profile.do_get_details(node_obj))

        node_obj.physical_id = None
        self.assertEqual({}, profile.do_get_details(node_obj))

    def test_do_get_details_server_not_found(self):
        # Test path for server not created
        cc = mock.Mock()
        err = exc.InternalError(code=404, message='No Server found for ID')
        cc.server_get.side_effect = err
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_get_details(node_obj)
        expected = {
            'Error': {
                'message': 'No Server found for ID',
                'code': 404
            }
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_join_successful(self):
        profile = server.ServerProfile('t', self.spec)

        cluster_id = "FAKE_CLUSTER_ID"
        cc = mock.Mock()
        cc.server_metadata_get.return_value = {'FOO': 'BAR'}
        cc.server_metadata_update.return_value = {'cluster_id': cluster_id}
        profile._computeclient = cc

        node_obj = mock.Mock(physical_id='FAKE_ID', index=567)

        res = profile.do_join(node_obj, cluster_id)

        self.assertTrue(res)
        cc.server_metadata_get.assert_called_once_with('FAKE_ID')
        expected_metadata = {
            'cluster_id': 'FAKE_CLUSTER_ID',
            'cluster_node_index': '567',
            'FOO': 'BAR'
        }
        cc.server_metadata_update.assert_called_once_with(
            'FAKE_ID', expected_metadata)

    def test_do_join_server_not_created(self):
        # Test path where server not specified
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id=None)

        res = profile.do_join(node_obj, 'FAKE_CLUSTER_ID')

        self.assertFalse(res)

    def test_do_leave_successful(self):
        # Test normal path
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_leave(node_obj)

        self.assertTrue(res)
        cc.server_metadata_delete.assert_called_once_with(
            'FAKE_ID', ['cluster_id', 'cluster_node_index'])

    def test_do_leave_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id=None)

        res = profile.do_leave(node_obj)

        self.assertFalse(res)

    def test_do_check(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = None
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_check(test_server)
        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertFalse(res)

        return_server = mock.Mock()
        return_server.status = 'ACTIVE'
        cc.server_get.return_value = return_server
        res = profile.do_check(test_server)
        cc.server_get.assert_called_with('FAKE_ID')
        self.assertTrue(res)

    @mock.patch.object(server.ServerProfile, 'handle_rebuild')
    def test_do_recover_rebuild(self, mock_rebuild):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_recover(node_obj, operation='REBUILD')

        self.assertEqual(mock_rebuild.return_value, res)
        mock_rebuild.assert_called_once_with(node_obj)

    @mock.patch.object(server.ServerProfile, 'handle_rebuild')
    def test_do_recover_with_list(self, mock_rebuild):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_recover(node_obj, operation=['REBUILD'])

        self.assertEqual(mock_rebuild.return_value, res)
        mock_rebuild.assert_called_once_with(node_obj)

    @mock.patch.object(profiles_base.Profile, 'do_recover')
    def test_do_recover_fallback(self, mock_base_recover):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_recover(node_obj, operation='blahblah')

        self.assertEqual(mock_base_recover.return_value, res)
        mock_base_recover.assert_called_once_with(node_obj,
                                                  operation='blahblah')

    def test_handle_reboot(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        cc.server_reboot = mock.Mock()
        cc.wait_for_server = mock.Mock()
        profile._computeclient = cc

        # do it
        res = profile.handle_reboot(obj, type='SOFT')

        self.assertTrue(res)
        cc.server_reboot.assert_called_once_with('FAKE_ID', 'SOFT')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_reboot_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_reboot(obj, type='SOFT')

        self.assertFalse(res)

    def test_handle_reboot_default_type(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        cc.server_reboot = mock.Mock()
        cc.wait_for_server = mock.Mock()
        profile._computeclient = cc

        # do it
        res = profile.handle_reboot(obj)

        self.assertTrue(res)
        cc.server_reboot.assert_called_once_with('FAKE_ID', 'SOFT')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_reboot_bad_type(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_reboot(obj, type=['foo'])
        self.assertFalse(res)

        res = profile.handle_reboot(obj, type='foo')
        self.assertFalse(res)

    def test_handle_rebuild(self):
        profile = server.ServerProfile('t', self.spec)
        x_image = {'id': '123'}
        x_server = mock.Mock(image=x_image)
        cc = mock.Mock()
        cc.server_get.return_value = x_server
        cc.server_rebuild.return_value = True
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.handle_rebuild(node_obj)

        self.assertTrue(res)
        cc.server_get.assert_called_with('FAKE_ID')
        cc.server_rebuild.assert_called_once_with('FAKE_ID', '123',
                                                  'FAKE_SERVER_NAME',
                                                  'adminpass')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_rebuild_server_not_found(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        err = exc.InternalError(code=404, message='FAKE_ID not found')
        cc.server_get.side_effect = err
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_rebuild,
                               node_obj)

        self.assertEqual("Failed in rebuilding server 'FAKE_ID': "
                         "FAKE_ID not found.",
                         six.text_type(ex))
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_handle_rebuild_failed_rebuild(self):
        profile = server.ServerProfile('t', self.spec)
        x_image = {'id': '123'}
        x_server = mock.Mock(image=x_image)
        cc = mock.Mock()
        cc.server_get.return_value = x_server
        ex = exc.InternalError(code=500, message='cannot rebuild')
        cc.server_rebuild.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_rebuild,
                               node_obj)

        self.assertEqual("Failed in rebuilding server 'FAKE_ID': "
                         "cannot rebuild.",
                         six.text_type(ex))
        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.server_rebuild.assert_called_once_with('FAKE_ID', '123',
                                                  'FAKE_SERVER_NAME',
                                                  'adminpass')
        self.assertEqual(0, cc.wait_for_server.call_count)

    def test_handle_rebuild_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        x_image = {'id': '123'}
        x_server = mock.Mock(image=x_image)
        cc = mock.Mock()
        cc.server_get.return_value = x_server
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_rebuild,
                               node_obj)

        self.assertEqual("Failed in rebuilding server 'FAKE_ID': "
                         "timeout.", six.text_type(ex))
        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.server_rebuild.assert_called_once_with('FAKE_ID', '123',
                                                  'FAKE_SERVER_NAME',
                                                  'adminpass')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_rebuild_failed_retrieving_server(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        cc.server_get.return_value = None
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.handle_rebuild(node_obj)

        self.assertFalse(res)
        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertEqual(0, cc.server_rebuild.call_count)
        self.assertEqual(0, cc.wait_for_server.call_count)

    def test_handle_rebuild_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        test_server = mock.Mock()
        test_server.physical_id = None

        res = profile.handle_rebuild(test_server)

        self.assertFalse(res)

    def test_handle_change_password(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        cc.server_reboot = mock.Mock()
        cc.wait_for_server = mock.Mock()
        profile._computeclient = cc

        # do it
        res = profile.handle_change_password(obj, admin_pass='new_pass')

        self.assertTrue(res)
        cc.server_change_password.assert_called_once_with('FAKE_ID',
                                                          'new_pass')

    def test_handle_change_password_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_change_password(obj, admin_pass='new_pass')

        self.assertFalse(res)

    def test_handle_change_password_no_password(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_change_password(obj)

        self.assertFalse(res)

    def test_handle_change_password_bad_param(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_change_password(obj, admin_pass=['foo'])
        self.assertFalse(res)

        res = profile.handle_change_password(obj, foo='bar')
        self.assertFalse(res)
