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

from senlin.drivers import sdk


class DockerClient(object):
    """Docker driver."""

    def __init__(self, url):
        self._dockerclient = docker.APIClient(base_url=url, version='auto')

    @sdk.translate_exception
    def container_create(self, image, name=None, command=None):
        return self._dockerclient.create_container(name=name, image=image,
                                                   command=command)

    @sdk.translate_exception
    def container_delete(self, container):
        self._dockerclient.remove_container(container)
        return True

    @sdk.translate_exception
    def restart(self, container, timeout=None):
        params = {'timeout': timeout} if timeout else {}
        self._dockerclient.restart(container, **params)

    @sdk.translate_exception
    def pause(self, container):
        self._dockerclient.pause(container)

    @sdk.translate_exception
    def unpause(self, container):
        self._dockerclient.unpause(container)
