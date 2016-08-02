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

from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.common import utils
from senlin.drivers import base as driver_base
from senlin.drivers.container import docker_v1 as docker_driver
from senlin.engine import node
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class DockerProfile(base.Profile):
    """Profile for a docker container."""

    _VALID_HOST_TYPES = [
        HOST_NOVA_SERVER, HOST_HEAT_STACK,
    ] = [
        "os.nova.server", "os.heat.stack",
    ]

    KEYS = (
        CONTEXT, IMAGE, NAME, COMMAND, HOST_NODE, PORT,
    ) = (
        'context', 'image', 'name', 'command', 'host_node', 'port',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('Customized security context for operating containers.')
        ),
        IMAGE: schema.String(
            _('The image used to create a container'),
            required=True,
        ),
        NAME: schema.String(
            _('The name of the container.')
        ),
        COMMAND: schema.String(
            _('The command to run when container is started.')
        ),
        PORT: schema.Integer(
            _('The port number used to connect to docker daemon.'),
            default=2375
        ),
        HOST_NODE: schema.String(
            _('The node on which container will be launched.')
        ),
    }

    OPERATIONS = {}

    def __init__(self, type_name, name, **kwargs):
        super(DockerProfile, self).__init__(type_name, name, **kwargs)

        self._dockerclient = None
        self._novaclient = None
        self._heatclient = None
        self.container_id = None

    def docker(self, obj):
        """Construct docker client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._dockerclient is not None:
            return self._dockerclient

        host_node = self.properties[self.HOST_NODE]
        if not host_node:
            msg = _("No host specified to start containers on")
            raise exc.EResourceCreation(type='container', message=msg)

        # TODO(Anyone): Check node.data for per-node host selection

        ctx = context.get_admin_context()
        try:
            host = node.Node.load(ctx, node_id=host_node)
        except exc.NodeNotFound:
            msg = _("The host_node (%s) could not be found") % host_node
            raise exc.EResourceCreation(type='container', message=msg)

        host_type = host.rt['profile'].type_name
        if host_type not in self._VALID_HOST_TYPES:
            msg = _("Type of host node (%s) is not supported") % host_type
            raise exc.EResourceCreation(type='container', message=msg)

        host_ip = self._get_host_ip(obj, host.physical_id, host_type)
        if host_ip is None:
            msg = _("Unable to determine the IP address of host node")
            raise exc.EResourceCreation(type='container', message=msg)

        url = 'tcp://%(ip)s:%(port)d' % {'ip': host_ip,
                                         'port': self.properties[self.PORT]}
        self._dockerclient = docker_driver.DockerClient(url)
        return self._dockerclient

    def _get_host_ip(self, obj, host_node, host_type):
        """Fetch the ip address of physical node.

        :param obj: The node object representing the container instance.
        :param host_node: The name or ID of the hosting node object.
        :param host_type: The type of the hosting node, which can be either a
                          nova server or a heat stack.
        :returns: The fixed IP address of the hosting node.
        """
        host_ip = None
        if host_type == self.HOST_NOVA_SERVER:
            server = self.nova(obj).server_get(host_node)
            private_addrs = server.addresses['private']
            for addr in private_addrs:
                if addr['version'] == 4 and addr['OS-EXT-IPS:type'] == 'fixed':
                    host_ip = addr['addr']
        elif host_type == self.HOST_HEAT_STACK:
            stack = self.heat(obj).stack_get(host_node)
            outputs = stack.outputs or {}
            if outputs:
                for output in outputs:
                    if output['output_key'] == 'fixed_ip':
                        host_ip = output['output_value']
                        break

            if not outputs or host_ip is None:
                msg = _("Output 'fixed_ip' is missing from the provided stack"
                        " node")
                raise exc.EResourceCreation(type='container', message=msg)

        return host_ip

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

    def heat(self, obj):
        """Construct heat client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._heatclient is not None:
            return self._heatclient

        params = self._build_conn_params(obj.user, obj.project)
        self._heatclient = driver_base.SenlinDriver().orchestration(params)
        return self._heatclient

    def do_create(self, obj):
        """Create a container instance using the given profile.

        :param obj: The node object for this container.
        :returns: ID of the container instance or ``None`` if driver fails.
        :raises: `EResourceCreation`
        """
        name = self.properties[self.NAME]
        if name is None:
            name = '-'.join([obj.name, utils.random_name()])

        params = {
            'image': self.properties[self.IMAGE],
            'name': self.properties[self.NAME],
            'command': self.properties[self.COMMAND],
        }

        # TODO(Anyone): Wrap docker exceptions at the driver layer so they
        # are converted to exc.InternalError
        try:
            container = self.docker(obj).container_create(**params)
        except Exception as ex:
            raise exc.EResourceCreation(type='container',
                                        message=six.text_type(ex))

        self.container_id = container.id
        return container.id

    def do_delete(self, obj):
        """Delete a container node.

        :param obj: The node object representing the container.
        :returns: `None`
        """
        if not obj.physical_id:
            return

        # TODO(Anyone): Wrap docker exceptions at the driver layer so they
        # are converted to exc.InternalError
        try:
            self.docker(obj).container_delete(obj.physical_id)
        except Exception as ex:
            raise exc.EResourceDeletion(type='container',
                                        id=obj.physical_id,
                                        message=six.text_type(ex))
        return
