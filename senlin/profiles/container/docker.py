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

import random
import six

from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.common import utils
from senlin.db.sqlalchemy import api as db_api
from senlin.drivers.container import docker_v1 as docker_driver
from senlin.engine import cluster
from senlin.engine import node as node_mod
from senlin.objects import cluster as co
from senlin.objects import node as no
from senlin.profiles import base


class DockerProfile(base.Profile):
    """Profile for a docker container."""
    VERSIONS = {
        '1.0': [
            {'status': consts.EXPERIMENTAL, 'since': '2017.02'}
        ]
    }

    _VALID_HOST_TYPES = [
        HOST_NOVA_SERVER, HOST_HEAT_STACK,
    ] = [
        "os.nova.server", "os.heat.stack",
    ]

    KEYS = (
        CONTEXT, IMAGE, NAME, COMMAND, HOST_NODE, HOST_CLUSTER, PORT,
    ) = (
        'context', 'image', 'name', 'command', 'host_node', 'host_cluster',
        'port',
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
        HOST_CLUSTER: schema.String(
            _('The cluster on which container will be launched.')
        ),
    }

    OP_NAMES = (
        OP_RESTART, OP_PAUSE, OP_UNPAUSE,
    ) = (
        'restart', 'pause', 'unpause',
    )

    _RESTART_WAIT = (RESTART_WAIT) = ('wait_time')

    OPERATIONS = {
        OP_RESTART: schema.Operation(
            _("Restart a container."),
            schema={
                RESTART_WAIT: schema.IntegerParam(
                    _("Number of seconds to wait before killing the "
                      "container.")
                )
            }
        ),
        OP_PAUSE: schema.Operation(
            _("Pause a container.")
        ),
        OP_UNPAUSE: schema.Operation(
            _("Unpause a container.")
        )
    }

    def __init__(self, type_name, name, **kwargs):
        super(DockerProfile, self).__init__(type_name, name, **kwargs)

        self._dockerclient = None
        self.container_id = None
        self.host = None
        self.cluster = None

    @classmethod
    def create(cls, ctx, name, spec, metadata=None):
        profile = super(DockerProfile, cls).create(ctx, name, spec, metadata)

        host_cluster = profile.properties.get(profile.HOST_CLUSTER, None)
        if host_cluster:
            db_api.cluster_add_dependents(ctx, host_cluster, profile.id)

        host_node = profile.properties.get(profile.HOST_NODE, None)
        if host_node:
            db_api.node_add_dependents(ctx, host_node, profile.id, 'profile')

        return profile

    @classmethod
    def delete(cls, ctx, profile_id):
        obj = cls.load(ctx, profile_id=profile_id)
        cluster_id = obj.properties.get(obj.HOST_CLUSTER, None)
        if cluster_id:
            db_api.cluster_remove_dependents(ctx, cluster_id, profile_id)

        node_id = obj.properties.get(obj.HOST_NODE, None)
        if node_id:
            db_api.node_remove_dependents(ctx, node_id, profile_id, 'profile')

        super(DockerProfile, cls).delete(ctx, profile_id)

    def docker(self, obj):
        """Construct docker client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._dockerclient is not None:
            return self._dockerclient

        host_node = self.properties.get(self.HOST_NODE, None)
        host_cluster = self.properties.get(self.HOST_CLUSTER, None)
        ctx = context.get_admin_context()
        self.host = self._get_host(ctx, host_node, host_cluster)

        # TODO(Anyone): Check node.data for per-node host selection
        host_type = self.host.rt['profile'].type_name
        if host_type not in self._VALID_HOST_TYPES:
            msg = _("Type of host node (%s) is not supported") % host_type
            raise exc.InternalError(message=msg)

        host_ip = self._get_host_ip(obj, self.host.physical_id, host_type)
        if host_ip is None:
            msg = _("Unable to determine the IP address of host node")
            raise exc.InternalError(message=msg)

        url = 'tcp://%(ip)s:%(port)d' % {'ip': host_ip,
                                         'port': self.properties[self.PORT]}
        self._dockerclient = docker_driver.DockerClient(url)
        return self._dockerclient

    def _get_host(self, ctx, host_node, host_cluster):
        """Determine which node to launch container on.

        :param ctx: An instance of the request context.
        :param host_node: The uuid of the hosting node.
        :param host_cluster: The uuid of the hosting cluster.
        """
        host = None
        if host_node is not None:
            try:
                host = node_mod.Node.load(ctx, node_id=host_node)
            except exc.ResourceNotFound as ex:
                msg = ex.enhance_msg('host', ex)
                raise exc.InternalError(message=msg)
            return host

        if host_cluster is not None:
            host = self._get_random_node(ctx, host_cluster)

        return host

    def _get_random_node(self, ctx, host_cluster):
        """Get a node randomly from the host cluster.

        :param ctx: An instance of the request context.
        :param host_cluster: The uuid of the hosting cluster.
        """
        self.cluster = None
        try:
            self.cluster = cluster.Cluster.load(ctx, cluster_id=host_cluster)
        except exc.ResourceNotFound as ex:
            msg = ex.enhance_msg('host', ex)
            raise exc.InternalError(message=msg)

        filters = {consts.NODE_STATUS: consts.NS_ACTIVE}
        nodes = no.Node.get_all_by_cluster(ctx, cluster_id=host_cluster,
                                           filters=filters)
        if len(nodes) == 0:
            msg = _("The cluster (%s) contains no active nodes") % host_cluster
            raise exc.InternalError(message=msg)

        # TODO(anyone): Should pick a node by its load
        db_node = nodes[random.randrange(len(nodes))]
        return node_mod.Node.load(ctx, db_node=db_node)

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
            server = self.compute(obj).server_get(host_node)
            private_addrs = server.addresses['private']
            for addr in private_addrs:
                if addr['version'] == 4 and addr['OS-EXT-IPS:type'] == 'fixed':
                    host_ip = addr['addr']
        elif host_type == self.HOST_HEAT_STACK:
            stack = self.orchestration(obj).stack_get(host_node)
            outputs = stack.outputs or {}
            if outputs:
                for output in outputs:
                    if output['output_key'] == 'fixed_ip':
                        host_ip = output['output_value']
                        break

            if not outputs or host_ip is None:
                msg = _("Output 'fixed_ip' is missing from the provided stack"
                        " node")
                raise exc.InternalError(message=msg)

        return host_ip

    def do_validate(self, obj):
        """Validate if the spec has provided valid configuration.

        :param obj: The node object.
        """
        cluster = self.properties[self.HOST_CLUSTER]
        node = self.properties[self.HOST_NODE]
        if all([cluster, node]):
            msg = _("Either '%(c)s' or '%(n)s' must be specified, but not "
                    "both.") % {'c': self.HOST_CLUSTER, 'n': self.HOST_NODE}
            raise exc.InvalidSpec(message=msg)

        if not any([cluster, node]):
            msg = _("Either '%(c)s' or '%(n)s' must be specified."
                    ) % {'c': self.HOST_CLUSTER, 'n': self.HOST_NODE}
            raise exc.InvalidSpec(message=msg)

        if cluster:
            try:
                co.Cluster.find(self.context, cluster)
            except (exc.ResourceNotFound, exc.MultipleChoices):
                msg = _("The specified %(key)s '%(val)s' could not be found "
                        "or is not unique."
                        ) % {'key': self.HOST_CLUSTER, 'val': cluster}
                raise exc.InvalidSpec(message=msg)

        if node:
            try:
                no.Node.find(self.context, node)
            except (exc.ResourceNotFound, exc.MultipleChoices):
                msg = _("The specified %(key)s '%(val)s' could not be found "
                        "or is not unique."
                        ) % {'key': self.HOST_NODE, 'val': node}
                raise exc.InvalidSpec(message=msg)

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

        try:
            ctx = context.get_service_context(project=obj.project,
                                              user=obj.user)
            dockerclient = self.docker(obj)
            db_api.node_add_dependents(ctx, self.host.id, obj.id)
            container = dockerclient.container_create(**params)
        except exc.InternalError as ex:
            raise exc.EResourceCreation(type='container',
                                        message=six.text_type(ex))

        self.container_id = container['Id'][:36]
        return self.container_id

    def do_delete(self, obj):
        """Delete a container node.

        :param obj: The node object representing the container.
        :returns: `None`
        """
        if not obj.physical_id:
            return

        try:
            self.docker(obj).container_delete(obj.physical_id)
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='container',
                                        id=obj.physical_id,
                                        message=six.text_type(ex))
        ctx = context.get_admin_context()
        db_api.node_remove_dependents(ctx, self.host.id, obj.id)
        return

    def handle_reboot(self, obj, **options):
        """Handler for a reboot operation.

        :param obj: The node object representing the container.
        :returns: None
        """
        if not obj.physical_id:
            return

        if 'timeout' in options:
            params = {'timeout': options['timeout']}
        else:
            params = {}
        try:
            self.docker(obj).reboot(obj.physical_id, **params)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(type='container',
                                         id=obj.physical_id[:8],
                                         op='rebooting',
                                         message=six.text_type(ex))
        return

    def handle_pause(self, obj):
        """Handler for a pause operation.

        :param obj: The node object representing the container.
        :returns: None
        """
        if not obj.physical_id:
            return

        try:
            self.docker(obj).pause(obj.physical_id)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(type='container',
                                         id=obj.physical_id[:8],
                                         op='pausing',
                                         message=six.text_type(ex))
        return

    def handle_unpause(self, obj):
        """Handler for an unpause operation.

        :param obj: The node object representing the container.
        :returns: None
        """
        if not obj.physical_id:
            return

        try:
            self.docker(obj).unpause(obj.physical_id)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(type='container',
                                         id=obj.physical_id[:8],
                                         op='unpausing',
                                         message=six.text_type(ex))
        return
