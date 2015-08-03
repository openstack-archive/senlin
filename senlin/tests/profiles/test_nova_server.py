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

from senlin.common import exception
from senlin.drivers.openstack import nova_v2 as novaclient
from senlin.profiles.os.nova import server
from senlin.tests.common import base
from senlin.tests.common import utils


class TestNovaServerProfile(base.SenlinTestCase):

    def setUp(self):
        super(TestNovaServerProfile, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'context': {},
            'adminPass': 'adminpass',
            'auto_disk_config': True,
            'availability_zone': 'FAKE_AZ',
            'block_device_mapping': [{'device_name': 'FAKE_NAME',
                                      'volume_size': 1000}],
            'config_drive': False,
            'flavor': 'FLAV',
            'image': 'FAKE_IMAGE',
            'key_name': 'FAKE_KEYNAME',
            "metadata": {"meta var": "meta val"},
            'name': 'FAKE_SERVER_NAME',
            'networks': [{'port': 'FAKE_PORT',
                          'fixed-ip': 'FAKE_IP'}],
            "personality": [{"path": "/etc/motd", "contents": "foo"}],
            'security_groups': ['HIGH_SECURITY_GROUP'],
            'timeout': 120,
            'user_data': 'FAKE_USER_DATA',
        }

    def test_nova_init(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        self.assertIsNone(profile._nc)
        self.assertIsNone(profile.server_id)

    def test_nova_client(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()
        profile.nova(test_server)
        self.assertIsNotNone(profile._nc)

        with mock.patch('senlin.drivers.openstack.nova_v2.NovaClient',
                        mock.MagicMock()):
            profile._get_connection_params = mock.MagicMock()
            profile._nc = None
            profile.nova(test_server)
            self.assertIsNotNone(profile._nc)
            self.assertTrue(novaclient.NovaClient.called)

    def test_do_validate(self):
        # Not implemented in server profile yet.
        pass

    def test_do_create(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()

        profile._nc.image_get_by_name = mock.MagicMock(side_effect=Exception())
        self.assertRaises(exception.ResourceNotFound,
                          profile.do_create, test_server)

        # Test normal path
        profile._nc.image_get_by_name = mock.MagicMock()
        test_server.name = "TEST_SERVER"
        flavor = mock.Mock()
        flavor.id = 'FAKE_FLAVOR_ID'
        nova_server = mock.Mock()
        nova_server.id = 'FAKE_NOVA_SERVER_ID'
        profile._nc.flavor_get = mock.MagicMock(side_effect=flavor)
        profile._nc.server_create = mock.MagicMock(return_value=nova_server)
        server_id = profile.do_create(test_server)
        self.assertTrue(profile._nc.image_get_by_name.called)
        self.assertTrue(profile._nc.flavor_get.called)
        self.assertTrue(profile._nc.server_create.called)
        self.assertEqual(nova_server.id, server_id)

    def test_do_delete(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()

        # Test path where server doesn't already exist
        test_server.physical_id = None
        self.assertTrue(profile.do_delete(test_server))
        self.assertIsNone(test_server.physical_id)

        # Test specific exception path
        ex = exception.ProfileOperationTimeout(message="timeout")
        profile._nc.server_delete = mock.MagicMock(side_effect=ex)
        test_server.physical_id = "FAKE_ID"
        self.assertRaises(exception.ProfileOperationTimeout,
                          profile.do_delete,
                          test_server)
        self.assertTrue(profile._nc.server_delete.called)

        # Test path for an existing server
        profile._nc.server_delete = mock.MagicMock()
        self.assertTrue(profile.do_delete(test_server))
        self.assertTrue(profile._nc.server_delete.called)

    def test_do_update(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()
        new_profile = mock.Mock()

        # Test path where server doesn't already exist
        self.assertTrue(profile.do_update(test_server, new_profile))

        # Test path for an existing server
        test_server.physical_id = 'FAKE_ID'
        self.assertTrue(profile.do_update(test_server, new_profile))

    def test_do_check(self):
        # Not implemented in server profile yet.
        pass

    def test_do_get_details(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()

        # Test path where server not specified
        test_server.physical_id = ''
        self.assertEqual({}, profile.do_get_details(test_server))

        # Test path where server was not found
        profile._nc.server_get = mock.MagicMock()
        self.assertEqual({}, profile.do_get_details(test_server))

        # Test normal path
        test_server.physical_id = 'FAKE_ID'
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
        profile._nc.server_get = mock.MagicMock(side_effect=nova_server)
        profile.do_get_details(test_server)
        self.assertTrue(profile._nc.server_get.called)

    def test_do_join(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()
        cluster_id = "FAKE_CLUSTER_ID"

        # Test path where server not specified
        test_server.physical_id = None
        self.assertEqual({}, profile.do_join(test_server, cluster_id))

        # Test normal path
        test_server.physical_id = 'FAKE_ID'
        profile._nc.server_metadata_get = mock.MagicMock()
        profile._nc.server_metadata_update = mock.MagicMock()
        profile.do_join(test_server, cluster_id)
        self.assertTrue(profile._nc.server_metadata_get.called)
        self.assertTrue(profile._nc.server_metadata_update.called)

    def test_do_leave(self):
        kwargs = {
            'spec': self.spec
        }
        profile = server.ServerProfile('StackProfile',
                                       'test-profile',
                                       **kwargs)

        profile._nc = mock.Mock()
        test_server = mock.Mock()

        # Test path where server not specified
        test_server.physical_id = None
        self.assertIsNone(profile.do_leave(test_server))

        # Test normal path
        test_server.physical_id = 'FAKE_ID'
        profile._nc.server_metadata_get = mock.MagicMock()
        profile._nc.server_metadata_update = mock.MagicMock()
        profile.do_leave(test_server)
        self.assertTrue(profile._nc.server_metadata_get.called)
        self.assertTrue(profile._nc.server_metadata_update.called)
