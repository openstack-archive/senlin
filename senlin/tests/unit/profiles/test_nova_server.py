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
from unittest import mock

from oslo_config import cfg
from oslo_utils import encodeutils

from senlin.common import consts
from senlin.common import exception as exc
from senlin.objects import node as node_ob
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
                    'fixed_ip': 'FAKE_IP',
                    'network': 'FAKE_NET',
                    'floating_network': 'FAKE_PUBLIC_NET',
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

    def test_build_metadata(self):
        obj = mock.Mock(id='NODE_ID', cluster_id='')
        profile = server.ServerProfile('t', self.spec)

        res = profile._build_metadata(obj, None)

        self.assertEqual({'cluster_node_id': 'NODE_ID'}, res)

    def test_build_metadata_with_inputs(self):
        obj = mock.Mock(id='NODE_ID', cluster_id='')
        profile = server.ServerProfile('t', self.spec)

        res = profile._build_metadata(obj, {'foo': 'bar'})

        self.assertEqual({'cluster_node_id': 'NODE_ID', 'foo': 'bar'}, res)

    def test_build_metadata_for_cluster_node(self):
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
                'floating_network': 'FAKE_PUBLIC_NET_ID',
            }
            self.patchobject(profile, '_validate_network',
                             return_value=fake_net)
            fake_ports = [{
                'id': 'FAKE_PORT'
            }]
            self.patchobject(profile, '_create_ports_from_properties',
                             return_value=fake_ports)

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
        cc.server_get.return_value = fake_server

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
                'port': 'FAKE_PORT',
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
        cc.server_get.assert_called_once_with('FAKE_ID')
        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_create_fail_create_instance_when_node_longer_exists(
            self, mock_node_update):
        mock_node_update.side_effect = [
            None, exc.ResourceNotFound(type='Node', id='FAKE_NODE_ID')
        ]

        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc
        profile._rollback_ports = mock.Mock()
        profile._rollback_instance = mock.Mock()
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=False)
        node_obj = mock.Mock(id='FAKE_NODE_ID', index=123,
                             availability_zone="AZ01",
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
        cc.server_get.return_value = fake_server

        self.assertRaises(
            exc.ResourceNotFound, profile.do_create, node_obj
        )

        profile._rollback_ports.assert_called_once()
        profile._rollback_instance.assert_called_once()

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_create_fail_create_port_when_node_longer_exists(
            self, mock_node_update):
        mock_node_update.side_effect = exc.ResourceNotFound(
            type='Node', id='FAKE_NODE_ID'
        )

        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc
        profile._rollback_ports = mock.Mock()
        profile._rollback_instance = mock.Mock()
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True, mock_net=False)
        node_obj = mock.Mock(id='FAKE_NODE_ID', index=123,
                             cluster_id='FAKE_CLUSTER_ID',
                             data={
                                'placement': {
                                    'zone': 'AZ1',
                                    'servergroup': 'SERVER_GROUP_1'
                                }
                             })
        node_obj.name = 'TEST_SERVER'

        self.assertRaises(
            exc.ResourceNotFound, profile.do_create, node_obj
        )

        profile._rollback_ports.assert_called_once()
        profile._rollback_instance.assert_not_called()

    def test_do_create_invalid_image(self):
        profile = server.ServerProfile('s2', self.spec)
        err = exc.EResourceCreation(type='server', message='boom')
        mock_image = self.patchobject(profile, '_validate_image',
                                      side_effect=err)
        node_obj = mock.Mock()

        self.assertRaises(exc.EResourceCreation, profile.do_create, node_obj)

        mock_image.assert_called_once_with(node_obj, 'FAKE_IMAGE', 'create')

    def test_do_create_bdm_invalid_image(self):
        cc = mock.Mock()
        nc = mock.Mock()
        node_obj = mock.Mock(id='FAKE_NODE_ID', data={}, index=123,
                             cluster_id='FAKE_CLUSTER_ID')
        bdm_v2 = [
            {
                'volume_size': 1,
                'uuid': '6ce0be68',
                'source_type': 'image',
                'destination_type': 'volume',
                'boot_index': 0,
            },
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
        profile = server.ServerProfile('s2', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True)
        err = exc.EResourceCreation(type='server', message='FOO')
        mock_volume = self.patchobject(profile, '_resolve_bdm',
                                       side_effect=err)

        self.assertRaises(exc.EResourceCreation,
                          profile.do_create,
                          node_obj)
        expected_volume = [{
            'guest_format': None,
            'boot_index': 0,
            'uuid': '6ce0be68',
            'volume_size': 1,
            'device_name': None,
            'disk_bus': None,
            'source_type': 'image',
            'device_type': None,
            'destination_type': 'volume',
            'delete_on_termination': None,
            'volume_type': None
        }]
        mock_volume.assert_called_once_with(
            node_obj, expected_volume, 'create')

    def test_do_create_bdm_invalid_volume(self):
        cc = mock.Mock()
        nc = mock.Mock()
        node_obj = mock.Mock(id='FAKE_NODE_ID', data={}, index=123,
                             cluster_id='FAKE_CLUSTER_ID')
        bdm_v2 = [
            {
                'volume_size': 1,
                'uuid': '6ce0be68',
                'source_type': 'volume',
                'destination_type': 'volume',
                'boot_index': 0,
            },
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
        profile = server.ServerProfile('s2', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True)
        err = exc.EResourceCreation(type='server', message='FOO')
        mock_volume = self.patchobject(profile, '_resolve_bdm',
                                       side_effect=err)

        self.assertRaises(exc.EResourceCreation,
                          profile.do_create,
                          node_obj)
        expected_volume = [{
            'guest_format': None,
            'boot_index': 0,
            'uuid': '6ce0be68',
            'volume_size': 1,
            'device_name': None,
            'disk_bus': None,
            'source_type': 'volume',
            'device_type': None,
            'destination_type': 'volume',
            'delete_on_termination': None,
            'volume_type': None
        }]
        mock_volume.assert_called_once_with(
            node_obj, expected_volume, 'create')

    def test_do_create_bdm_invalid_volume_type(self):
        cc = mock.Mock()
        nc = mock.Mock()
        node_obj = mock.Mock(id='FAKE_NODE_ID', data={}, index=123,
                             cluster_id='FAKE_CLUSTER_ID')
        bdm_v2 = [
            {
                'volume_size': 1,
                'source_type': 'blank',
                'destination_type': 'volume',
                'boot_index': 0,
                'volume_type': '588854a9',
            },
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
        profile = server.ServerProfile('s2', spec)
        profile._computeclient = cc
        profile._networkclient = nc
        self._stubout_profile(profile, mock_image=True, mock_flavor=True,
                              mock_keypair=True)
        err = exc.EResourceCreation(type='server', message='FOO')
        mock_volume = self.patchobject(profile, '_resolve_bdm',
                                       side_effect=err)

        self.assertRaises(exc.EResourceCreation,
                          profile.do_create,
                          node_obj)
        expected_volume = [{
            'guest_format': None,
            'boot_index': 0,
            'uuid': None,
            'volume_size': 1,
            'device_name': None,
            'disk_bus': None,
            'source_type': 'blank',
            'device_type': None,
            'destination_type': 'volume',
            'delete_on_termination': None,
            'volume_type': '588854a9'
        }]
        mock_volume.assert_called_once_with(
            node_obj, expected_volume, 'create')

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
        expect_params = {
            'floating_network': None,
            'network': 'FAKE_NET',
            'vnic_type': None,
            'fixed_ip': None,
            'floating_ip': None,
            'port': None,
            'security_groups': None,
            'subnet': None
        }
        mock_net.assert_called_once_with(
            node_obj, expect_params, 'create')

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
        cc.server_get.return_value = fake_server

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
        cc.server_get.assert_called_once_with('FAKE_ID')
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
        cc.server_get.return_value = fake_server

        server_id = profile.do_create(node_obj)

        attrs = {
            'OS-DCF:diskConfig': 'AUTO',
            'flavorRef': 'FAKE_FLAVOR_ID',
            'name': 'FAKE_SERVER_NAME',
            'metadata': {'cluster_node_id': 'FAKE_NODE_ID'},
            'security_groups': [{'name': 'HIGH_SECURITY_GROUP'}]
        }

        cc.server_create.assert_called_once_with(**attrs)
        cc.server_get.assert_called_once_with('FAKE_ID')
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
        cc.server_get.return_value = fake_server

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
        cc.server_get.assert_called_once_with('FAKE_ID')
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
        cc.server_get.return_value = fake_server

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
            'delete_on_termination': None,
            'volume_type': None
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
        cc.server_get.assert_called_once_with('FAKE_ID')
        profile._validate_image.assert_called_once_with(
            node_obj, expected_volume['uuid'], 'create')

        mock_zone_info.assert_called_once_with(node_obj, fake_server)
        self.assertEqual('FAKE_ID', server_id)

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_create_wait_server_timeout(self, mock_node_obj):
        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc
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
        self.assertEqual('FAKE_ID', ex.resource_id)
        self.assertEqual('Failed in creating server: TIMEOUT.',
                         str(ex))
        mock_node_obj.assert_not_called()
        cc.wait_for_server.assert_called_once_with(
            'FAKE_ID', timeout=cfg.CONF.default_nova_timeout)

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_create_failed(self, mock_node_obj):
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
        mock_node_obj.assert_called_once_with(mock.ANY, node_obj.id,
                                              {'data': node_obj.data})
        self.assertEqual('Failed in creating server: creation failed.',
                         str(ex))
        self.assertIsNone(ex.resource_id)
        self.assertEqual(0, cc.wait_for_server.call_count)
        self.assertEqual(0, mock_zone_info.call_count)

    @mock.patch.object(node_ob.Node, 'update')
    @mock.patch.object(server.ServerProfile, 'do_delete')
    def test_do_create_failed_with_server_id(self, mock_profile_delete,
                                             mock_node_obj):
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
        fake_server = mock.Mock(id='FAKE_ID')
        cc.server_create.return_value = fake_server
        cc.wait_for_server.side_effect = exc.InternalError(
            code=500, message="creation failed.")

        # do it
        ex = self.assertRaises(exc.EResourceCreation, profile.do_create,
                               node_obj)

        # assertions
        mock_node_obj.assert_not_called()
        mock_profile_delete.assert_called_once_with(
            node_obj, internal_ports=[{'id': 'FAKE_PORT'}])
        self.assertEqual('Failed in creating server: creation failed.',
                         str(ex))
        self.assertEqual(1, cc.wait_for_server.call_count)
        self.assertEqual(0, mock_zone_info.call_count)

    def test_rollback_ports(self):
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.return_value = None
        profile = server.ServerProfile('t', self.spec)
        profile._networkclient = nc

        ports = [
            {
                'id': 'FAKE_PORT_ID',
                'remove': True
            },
            {
                'floating': {
                    'remove': True,
                    'id': 'FAKE_FLOATING_ID',
                },
                'id': 'FAKE_PORT_ID',
                'remove': True
            },
            {
                'floating': {
                    'remove': False,
                    'id': 'FAKE_FLOATING_ID',
                },
                'id': 'FAKE_PORT_ID',
                'remove': False
            }
        ]

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})

        profile._rollback_ports(node_obj, ports)

        nc.port_delete.assert_called()
        nc.floatingip_delete.assert_called_once_with('FAKE_FLOATING_ID')

    def test_rollback_with_no_ports(self):
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.return_value = None
        profile = server.ServerProfile('t', self.spec)
        profile._networkclient = nc

        ports = []

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})

        profile._rollback_ports(node_obj, ports)

        nc.port_delete.assert_not_called()
        nc.floatingip_delete.assert_not_called()

    def test_rollback_ports_with_internal_error(self):
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.side_effect = exc.InternalError()
        profile = server.ServerProfile('t', self.spec)
        profile._networkclient = nc

        ports = [{
            'floating': {
                'remove': True,
                'id': 'FAKE_FLOATING_ID',
            },
            'id': 'FAKE_PORT_ID',
            'remove': True
        }]

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})

        profile._rollback_ports(node_obj, ports)

        nc.port_delete.assert_not_called()
        nc.floatingip_delete.assert_called_once_with('FAKE_FLOATING_ID')

    def test_rollback_instance(self):
        cc = mock.Mock()
        cc.port_delete.return_value = None
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        server_obj = mock.Mock(id='SERVER_ID')

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})

        profile._rollback_instance(node_obj, server_obj)

        cc.server_force_delete.assert_called_once_with('SERVER_ID', True)

    def test_rollback_with_no_instance(self):
        cc = mock.Mock()
        cc.port_delete.return_value = None
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        server_obj = None

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})

        profile._rollback_instance(node_obj, server_obj)

        cc.server_force_delete.assert_not_called()

    def test_rollback_instance_with_internal_error(self):
        cc = mock.Mock()
        cc.server_force_delete.side_effect = exc.InternalError()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        server_obj = mock.Mock(id='SERVER_ID')

        node_obj = mock.Mock(id='NODE_ID', cluster_id='', index=-1, data={})

        profile._rollback_instance(node_obj, server_obj)

        cc.server_force_delete.assert_called_once_with('SERVER_ID', True)

    def test_do_delete_ok(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_delete.return_value = None
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')
        test_server.data = {}

        res = profile.do_delete(test_server)

        self.assertTrue(res)
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with(
            'FAKE_ID', timeout=cfg.CONF.default_nova_timeout)

    def test_do_delete_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        profile._computeclient = cc

        test_server = mock.Mock(physical_id=None)
        test_server.data = {}

        # do it
        res = profile.do_delete(test_server)

        # assertions
        self.assertTrue(res)
        self.assertFalse(cc.server_delete.called)
        self.assertFalse(cc.wait_for_server_delete.called)

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_no_physical_id_with_internal_ports(self, mock_node_obj):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.return_value = None
        profile._computeclient = cc
        profile._networkclient = nc

        test_server = mock.Mock(physical_id=None)
        test_server.data = {'internal_ports': [{
            'floating': {
                'remove': True,
                'id': 'FAKE_FLOATING_ID',
            },
            'id': 'FAKE_PORT_ID',
            'remove': True
        }]}

        # do it
        res = profile.do_delete(test_server)

        # assertions
        self.assertTrue(res)
        mock_node_obj.assert_called_once_with(
            mock.ANY, test_server.id, {'data': {'internal_ports': []}})
        self.assertFalse(cc.server_delete.called)
        self.assertFalse(cc.wait_for_server_delete.called)

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_ports_ok(self, mock_node_obj):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_delete.return_value = None
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.return_value = None
        profile._computeclient = cc
        profile._networkclient = nc

        test_server = mock.Mock(physical_id='FAKE_ID')
        test_server.Node = mock.Mock()
        test_server.data = {'internal_ports': [{
            'floating': {
                'remove': True,
                'id': 'FAKE_FLOATING_ID',
            },
            'id': 'FAKE_PORT_ID',
            'remove': True
        }]}

        res = profile.do_delete(test_server)

        self.assertTrue(res)
        mock_node_obj.assert_called_once_with(
            mock.ANY, test_server.id, {'data': {'internal_ports': []}})
        nc.floatingip_delete.assert_called_once_with('FAKE_FLOATING_ID')
        nc.port_delete.assert_called_once_with('FAKE_PORT_ID')
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with(
            'FAKE_ID', timeout=cfg.CONF.default_nova_timeout)

    def test_do_delete_ignore_missing_force(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')
        test_server.data = {}

        res = profile.do_delete(test_server, ignore_missing=False, force=True)

        self.assertTrue(res)
        cc.server_force_delete.assert_called_once_with('FAKE_ID', False)
        cc.wait_for_server_delete.assert_called_once_with(
            'FAKE_ID', timeout=cfg.CONF.default_nova_timeout)

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_with_delete_failure(self, mock_node_obj):
        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc

        err = exc.InternalError(code=500, message='Nova Error')
        cc.server_delete.side_effect = err
        obj = mock.Mock(physical_id='FAKE_ID')
        obj.data = {'internal_ports': [{
            'floating': {
                'remove': True,
                'id': 'FAKE_FLOATING_ID',
            },
            'id': 'FAKE_PORT_ID',
            'remove': True
        }]}

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, obj)

        mock_node_obj.assert_called_once_with(mock.ANY, obj.id,
                                              {'data': obj.data})
        self.assertEqual("Failed in deleting server 'FAKE_ID': "
                         "Nova Error.", str(ex))
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        self.assertEqual(0, cc.wait_for_server_delete.call_count)
        nc.port_delete.assert_called_once_with('FAKE_PORT_ID')

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_with_force_delete_failure(self, mock_node_obj):
        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc

        err = exc.InternalError(code=500, message='Nova Error')
        cc.server_force_delete.side_effect = err
        obj = mock.Mock(physical_id='FAKE_ID')
        obj.data = {}

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, obj, force=True)

        mock_node_obj.assert_not_called()
        self.assertEqual("Failed in deleting server 'FAKE_ID': "
                         "Nova Error.", str(ex))
        cc.server_force_delete.assert_called_once_with('FAKE_ID', True)
        self.assertEqual(0, cc.wait_for_server_delete.call_count)
        nc.port_delete.assert_not_called()

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_wait_for_server_timeout(self, mock_node_obj):
        cc = mock.Mock()
        nc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc

        err = exc.InternalError(code=500, message='TIMEOUT')
        cc.wait_for_server_delete.side_effect = err
        obj = mock.Mock(physical_id='FAKE_ID')
        obj.data = {'internal_ports': [{
            'floating': {
                'remove': True,
                'id': 'FAKE_FLOATING_ID',
            },
            'id': 'FAKE_PORT_ID',
            'remove': True
        }]}

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, obj, timeout=20)

        mock_node_obj.assert_called_once_with(mock.ANY, obj.id,
                                              {'data': obj.data})
        self.assertEqual("Failed in deleting server 'FAKE_ID': TIMEOUT.",
                         str(ex))
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with('FAKE_ID',
                                                          timeout=20)
        nc.port_delete.assert_called_once_with('FAKE_PORT_ID')

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_wait_for_server_timeout_delete_ports(
            self, mock_node_obj):
        cc = mock.Mock()
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.return_value = None
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc

        test_server = mock.Mock(physical_id='FAKE_ID')
        test_server.Node = mock.Mock()
        test_server.data = {'internal_ports': [{
            'floating': {
                'remove': True,
                'id': 'FAKE_FLOATING_ID',
            },
            'id': 'FAKE_PORT_ID',
            'remove': True
        }]}

        err = exc.InternalError(code=500, message='TIMEOUT')
        cc.wait_for_server_delete.side_effect = err

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, test_server, timeout=20)

        self.assertEqual("Failed in deleting server 'FAKE_ID': TIMEOUT.",
                         str(ex))
        mock_node_obj.assert_called_once_with(
            mock.ANY, test_server.id, {'data': {'internal_ports': []}})
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with('FAKE_ID',
                                                          timeout=20)
        nc.port_delete.assert_called_once_with('FAKE_PORT_ID')

    @mock.patch.object(node_ob.Node, 'update')
    def test_do_delete_wait_for_server_timeout_no_internal_ports(
            self, mock_node_obj):
        cc = mock.Mock()
        nc = mock.Mock()
        nc.port_delete.return_value = None
        nc.floatingip_delete.return_value = None
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc

        test_server = mock.Mock(physical_id='FAKE_ID')
        test_server.Node = mock.Mock()
        test_server.data = {}

        err = exc.InternalError(code=500, message='TIMEOUT')
        cc.wait_for_server_delete.side_effect = err

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, test_server, timeout=20)

        self.assertEqual("Failed in deleting server 'FAKE_ID': TIMEOUT.",
                         str(ex))
        mock_node_obj.assert_not_called()
        cc.server_delete.assert_called_once_with('FAKE_ID', True)
        cc.wait_for_server_delete.assert_called_once_with('FAKE_ID',
                                                          timeout=20)
        nc.port_delete.assert_not_called()

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
                'name': 'FAKE_FLAVOR',
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
            'attached_volumes': [{
                'id': 'FAKE_VOLUME',
            }],
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
            'progress': 0,
            'security_groups': [{'name': 'default'}],
            'status': 'FAKE_STATUS',
            'tenant_id': 'FAKE_TENANT',
            'updated': 'UPDATE_TIMESTAMP',
            'user_id': 'FAKE_USER_ID',
        }
        cc.server_get.return_value = nova_server
        cc.flavor_find.return_value = mock.Mock(id='1')
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
            'attached_volumes': ['FAKE_VOLUME'],
            'key_name': 'FAKE_KEY',
            'metadata': {},
            'name': 'FAKE_NAME',
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
            'attached_volumes': [{
                'id': 'FAKE_VOLUME',
            }],
            'security_groups': [],
        }
        cc.server_get.return_value = nova_server
        cc.flavor_find.return_value = mock.Mock(id='FAKE_FLAVOR')
        res = profile.do_get_details(node_obj)
        expected = {
            'flavor': 'FAKE_FLAVOR',
            'id': 'FAKE_ID',
            'image': 'FAKE_IMAGE',
            'attached_volumes': ['FAKE_VOLUME'],
            'addresses': {},
            'security_groups': '',
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_flavor_no_id_key(self):
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
                }]
            },
            'flavor': {
                'original_name': 'FAKE_FLAVOR',
            },
            'id': 'FAKE_ID',
            'image': {},
            'attached_volumes': [{
                'id': 'FAKE_VOLUME',
            }],
            'security_groups': [{'name': 'default'}],
        }
        cc.server_get.return_value = nova_server
        cc.flavor_find.return_value = mock.PropertyMock(id='FAKE_FLAVOR_ID')

        res = profile.do_get_details(node_obj)
        expected = {
            'flavor': 'FAKE_FLAVOR_ID',
            'id': 'FAKE_ID',
            'image': {},
            'attached_volumes': ['FAKE_VOLUME'],
            'addresses': {
                'private': [{
                    'version': 4,
                    'addr': '10.0.0.3',
                }]
            },
            'security_groups': 'default',
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_image_no_id_key(self):
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
                }]
            },
            'flavor': {
                'id': '1',
                'name': 'FAKE_FLAVOR'
            },
            'id': 'FAKE_ID',
            'image': {},
            'attached_volumes': [{
                'id': 'FAKE_VOLUME',
            }],
            'security_groups': [{'name': 'default'}],
        }
        cc.server_get.return_value = nova_server
        cc.flavor_find.return_value = mock.Mock(id='1')
        res = profile.do_get_details(node_obj)
        expected = {
            'flavor': '1',
            'id': 'FAKE_ID',
            'image': {},
            'attached_volumes': ['FAKE_VOLUME'],
            'addresses': {
                'private': [{
                    'version': 4,
                    'addr': '10.0.0.3',
                }]
            },
            'security_groups': 'default',
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_bdm_no_id_key(self):
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
                }]
            },
            'flavor': {
                'id': 'FAKE_FLAVOR',
            },
            'id': 'FAKE_ID',
            'image': {},
            'attached_volumes': [],
            'security_groups': [{'name': 'default'}],
        }
        cc.server_get.return_value = nova_server
        cc.flavor_find.return_value = mock.Mock(id='FAKE_FLAVOR')
        res = profile.do_get_details(node_obj)
        expected = {
            'flavor': 'FAKE_FLAVOR',
            'id': 'FAKE_ID',
            'image': {},
            'attached_volumes': [],
            'addresses': {
                'private': [{
                    'version': 4,
                    'addr': '10.0.0.3',
                }]
            },
            'security_groups': 'default',
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
        data = {
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
            'attached_volumes': [{
                'id': 'FAKE_VOLUME',
            }],
            'security_groups': [{
                'name': 'default',
            }, {
                'name': 'webserver',
            }],
        }
        nova_server.to_dict.return_value = data
        cc.server_get.return_value = nova_server

        res = profile.do_get_details(node_obj)

        self.assertEqual(set(data['addresses']), set(res['addresses']))
        self.assertEqual(set(['default', 'webserver']),
                         set(res['security_groups']))
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

    def test_do_adopt(self):
        profile = server.ServerProfile('t', self.spec)
        x_server = mock.Mock(
            disk_config="",
            availability_zone="AZ01",
            block_device_mapping={"foo": "bar"},
            has_config_drive=False,
            flavor={"id": "FLAVOR_ID"},
            image={"id": "IMAGE_ID"},
            key_name="FAKE_KEY",
            metadata={
                "mkey": "mvalue",
                "cluster_id": "CLUSTER_ID",
                "cluster_node_id": "NODE_ID",
                "cluster_node_index": 123
            },
            addresses={
                "NET1": [{
                    "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:09:6f:d8",
                    "OS-EXT-IPS:type": "fixed",
                    "addr": "ADDR1_IPv4",
                    "version": 4
                }, {
                    "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:09:6f:d8",
                    "OS-EXT-IPS:type": "fixed",
                    "addr": "ADDR1_IPv6",
                    "version": 6
                }],
                "NET2": [{
                    "OS-EXT-IPS-MAC:mac_addr": "aa:e6:3e:09:6f:db",
                    "OS-EXT-IPS:type": "fixed",
                    "addr": "ADDR2_IPv4",
                    "version": 4
                }, {
                    "OS-EXT-IPS-MAC:mac_addr": "aa:e6:3e:09:6f:db",
                    "OS-EXT-IPS:type": "fixed",
                    "addr": "ADDR2_IPv6",
                    "version": 6
                }],
            },
            security_groups=[{'name': 'GROUP1'}, {'name': 'GROUP2'}]
        )
        x_server.name = "FAKE_NAME"
        cc = mock.Mock()
        cc.server_get.return_value = x_server
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_adopt(node_obj)

        self.assertEqual(False, res['auto_disk_config'])
        self.assertEqual('AZ01', res['availability_zone'])
        self.assertEqual({'foo': 'bar'}, res['block_device_mapping_v2'])
        self.assertFalse(res['config_drive'])
        self.assertEqual('FLAVOR_ID', res['flavor'])
        self.assertEqual('IMAGE_ID', res['image'])
        self.assertEqual('FAKE_KEY', res['key_name'])
        self.assertEqual({'mkey': 'mvalue'}, res['metadata'])

        self.assertEqual(2, len(res['networks']))
        self.assertIn({'network': 'NET1'}, res['networks'])
        self.assertIn({'network': 'NET2'}, res['networks'])
        self.assertIn('GROUP1', res['security_groups'])
        self.assertIn('GROUP2', res['security_groups'])
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_adopt_failed_get(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        err = exc.InternalError(code=404, message='No Server found for ID')
        cc.server_get.side_effect = err
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_adopt(node_obj)

        expected = {
            'Error': {
                'code': 404,
                'message': 'No Server found for ID',
            }
        }
        self.assertEqual(expected, res)
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_adopt_with_overrides(self):
        profile = server.ServerProfile('t', self.spec)
        x_server = mock.Mock(
            disk_config="",
            availability_zone="AZ01",
            block_device_mapping={"foo": "bar"},
            has_config_drive=False,
            flavor={"id": "FLAVOR_ID"},
            image={"id": "IMAGE_ID"},
            key_name="FAKE_KEY",
            metadata={
                "mkey": "mvalue",
                "cluster_id": "CLUSTER_ID",
                "cluster_node_id": "NODE_ID",
                "cluster_node_index": 123
            },
            addresses={
                "NET1": [{
                    "OS-EXT-IPS:type": "fixed",
                }],
                "NET2": [{
                    "OS-EXT-IPS:type": "fixed",
                }],
            },
            security_groups=[{'name': 'GROUP1'}, {'name': 'GROUP2'}]
        )
        x_server.name = "FAKE_NAME"
        cc = mock.Mock()
        cc.server_get.return_value = x_server
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')
        overrides = {
            'networks': [{"network": "NET3"}]
        }

        res = profile.do_adopt(node_obj, overrides=overrides)

        self.assertEqual(False, res['auto_disk_config'])
        self.assertEqual('AZ01', res['availability_zone'])
        self.assertEqual({'foo': 'bar'}, res['block_device_mapping_v2'])
        self.assertFalse(res['config_drive'])
        self.assertEqual('FLAVOR_ID', res['flavor'])
        self.assertEqual('IMAGE_ID', res['image'])
        self.assertEqual('FAKE_KEY', res['key_name'])
        self.assertEqual({'mkey': 'mvalue'}, res['metadata'])
        self.assertIn({'network': 'NET3'}, res['networks'])
        self.assertNotIn({'network': 'NET1'}, res['networks'])
        self.assertNotIn({'network': 'NET2'}, res['networks'])
        self.assertIn('GROUP1', res['security_groups'])
        self.assertIn('GROUP2', res['security_groups'])
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_join_successful(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        metadata = {}
        cc.server_metadata_get.return_value = metadata
        profile._computeclient = cc

        node_obj = mock.Mock(physical_id='FAKE_ID', index='123')
        res = profile.do_join(node_obj, 'FAKE_CLUSTER_ID')
        self.assertTrue(res)

        meta = {'cluster_id': 'FAKE_CLUSTER_ID',
                'cluster_node_index': '123'}
        cc.server_metadata_update.assert_called_once_with(
            'FAKE_ID', meta)

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

    def test_do_check_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.do_check(obj)

        self.assertFalse(res)

    def test_do_check_no_server(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        err = exc.InternalError(code=404, message='No Server found')
        cc.server_get.side_effect = err
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EServerNotFound,
                               profile.do_check,
                               node_obj)

        self.assertEqual("Failed in found server 'FAKE_ID': "
                         "No Server found.",
                         str(ex))
        cc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_healthcheck_active(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = mock.Mock(status='ACTIVE')
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server, consts.NODE_STATUS_POLLING)
        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertTrue(res)

    def test_do_healthcheck_empty_server_obj(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = None
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server, consts.NODE_STATUS_POLLING)
        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertTrue(res)

    def test_do_healthcheck_exception(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        ex = exc.InternalError(code=503, message='Error')
        cc.server_get.side_effect = ex
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server, consts.NODE_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertTrue(res)

    def test_do_healthcheck_error(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = mock.Mock(status='ERROR')
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server, consts.NODE_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertFalse(res)

    def test_do_healthcheck_server_not_found(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        ex = exc.InternalError(code=404, message='No Server found')
        cc.server_get.side_effect = ex
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server, consts.NODE_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertFalse(res)

    def test_do_healthcheck_empty_hv_name(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.hypervisor_find.return_value = None
        cc.server_get.return_value = mock.Mock(hypervisor_hostname='')
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server,
                                     consts.HYPERVISOR_STATUS_POLLING)
        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.hypervisor_find.assert_not_called()
        self.assertTrue(res)

    def test_do_healthcheck_empty_hv_obj(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.hypervisor_find.return_value = None
        cc.server_get.return_value = mock.Mock(hypervisor_hostname='FAKE_HV')
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server,
                                     consts.HYPERVISOR_STATUS_POLLING)
        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.hypervisor_find.assert_called_once_with('FAKE_HV')
        self.assertTrue(res)

    def test_do_healthcheck_hv_exception(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = mock.Mock(hypervisor_hostname='FAKE_HV')
        ex = exc.InternalError(code=503, message='Error')
        cc.hypervisor_find.side_effect = ex
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server,
                                     consts.HYPERVISOR_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.hypervisor_find.assert_called_once_with('FAKE_HV')
        self.assertTrue(res)

    def test_do_healthcheck_hv_not_found(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = mock.Mock(hypervisor_hostname='FAKE_HV')
        ex = exc.InternalError(code=404, message='No Hypervisor found')
        cc.hypervisor_find.side_effect = ex
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server,
                                     consts.HYPERVISOR_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.hypervisor_find.assert_called_once_with('FAKE_HV')
        self.assertFalse(res)

    def test_do_healthcheck_hv_down(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = mock.Mock(hypervisor_hostname='FAKE_HV')
        cc.hypervisor_find.return_value = mock.Mock(state='down')
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server,
                                     consts.HYPERVISOR_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.hypervisor_find.assert_called_once_with('FAKE_HV')
        self.assertFalse(res)

    def test_do_healthcheck_hv_disabled(self):
        profile = server.ServerProfile('t', self.spec)

        cc = mock.Mock()
        cc.server_get.return_value = mock.Mock(hypervisor_hostname='FAKE_HV')
        cc.hypervisor_find.return_value = mock.Mock(status='disabled')
        profile._computeclient = cc

        test_server = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_healthcheck(test_server,
                                     consts.HYPERVISOR_STATUS_POLLING)

        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.hypervisor_find.assert_called_once_with('FAKE_HV')
        self.assertFalse(res)

    @mock.patch.object(server.ServerProfile, 'do_delete')
    @mock.patch.object(server.ServerProfile, 'do_create')
    def test_do_recover_operation_is_none(self, mock_create, mock_delete):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        mock_delete.return_value = None
        mock_create.return_value = True

        res = profile.do_recover(node_obj, operation=None)

        self.assertTrue(res)
        mock_delete.assert_called_once_with(node_obj, force=False,
                                            timeout=None)
        mock_create.assert_called_once_with(node_obj)

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

        res = profile.do_recover(node_obj, operation='REBUILD')

        self.assertEqual(mock_rebuild.return_value, res)
        mock_rebuild.assert_called_once_with(node_obj)

    @mock.patch.object(server.ServerProfile, 'handle_reboot')
    def test_do_recover_reboot(self, mock_reboot):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_recover(node_obj, operation='REBOOT')

        self.assertTrue(res)
        self.assertEqual(mock_reboot.return_value, res)
        mock_reboot.assert_called_once_with(node_obj, type='HARD')

    @mock.patch.object(profiles_base.Profile, 'do_recover')
    def test_do_recover_bad_operation(self, mock_base_recover):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res, status = profile.do_recover(node_obj,
                                         operation='BLAHBLAH')

        self.assertFalse(status)

    @mock.patch.object(profiles_base.Profile, 'do_recover')
    def test_do_recover_fallback(self, mock_base_recover):
        profile = server.ServerProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_recover(node_obj, operation='RECREATE')

        self.assertEqual(mock_base_recover.return_value, res)
        mock_base_recover.assert_called_once_with(
            node_obj, operation='RECREATE')

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
        res, status = profile.handle_reboot(obj, type='SOFT')

        self.assertFalse(status)

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
        res, status = profile.handle_reboot(obj, type=['foo'])
        self.assertFalse(status)

        res, status = profile.handle_reboot(obj, type='foo')
        self.assertFalse(status)

    def test_handle_rebuild_with_image(self):
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

    def test_handle_rebuild_with_bdm(self):
        bdm_v2 = [
            {
                'volume_size': 1,
                'uuid': '123',
                'source_type': 'image',
                'destination_type': 'volume',
                'boot_index': 0,
            }
        ]
        spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAV',
                'admin_pass': 'adminpass',
                'name': 'FAKE_SERVER_NAME',
                'security_groups': ['HIGH_SECURITY_GROUP'],
                'block_device_mapping_v2': bdm_v2,
            }
        }
        profile = server.ServerProfile('t', spec)
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
                         str(ex))
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
                         str(ex))
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
                         "timeout.", str(ex))
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

        res, status = profile.handle_rebuild(node_obj)

        self.assertFalse(status)
        cc.server_get.assert_called_once_with('FAKE_ID')
        self.assertEqual(0, cc.server_rebuild.call_count)
        self.assertEqual(0, cc.wait_for_server.call_count)

    def test_handle_rebuild_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        test_server = mock.Mock()
        test_server.physical_id = None

        res, status = profile.handle_rebuild(test_server)

        self.assertFalse(status)

    def test_handle_rebuild_failed_with_name(self):
        self.spec['properties']['name'] = None
        profile = server.ServerProfile('t', self.spec)
        x_image = {'id': '123'}
        x_server = mock.Mock(image=x_image)
        cc = mock.Mock()
        cc.server_get.return_value = x_server
        ex = exc.InternalError(code=400,
                               message='Server name is not '
                                       'a string or unicode.')
        cc.server_rebuild.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')
        node_obj.name = None

        ex = self.assertRaises(exc.ESchema,
                               profile.handle_rebuild,
                               node_obj)

        self.assertEqual("The value 'None' is not a valid string.",
                         str(ex))
        cc.server_get.assert_called_once_with('FAKE_ID')
        cc.server_rebuild.assert_not_called()
        self.assertEqual(0, cc.wait_for_server.call_count)

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
        cc.server_change_password.assert_called_once_with(
            'FAKE_ID', new_password='new_pass')

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

    def test_handle_suspend(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_suspend(obj)
        self.assertTrue(res)

    def test_handle_suspend_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_suspend(obj)
        self.assertFalse(res)

    def test_handle_suspend_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_suspend,
                               node_obj)

        self.assertEqual("Failed in suspend server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_suspend.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'SUSPENDED')

    def test_handle_resume(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_resume(obj)
        self.assertTrue(res)

    def test_handle_resume_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_resume(obj)
        self.assertFalse(res)

    def test_handle_resume_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_resume,
                               node_obj)

        self.assertEqual("Failed in resume server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_resume.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_start(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_start(obj)
        self.assertTrue(res)

    def test_handle_start_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_start(obj)
        self.assertFalse(res)

    def test_handle_start_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_start,
                               node_obj)

        self.assertEqual("Failed in start server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_start.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_stop(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_stop(obj)
        self.assertTrue(res)

    def test_handle_stop_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_stop(obj)
        self.assertFalse(res)

    def test_handle_stop_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_stop,
                               node_obj)

        self.assertEqual("Failed in stop server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_stop.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'SHUTOFF')

    def test_handle_lock(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_lock(obj)
        self.assertTrue(res)

    def test_handle_lock_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_lock(obj)
        self.assertFalse(res)

    def test_handle_unlock(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_unlock(obj)
        self.assertTrue(res)

    def test_handle_unlock_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_unlock(obj)
        self.assertFalse(res)

    def test_handle_pause(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_pause(obj)
        self.assertTrue(res)

    def test_handle_pause_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_pause(obj)
        self.assertFalse(res)

    def test_handle_pause_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_pause,
                               node_obj)

        self.assertEqual("Failed in pause server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_pause.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'PAUSED')

    def test_handle_unpause(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_unpause(obj)
        self.assertTrue(res)

    def test_handle_unpause_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_unpause(obj)
        self.assertFalse(res)

    def test_handle_unpause_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_unpause,
                               node_obj)

        self.assertEqual("Failed in unpause server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_unpause.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_rescue(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        gc = mock.Mock()
        profile._computeclient = cc
        profile._glanceclient = gc

        # do it
        res = profile.handle_rescue(obj, admin_pass='new_pass',
                                    image='FAKE_IMAGE')

        self.assertTrue(res)
        cc.server_rescue.assert_called_once_with(
            'FAKE_ID', admin_pass='new_pass', image_ref='FAKE_IMAGE')
        gc.image_find.assert_called_once_with('FAKE_IMAGE', False)

    def test_handle_rescue_image_none(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc

        res = profile.handle_rescue(obj, admin_pass='new_pass',
                                    image=None)
        self.assertFalse(res)

    def test_handle_rescue_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_rescue(obj)
        self.assertFalse(res)

    def test_handle_rescue_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        gc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        profile._glanceclient = gc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_rescue,
                               node_obj, admin_pass='new_pass',
                               image='FAKE_IMAGE')

        self.assertEqual("Failed in rescue server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_rescue.assert_called_once_with('FAKE_ID',
                                                 admin_pass='new_pass',
                                                 image_ref='FAKE_IMAGE')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'RESCUE')
        gc.image_find.assert_called_once_with('FAKE_IMAGE', False)

    def test_handle_unrescue(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_unrescue(obj)
        self.assertTrue(res)

    def test_handle_unresuce_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_unrescue(obj)
        self.assertFalse(res)

    def test_handle_unrescue_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_unrescue,
                               node_obj)

        self.assertEqual("Failed in unrescue server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_unrescue.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_migrate(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_migrate(obj)
        self.assertTrue(res)

    def test_handle_migrate_no_physical_id(self):
        obj = mock.Mock(physical_id=None)
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_migrate(obj)
        self.assertFalse(res)

    def test_handle_migrate_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_migrate,
                               node_obj)

        self.assertEqual("Failed in migrate server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.server_migrate.assert_called_once_with('FAKE_ID')
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_snapshot(self):
        obj = mock.Mock(physical_id='FAKE_ID', name='NODE001')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        # do it
        res = profile.handle_snapshot(obj)
        self.assertTrue(res)

    def test_handle_snapshot_no_physical_id(self):
        obj = mock.Mock(physical_id=None, name='NODE001')
        profile = server.ServerProfile('t', self.spec)

        # do it
        res = profile.handle_snapshot(obj)
        self.assertFalse(res)

    def test_handle_snapshot_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock(name='NODE001')
        ex = exc.InternalError(code=500, message='timeout')
        cc.wait_for_server.side_effect = ex
        profile._computeclient = cc
        node_obj = mock.Mock(physical_id='FAKE_ID', name='NODE001')

        ex = self.assertRaises(exc.EResourceOperation,
                               profile.handle_snapshot,
                               node_obj)

        self.assertEqual("Failed in snapshot server 'FAKE_ID': "
                         "timeout.", str(ex))
        cc.wait_for_server.assert_called_once_with('FAKE_ID', 'ACTIVE')

    def test_handle_restore(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc

        # do it
        res = profile.handle_restore(obj, admin_pass='new_pass',
                                     image='FAKE_IMAGE')

        self.assertTrue(res)

    def test_handle_restore_image_none(self):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc

        res = profile.handle_restore(obj, admin_pass='new_pass',
                                     image=None)
        self.assertFalse(res)
