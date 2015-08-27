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

from senlin.common import exception
from senlin.common import utils as common_utils
from senlin.drivers import base as driver_base
from senlin.profiles.os.nova import server
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNovaServerProfile(base.SenlinTestCase):

    def setUp(self):
        super(TestNovaServerProfile, self).setUp()

        self.context = utils.dummy_context()
        self.spec = {
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
            'timeout': 120,
            'user_data': 'FAKE_USER_DATA',
        }

    def test_nova_init(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('os.nova.server',
                                       'test-profile',
                                       **kwargs)

        self.assertIsNone(profile._novaclient)
        self.assertIsNone(profile._neutronclient)
        self.assertIsNone(profile.server_id)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_nova_client(self, mock_senlindriver):
        test_server = mock.Mock()
        sd = mock.Mock()
        nc = mock.Mock()
        sd.compute.return_value = nc
        mock_senlindriver.return_value = sd

        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('os.nova.server',
                                       'test-profile',
                                       **kwargs)

        # cached will be returned
        profile._novaclient = nc
        self.assertEqual(nc, profile.nova(test_server))

        # new nc created if no cache found
        profile._novaclient = None
        params = mock.Mock()
        mock_param = self.patchobject(profile, '_build_connection_params',
                                      return_value=params)
        res = profile.nova(test_server)
        self.assertEqual(nc, res)
        self.assertEqual(nc, profile._novaclient)
        mock_param.assert_called_once_with(mock.ANY, test_server)
        sd.compute.assert_called_once_with(params)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_neutron_client(self, mock_senlindriver):
        test_server = mock.Mock()
        sd = mock.Mock()
        nc = mock.Mock()
        sd.network.return_value = nc
        mock_senlindriver.return_value = sd

        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('os.nova.server',
                                       'test-profile',
                                       **kwargs)

        # cached will be returned
        profile._neutronclient = nc
        self.assertEqual(nc, profile.neutron(test_server))

        # new nc created if no cache found
        profile._neutronclient = None
        params = mock.Mock()
        mock_param = self.patchobject(profile, '_build_connection_params',
                                      return_value=params)
        res = profile.neutron(test_server)
        self.assertEqual(nc, res)
        self.assertEqual(nc, profile._neutronclient)
        mock_param.assert_called_once_with(mock.ANY, test_server)
        sd.network.assert_called_once_with(params)

    def test_do_validate(self):
        profile = server.ServerProfile('os.nova.server', 't', spec=self.spec)
        res = profile.do_validate(mock.Mock())
        self.assertTrue(res)

    @mock.patch.object(common_utils, 'random_name')
    def test_do_create(self, mock_random_name):
        mock_random_name.return_value = '12345678'
        novaclient = mock.Mock()
        neutronclient = mock.Mock()
        test_server = mock.Mock()
        test_server.name = 'TEST_SERVER'
        test_server.cluster_id = 'FAKE_CLUSTER_ID'
        image = mock.Mock()
        image.id = 'FAKE_IMAGE_ID'
        novaclient.image_get_by_name.return_value = image
        flavor = mock.Mock()
        flavor.id = 'FAKE_FLAVOR_ID'
        novaclient.flavor_find.return_value = flavor
        net = mock.Mock()
        net.id = 'FAKE_NETWORK_ID'
        neutronclient.network_get.return_value = net

        nova_server = mock.Mock()
        nova_server.id = 'FAKE_NOVA_SERVER_ID'
        novaclient.server_create.return_value = nova_server

        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = novaclient
        profile._neutronclient = neutronclient
        server_id = profile.do_create(test_server)

        mock_random_name.assert_called_once_with(8)
        novaclient.image_get_by_name.assert_called_once_with('FAKE_IMAGE')
        novaclient.flavor_find.assert_called_once_with('FLAV', False)
        neutronclient.network_get.assert_called_once_with('FAKE_NET')

        attrs = dict(adminPass='adminpass',
                     auto_disk_config=True,
                     availability_zone='FAKE_AZ',
                     block_device_mapping=[{
                         'volume_size': 1000,
                         'device_name': 'FAKE_NAME'
                     }],
                     config_drive=False,
                     flavorRef='FAKE_FLAVOR_ID',
                     imageRef='FAKE_IMAGE_ID',
                     key_name='FAKE_KEYNAME',
                     metadata={
                         'cluster': 'FAKE_CLUSTER_ID',
                         'meta var': 'meta val'
                     },
                     name='TEST_SERVER-12345678',
                     networks=[{
                         'fixed-ip': 'FAKE_IP',
                         'port': 'FAKE_PORT',
                         'uuid': 'FAKE_NETWORK_ID',
                     }],
                     personality=[{
                         'path': '/etc/motd',
                         'contents': 'foo'
                     }],
                     scheduler_hints={
                         'same_host': 'HOST_ID'
                     },
                     security_groups=['HIGH_SECURITY_GROUP'],
                     timeout=120,
                     user_data='FAKE_USER_DATA')

        ud = encodeutils.safe_encode('FAKE_USER_DATA')
        attrs['user_data'] = encodeutils.safe_decode(base64.b64encode(ud))

        novaclient.server_create.assert_called_once_with(**attrs)
        self.assertEqual(nova_server.id, server_id)

    @mock.patch.object(common_utils, 'random_name')
    def test_do_create_server_attrs_not_defined(self, mock_random_name):
        mock_random_name.return_value = '12345678'
        novaclient = mock.Mock()
        neutronclient = mock.Mock()
        test_server = mock.Mock()
        test_server.name = 'TEST_SERVER'
        test_server.cluster_id = 'FAKE_CLUSTER_ID'
        flavor = mock.Mock()
        flavor.id = 'FAKE_FLAVOR_ID'
        novaclient.flavor_find.return_value = flavor
        net = mock.Mock()
        net.id = 'FAKE_NETWORK_ID'
        neutronclient.network_get.return_value = net

        nova_server = mock.Mock()
        nova_server.id = 'FAKE_NOVA_SERVER_ID'
        novaclient.server_create.return_value = nova_server

        # Assume image/scheduler_hints/user_data were not defined in spec file
        spec = {
            'flavor': 'FLAV',
            'name': 'FAKE_SERVER_NAME',
            'security_groups': ['HIGH_SECURITY_GROUP'],
            'timeout': 120,
        }

        profile = server.ServerProfile('os.nova.server', 's1', spec=spec)
        profile._novaclient = novaclient
        profile._neutronclient = neutronclient
        server_id = profile.do_create(test_server)

        mock_random_name.assert_called_once_with(8)
        attrs = dict(auto_disk_config=True,
                     flavorRef='FAKE_FLAVOR_ID',
                     name='TEST_SERVER-12345678',
                     metadata={
                         'cluster': 'FAKE_CLUSTER_ID',
                     },
                     security_groups=['HIGH_SECURITY_GROUP'],
                     timeout=120)

        novaclient.server_create.assert_called_once_with(**attrs)
        self.assertEqual(nova_server.id, server_id)

    def test_do_create_obj_name_cluster_id_is_none(self):
        novaclient = mock.Mock()
        neutronclient = mock.Mock()
        test_server = mock.Mock()
        test_server.name = None
        test_server.cluster_id = None
        flavor = mock.Mock()
        flavor.id = 'FAKE_FLAVOR_ID'
        novaclient.flavor_find.return_value = flavor
        net = mock.Mock()
        net.id = 'FAKE_NETWORK_ID'
        neutronclient.network_get.return_value = net

        nova_server = mock.Mock()
        nova_server.id = 'FAKE_NOVA_SERVER_ID'
        novaclient.server_create.return_value = nova_server

        spec = {
            'flavor': 'FLAV',
            'name': 'FAKE_SERVER_NAME',
            'security_groups': ['HIGH_SECURITY_GROUP'],
            'timeout': 120,
        }

        profile = server.ServerProfile('os.nova.server', 's1', spec=spec)
        profile._novaclient = novaclient
        profile._neutronclient = neutronclient
        server_id = profile.do_create(test_server)

        attrs = dict(auto_disk_config=True,
                     flavorRef='FAKE_FLAVOR_ID',
                     name='FAKE_SERVER_NAME',
                     metadata={},
                     security_groups=['HIGH_SECURITY_GROUP'],
                     timeout=120)

        novaclient.server_create.assert_called_once_with(**attrs)
        self.assertEqual(nova_server.id, server_id)

    def test_do_create_wait_for_server_timeout(self):
        novaclient = mock.Mock()
        neutronclient = mock.Mock()
        test_server = mock.Mock()
        test_server.name = None
        test_server.cluster_id = None
        flavor = mock.Mock()
        flavor.id = 'FAKE_FLAVOR_ID'
        novaclient.flavor_find.return_value = flavor
        net = mock.Mock()
        net.id = 'FAKE_NETWORK_ID'
        neutronclient.network_get.return_value = net

        nova_server = mock.Mock()
        novaclient.server_create.return_value = nova_server
        novaclient.wait_for_server.side_effect = exception.InternalError(
            code=500, message='timeout')

        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = novaclient
        profile._neutronclient = neutronclient
        res = profile.do_create(test_server)
        self.assertFalse(res)
        novaclient.wait_for_server.assert_called_once_with(nova_server)

    def test_do_delete_no_physical_id(self):
        # Test path where server doesn't already exist
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc
        test_server = mock.Mock()
        test_server.physical_id = None

        self.assertTrue(profile.do_delete(test_server))

    def test_do_delete_successful(self):
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)

        nc = mock.Mock()
        nc.server_delete.return_value = None
        profile._novaclient = nc

        test_server = mock.Mock()
        test_server.physical_id = 'FAKE_ID'

        res = profile.do_delete(test_server)
        self.assertTrue(res)

    def test_do_delete_wait_for_server_delete_timeout(self):
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'
        nc.wait_for_server_delete.side_effect = exception.InternalError(
            code=500, message='timeout')

        res = profile.do_delete(obj)
        self.assertFalse(res)
        nc.wait_for_server_delete.assert_called_once_with('FAKE_ID')

    def test_do_delete_with_delete_exception(self):
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc

        err = exception.ProfileOperationTimeout(message='exception')
        nc.server_delete.side_effect = err

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        # Test specific exception path
        res = profile.do_delete(obj)
        self.assertFalse(res)
        nc.server_delete.assert_called_once_with('FAKE_ID')

    def test_do_update_successful(self):
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = mock.Mock()

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        new_profile = mock.Mock()

        # Test path for an existing server
        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)

    def test_do_update_no_physical_id(self):
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = mock.Mock()

        test_server = mock.Mock()
        test_server.physical_id = None

        new_profile = mock.Mock()

        # Test path where server doesn't already exist
        res = profile.do_update(test_server, new_profile)
        self.assertTrue(res)

    def test_do_check(self):
        # Not implemented in server profile yet.
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        res = profile.do_check(mock.Mock())
        self.assertTrue(res)

    def test_do_get_details(self):
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc
        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        # Test normal path
        nova_server = mock.Mock()
        nova_server.id = 'FAKE_ID'
        nova_server.name = 'FAKE_NAME'
        nova_server.access_ipv4 = 'FAKE_IPV4'
        nova_server.access_ipv6 = 'FAKE_IPV6'
        nova_server.addresses = 'FAKE_ADDRESSES'
        nova_server.created_at = 'FAKE_CREATED'
        nova_server.flavor = 'FAKE_FLAVOR'
        nova_server.host_id = 'FAKE_HOST'
        nova_server.image = 'FAKE_IMAGE'
        nova_server.links = 'FAKE_LINKS'
        nova_server.metadata = 'FAKE_METADATA'
        nova_server.progress = 'FAKE_PROGRESS'
        nova_server.project_id = 'FAKE_PROJECT_ID'
        nova_server.status = 'FAKE_STATUS'
        nova_server.updated_at = 'FAKE_UPDATED'
        nova_server.user_id = 'FAKE_USER_ID'

        nc.server_get.return_value = nova_server
        res = profile.do_get_details(obj)
        expected = {
            'id': 'FAKE_ID',
            'name': 'FAKE_NAME',
            'access_ipv4': 'FAKE_IPV4',
            'access_ipv6': 'FAKE_IPV6',
            'addresses': 'FAKE_ADDRESSES',
            'created_at': 'FAKE_CREATED',
            'flavor': 'FAKE_FLAVOR',
            'host_id': 'FAKE_HOST',
            'image': 'FAKE_IMAGE',
            'links': 'FAKE_LINKS',
            'metadata': 'FAKE_METADATA',
            'progress': 'FAKE_PROGRESS',
            'project_id': 'FAKE_PROJECT_ID',
            'status': 'FAKE_STATUS',
            'updated_at': 'FAKE_UPDATED',
            'user_id': 'FAKE_USER_ID',
        }
        self.assertEqual(expected, res)
        nc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_no_physical_id(self):
        # Test path for server not created
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        obj = mock.Mock()
        obj.physical_id = ''
        self.assertEqual({}, profile.do_get_details(obj))

        obj.physical_id = None
        self.assertEqual({}, profile.do_get_details(obj))

    def test_do_get_details_server_not_found(self):
        # Test path for server not created
        nc = mock.Mock()
        nc.server_get.return_value = None
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc
        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        res = profile.do_get_details(obj)
        self.assertEqual({}, res)
        nc.server_get.assert_called_once_with('FAKE_ID')

    def test_do_join_successful(self):
        # Test normal path
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc
        nc.server_metadata_get.return_value = {'FOO': 'BAR'}
        nc.server_metadata_update.return_value = 'Boom'

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'
        cluster_id = "FAKE_CLUSTER_ID"

        res = profile.do_join(obj, cluster_id)
        self.assertEqual('Boom', res)
        nc.server_metadata_get.assert_called_once_with(server_id='FAKE_ID')
        nc.server_metadata_update.assert_called_once_with(
            FOO='BAR', cluster='FAKE_CLUSTER_ID')

    def test_do_join_server_not_created(self):
        # Test path where server not specified
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        obj = mock.Mock()
        obj.physical_id = None

        res = profile.do_join(obj, 'FAKE_CLUSTER_ID')
        self.assertEqual({}, res)

    def test_do_leave_successful(self):
        # Test normal path
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc
        nc.server_metadata_get.return_value = {'FOO': 'BAR', 'cluster': 'CLS'}
        nc.server_metadata_update.return_value = 'Boom'

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'
        obj.cluster_id = 'FAKE_CLUSTER_ID'

        res = profile.do_leave(obj)
        self.assertEqual('Boom', res)
        nc.server_metadata_get.assert_called_once_with(server_id='FAKE_ID')
        nc.server_metadata_update.assert_called_once_with(FOO='BAR')

    def test_do_leave_no_physical_id(self):
        # Test path where server not specified
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = mock.Mock()
        obj = mock.Mock()
        obj.physical_id = None
        self.assertIsNone(profile.do_leave(obj))

    def test_do_leave_not_in_cluster(self):
        # Test path where node is not in cluster
        nc = mock.Mock()
        profile = server.ServerProfile('os.nova.server', 's1', spec=self.spec)
        profile._novaclient = nc
        nc.server_metadata_get.return_value = {'FOO': 'BAR'}
        nc.server_metadata_update.return_value = 'Boom'

        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        res = profile.do_leave(obj)
        self.assertEqual('Boom', res)
        nc.server_metadata_get.assert_called_once_with(server_id='FAKE_ID')
        nc.server_metadata_update.assert_called_once_with(FOO='BAR')
