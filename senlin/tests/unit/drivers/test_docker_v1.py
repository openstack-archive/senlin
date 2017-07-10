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

from senlin.drivers.container import docker_v1
from senlin.tests.unit.common import base


class TestDocker(base.SenlinTestCase):

    @mock.patch("docker.APIClient")
    def setUp(self, mock_docker):
        super(TestDocker, self).setUp()
        self.x_docker = mock.Mock()
        mock_docker.return_value = self.x_docker
        self.sot = docker_v1.DockerClient("abc")

    @mock.patch("docker.APIClient")
    def test_init(self, mock_docker):
        x_docker = mock_docker.return_value
        url = mock.Mock()

        sot = docker_v1.DockerClient(url)

        self.assertEqual(x_docker, sot._dockerclient)
        mock_docker.assert_called_once_with(base_url=url, version='auto')

    def test_container_create(self):
        image = mock.Mock()

        self.sot.container_create(image)

        self.x_docker.create_container.assert_called_once_with(
            name=None, image=image, command=None)

    def test_container_delete(self):
        container = mock.Mock()

        res = self.sot.container_delete(container)

        self.assertTrue(res)
        self.x_docker.remove_container.assert_called_once_with(container)

    def test_restart(self):
        container = mock.Mock()

        res = self.sot.restart(container)

        self.assertIsNone(res)
        self.x_docker.restart.assert_called_once_with(container)

    def test_restart_with_wait(self):
        container = mock.Mock()

        res = self.sot.restart(container, timeout=20)

        self.assertIsNone(res)
        self.x_docker.restart.assert_called_once_with(container, timeout=20)

    def test_pause(self):
        container = mock.Mock()

        res = self.sot.pause(container)

        self.assertIsNone(res)
        self.x_docker.pause.assert_called_once_with(container)

    def test_unpause(self):
        container = mock.Mock()

        res = self.sot.unpause(container)

        self.assertIsNone(res)
        self.x_docker.unpause.assert_called_once_with(container)
