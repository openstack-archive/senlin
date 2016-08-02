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

from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.engine import node
from senlin.profiles.container import docker as docker_profile
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestContainerDockerProfile(base.SenlinTestCase):

    def setUp(self):
        super(TestContainerDockerProfile, self).setUp()

        self.context = utils.dummy_context()
        self.spec = {
            'type': 'container.dockerinc.docker',
            'version': '1.0',
            'properties': {
                'context': {
                    'region_name': 'RegionOne'
                },
                'name': 'docker_container',
                'image': 'hello-world',
                'command': '/bin/sleep 30',
                'host_node': 'fake_host',
                'port': 2375,
            }
        }

    def test_init(self):
        profile = docker_profile.DockerProfile('t', self.spec)
        self.assertIsNone(profile._dockerclient)
        self.assertIsNone(profile._novaclient)
        self.assertIsNone(profile._heatclient)
        self.assertIsNone(profile.container_id)

    @mock.patch('senlin.drivers.container.docker_v1.DockerClient')
    @mock.patch.object(docker_profile.DockerProfile, '_get_host_ip')
    @mock.patch.object(context, 'get_admin_context')
    @mock.patch.object(node.Node, 'load')
    def test_docker_client(self, mock_load, mock_ctx, mock_get, mock_client):
        profile = mock.Mock(type_name='os.nova.server')
        host = mock.Mock(rt={'profile': profile}, physical_id='server1')
        mock_load.return_value = host
        fake_ip = '1.2.3.4'
        mock_get.return_value = fake_ip
        ctx = mock.Mock()
        mock_ctx.return_value = ctx
        dockerclient = mock.Mock()
        mock_client.return_value = dockerclient
        profile = docker_profile.DockerProfile('container', self.spec)
        obj = mock.Mock()
        client = profile.docker(obj)
        self.assertEqual(dockerclient, client)
        mock_load.assert_called_once_with(ctx, node_id='fake_host')
        mock_get.assert_called_once_with(obj, 'server1', 'os.nova.server')
        url = 'tcp://1.2.3.4:2375'
        mock_client.assert_called_once_with(url)

    def test_docker_client_host_node_is_empty(self):
        spec = self.spec
        spec['properties']['host_node'] = ''
        profile = docker_profile.DockerProfile('container', spec)
        obj = mock.Mock()
        ex = self.assertRaises(exc.EResourceCreation,
                               profile.docker, obj)
        msg = _('Failed in creating container: No host specified to '
                'start containers on.')
        self.assertEqual(msg, ex.message)

    @mock.patch.object(node.Node, 'load')
    def test_docker_client_host_node_not_found(self, mock_load):
        mock_load.side_effect = exc.NodeNotFound(node='fake_host')
        profile = docker_profile.DockerProfile('container', self.spec)
        obj = mock.Mock()
        ex = self.assertRaises(exc.EResourceCreation,
                               profile.docker, obj)
        msg = _('Failed in creating container: The host_node (fake_host) '
                'could not be found.')
        self.assertEqual(msg, ex.message)

    @mock.patch.object(node.Node, 'load')
    def test_docker_client_wrong_host_type(self, mock_load):
        profile = mock.Mock(type_name='wrong_type')
        host = mock.Mock(rt={'profile': profile}, physical_id='server1')
        mock_load.return_value = host
        obj = mock.Mock()
        profile = docker_profile.DockerProfile('container', self.spec)
        ex = self.assertRaises(exc.EResourceCreation,
                               profile.docker, obj)
        msg = _('Failed in creating container: Type of host node '
                '(wrong_type) is not supported.')
        self.assertEqual(msg, ex.message)

    @mock.patch.object(docker_profile.DockerProfile, '_get_host_ip')
    @mock.patch.object(node.Node, 'load')
    def test_docker_client_get_host_ip_failed(self, mock_load, mock_get):
        profile = mock.Mock(type_name='os.nova.server')
        host = mock.Mock(rt={'profile': profile}, physical_id='server1')
        mock_load.return_value = host
        mock_get.return_value = None
        obj = mock.Mock()
        profile = docker_profile.DockerProfile('container', self.spec)
        ex = self.assertRaises(exc.EResourceCreation,
                               profile.docker, obj)
        msg = _('Failed in creating container: Unable to determine the IP '
                'address of host node.')
        self.assertEqual(msg, ex.message)

    @mock.patch.object(docker_profile.DockerProfile, 'nova')
    def test_get_host_ip_nova_server(self, mock_nova):
        addresses = {
            'private': [{'version': 4, 'OS-EXT-IPS:type': 'fixed',
                         'addr': '1.2.3.4'}]
        }
        server = mock.Mock(addresses=addresses)
        novaclient = mock.Mock()
        mock_nova.return_value = novaclient
        novaclient.server_get.return_value = server
        profile = docker_profile.DockerProfile('container', self.spec)
        obj = mock.Mock()
        host_ip = profile._get_host_ip(obj, 'fake_node', 'os.nova.server')
        self.assertEqual('1.2.3.4', host_ip)
        novaclient.server_get.assert_called_once_with('fake_node')

    @mock.patch.object(docker_profile.DockerProfile, 'heat')
    def test_get_host_ip_heat_stack(self, mock_heat):
        heatclient = mock.Mock()
        mock_heat.return_value = heatclient
        stack = mock.Mock()
        heatclient.stack_get.return_value = stack
        outputs = [{'output_key': 'fixed_ip', 'output_value': '1.2.3.4'}]
        stack.outputs = outputs
        profile = docker_profile.DockerProfile('container', self.spec)
        obj = mock.Mock()
        host_ip = profile._get_host_ip(obj, 'fake_node', 'os.heat.stack')
        self.assertEqual('1.2.3.4', host_ip)
        heatclient.stack_get.assert_called_once_with('fake_node')
        # No outputs in stack
        stack.outputs = None
        ex = self.assertRaises(exc.EResourceCreation,
                               profile._get_host_ip,
                               obj, 'fake_node', 'os.heat.stack')
        msg = _("Failed in creating container: Output 'fixed_ip' is "
                "missing from the provided stack node.")
        self.assertEqual(msg, ex.message)

    @mock.patch.object(docker_profile.DockerProfile, 'docker')
    def test_do_create(self, mock_docker):
        dockerclient = mock.Mock()
        mock_docker.return_value = dockerclient
        container = mock.Mock()
        dockerclient.container_create.return_value = container
        container_id = mock.Mock()
        container.id = container_id
        profile = docker_profile.DockerProfile('container', self.spec)
        obj = mock.Mock()
        self.assertEqual(container_id, profile.do_create(obj))
        params = {
            'image': 'hello-world',
            'name': 'docker_container',
            'command': '/bin/sleep 30',
        }
        dockerclient.container_create.assert_called_once_with(**params)

    @mock.patch.object(docker_profile.DockerProfile, 'docker')
    def test_do_create_failed(self, mock_docker):
        mock_docker.side_effect = Exception
        profile = docker_profile.DockerProfile('container', self.spec)
        obj = mock.Mock()
        self.assertRaises(exc.EResourceCreation,
                          profile.do_create, obj)

    @mock.patch.object(docker_profile.DockerProfile, 'docker')
    def test_do_delete(self, mock_docker):
        obj = mock.Mock()
        physical_id = mock.Mock()
        obj.physical_id = physical_id
        dockerclient = mock.Mock()
        mock_docker.return_value = dockerclient
        profile = docker_profile.DockerProfile('container', self.spec)
        self.assertIsNone(profile.do_delete(obj))
        dockerclient.container_delete.assert_called_once_with(physical_id)

    def test_do_delete_no_physical_id(self):
        obj = mock.Mock()
        obj.physical_id = None
        profile = docker_profile.DockerProfile('container', self.spec)
        self.assertIsNone(profile.do_delete(obj))

    @mock.patch.object(docker_profile.DockerProfile, 'docker')
    def test_do_delete_failed(self, mock_docker):
        obj = mock.Mock()
        physical_id = mock.Mock()
        obj.physical_id = physical_id
        mock_docker.side_effect = Exception
        profile = docker_profile.DockerProfile('container', self.spec)
        self.assertRaises(exc.EResourceDeletion,
                          profile.do_delete, obj)
