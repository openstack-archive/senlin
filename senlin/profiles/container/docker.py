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

from oslo_log import log as logging
import six

from senlin.common.i18n import _
from senlin.common import schema
from senlin.drivers import base as driver_base
from senlin.drivers.container import docker as docker_driver
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class DockerProfile(base.Profile):
    """Profile for a docker container."""

    KEYS = (
        CONTEXT, IMAGE, NAME, COMMAND, HOST_NODE, HOST_CLUSTER
    ) = (
        'context', 'image', 'name', 'command', 'host_node', 'host_cluster',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('Customized security context for operationg containers.')
        ),
        IMAGE: schema.String(
            _('The image used to create a container')
        ),
        NAME: schema.String(
            _('The name of the container.')
        ),
        COMMAND: schema.String(
            _('The command to run when container is started.')
        ),
        HOST_NODE: schema.String(
            _('The node on which container will be launched.')
        ),
        HOST_CLUSTER: schema.String(
            _('The cluster on which container cluster will be launched.')
        ),
    }

    OPERATIONS = {}

    def __init__(self, type_name, name, **kwargs):
        super(DockerProfile, self).__init__(type_name, name, **kwargs)

        self._dockerclient = None
        self._novaclient = None
        self.container_id = None

    def docker(self, obj):
        """Construct docker client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """

        if self._dockerclient is not None:
            return self._dockerclient
        host = self.properties[self.HOST_NODE]
        host_ip = self.get_host_ip(self, obj, host)
        url = 'tcp://' + host_ip + ':2375'
        self._dockerclient = docker_driver.Dockerclient(url)
        return self._dockerclient

    def get_host_ip(self, obj, host):
        """Fetch the ip address of nova server."""

        server = self.nova(obj).server_get(host)
        return server.access_ipv4

    def nova(self, obj):
        """Construct nova client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """

        if self._novaclient is not None:
            return self._novaclient
        params = self._build_conn_params(obj.user, obj.project)
        self._novaclient = driver_base.SenlinDriver().compute(params)
        return self._novaclient

    def do_create(self, obj):
        """Create a container using the given profile."""

        kwargs = {}
        kwargs['image'] = self.properties[self.IMAGE]
        kwargs['command'] = self.properties[self.COMMAND]
        kwargs['name'] = self.properties[self.NAME]
        try:
            container = self.docker(obj).container_create(**kwargs)
        except Exception as ex:
            LOG.error("Container creation failed: %s" % six.text_type(ex))
            return
        self.container_id = container.id
        return container.id

    def do_delete(self, obj):
        """Delete a container node."""

        self.container_id = obj.physical_id
        if not obj.physical_id:
            return True
        try:
            self.docker(obj).container_delete(self.container_id)
        except Exception as ex:
            LOG.error("Container deletion failded: %s" % six.text_type(ex))
            return False

        return True
