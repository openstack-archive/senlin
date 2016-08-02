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

from senlin.drivers.container import docker_v1 as docker_driver
from senlin.tests.unit.common import base


class TestDocker(base.SenlinTestCase):

    def setUp(self):
        super(TestDocker, self).setUp()

        self._dockerclient = mock.Mock()

    @mock.patch('docker.Client')
    def test_init(self, mock_client):
        mock_client.return_value = self._dockerclient
        url = mock.Mock()
        dockerclient = docker_driver.DockerClient(url)._dockerclient
        self.assertEqual(self._dockerclient, dockerclient)

    @mock.patch('docker.Client')
    def test_container_create(self, mock_client):
        mock_client.return_value = self._dockerclient
        url = mock.Mock()
        dockerclient = docker_driver.DockerClient(url)
        image = mock.Mock()
        dockerclient.container_create(image)
        self._dockerclient.create_container.assert_called_once_with(
            name=None, image=image, command=None)

    @mock.patch('docker.Client')
    def test_container_delete(self, mock_client):
        mock_client.return_value = self._dockerclient
        url = mock.Mock()
        dockerclient = docker_driver.DockerClient(url)
        container = mock.Mock()
        res = dockerclient.container_delete(container)
        self.assertTrue(res)
        self._dockerclient.remove_container.assert_called_once_with(container)
