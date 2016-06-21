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

import docker


class DockerClient(object):
    """Docker driver."""

    def __init__(self, url):
        self.url = url
        self._dockerclient = docker.Client(base_url=self.url)

    def container_create(self, image, name=None, command=None):
        return self._dockerclient.create_container(name=name, image=image,
                                                   command=command)

    def container_delete(self, container):
        self._dockerclient.remove_container(container)
        return True
