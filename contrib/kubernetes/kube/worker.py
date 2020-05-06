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

import jinja2
from oslo_log import log as logging
from oslo_utils import encodeutils

from kube import base
from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.objects import cluster as cluster_obj

LOG = logging.getLogger(__name__)


class ServerProfile(base.KubeBaseProfile):
    """Profile for an kubernetes node server."""

    VERSIONS = {
        '1.0': [
            {'status': consts.EXPERIMENTAL, 'since': '2017.10'}
        ]
    }

    KEYS = (
        CONTEXT, FLAVOR, IMAGE, KEY_NAME, BLOCK_DEVICE_MAPPING_V2
    ) = (
        'context', 'flavor', 'image', 'key_name', 'block_device_mapping_v2',
    )

    KUBE_KEYS = (
        MASTER_CLUSTER,
    ) = (
        'master_cluster',
    )

    MASTER_CLUSTER_KEYS = (
        KUBEADM_TOKEN, KUBE_MASTER_IP,
        PRIVATE_NETWORK, PRIVATE_SUBNET, PRIVATE_ROUTER,
    ) = (
        'kubeadm_token', 'kube_master_ip',
        'private_network', 'private_subnet', 'private_router',
    )

    INTERNAL_KEYS = (
        SECURITY_GROUP, SCALE_OUT_RECV_ID, SCALE_OUT_URL,
    ) = (
        'security_group', 'scale_out_recv_id', 'scale_out_url',
    )

    NETWORK_KEYS = (
        PORT, FIXED_IP, NETWORK, PORT_SECURITY_GROUPS,
        FLOATING_NETWORK, FLOATING_IP,
    ) = (
        'port', 'fixed_ip', 'network', 'security_groups',
        'floating_network', 'floating_ip',
    )

    BDM2_KEYS = (
        BDM2_UUID, BDM2_SOURCE_TYPE, BDM2_DESTINATION_TYPE,
        BDM2_DISK_BUS, BDM2_DEVICE_NAME, BDM2_VOLUME_SIZE,
        BDM2_GUEST_FORMAT, BDM2_BOOT_INDEX, BDM2_DEVICE_TYPE,
        BDM2_DELETE_ON_TERMINATION,
    ) = (
        'uuid', 'source_type', 'destination_type', 'disk_bus',
        'device_name', 'volume_size', 'guest_format', 'boot_index',
        'device_type', 'delete_on_termination',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('Customized security context for operating servers.'),
        ),
        FLAVOR: schema.String(
            _('ID of flavor used for the server.'),
            required=True,
            updatable=True,
        ),
        IMAGE: schema.String(
            # IMAGE is not required, because there could be BDM or BDMv2
            # support and the corresponding settings effective
            _('ID of image to be used for the new server.'),
            updatable=True,
        ),
        KEY_NAME: schema.String(
            _('Name of Nova keypair to be injected to server.'),
        ),
        MASTER_CLUSTER: schema.String(
            _('Cluster running kubernetes master.'),
            required=True,
        ),
        BLOCK_DEVICE_MAPPING_V2: schema.List(
            _('A list specifying the properties of block devices to be used '
              'for this server.'),
            schema=schema.Map(
                _('A map specifying the properties of a block device to be '
                  'used by the server.'),
                schema={
                    BDM2_UUID: schema.String(
                        _('ID of the source image, snapshot or volume'),
                    ),
                    BDM2_SOURCE_TYPE: schema.String(
                        _("Volume source type, must be one of 'image', "
                          "'snapshot', 'volume' or 'blank'"),
                        required=True,
                    ),
                    BDM2_DESTINATION_TYPE: schema.String(
                        _("Volume destination type, must be 'volume' or "
                          "'local'"),
                        required=True,
                    ),
                    BDM2_DISK_BUS: schema.String(
                        _('Bus of the device.'),
                    ),
                    BDM2_DEVICE_NAME: schema.String(
                        _('Name of the device(e.g. vda, xda, ....).'),
                    ),
                    BDM2_VOLUME_SIZE: schema.Integer(
                        _('Size of the block device in MB(for swap) and '
                          'in GB(for other formats)'),
                        required=True,
                    ),
                    BDM2_GUEST_FORMAT: schema.String(
                        _('Specifies the disk file system format(e.g. swap, '
                          'ephemeral, ...).'),
                    ),
                    BDM2_BOOT_INDEX: schema.Integer(
                        _('Define the boot order of the device'),
                    ),
                    BDM2_DEVICE_TYPE: schema.String(
                        _('Type of the device(e.g. disk, cdrom, ...).'),
                    ),
                    BDM2_DELETE_ON_TERMINATION: schema.Boolean(
                        _('Whether to delete the volume when the server '
                          'stops.'),
                    ),
                }
            ),
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(ServerProfile, self).__init__(type_name, name, **kwargs)
        self.server_id = None

    def _get_master_cluster_info(self, obj):
        ctx = context.get_service_context(user_id=obj.user,
                                          project_id=obj.project)
        master = self.properties[self.MASTER_CLUSTER]
        try:
            cluster = cluster_obj.Cluster.find(ctx, master)
        except Exception as ex:
            raise exc.EResourceCreation(type='kubernetes.worker',
                                        message=str(ex))
        for key in self.MASTER_CLUSTER_KEYS:
            if key not in cluster.data:
                raise exc.EResourceCreation(
                    type='kubernetes.worker',
                    message="Can't find %s in cluster %s" % (key, master))

        return cluster.data

    def _set_cluster_dependents(self, obj):
        ctx = context.get_service_context(user_id=obj.user,
                                          project_id=obj.project)
        master = self.properties[self.MASTER_CLUSTER]
        try:
            master_cluster = cluster_obj.Cluster.find(ctx, master)
        except exc.ResourceNotFound:
            msg = _("Cannot find the given cluster: %s") % master
            raise exc.BadRequest(msg=msg)
        if master_cluster:
            # configure kube master dependents, kube master record kube node
            # cluster uuid
            master_dependents = master_cluster.dependents
            master_dependents['kube-node'] = obj.id
            cluster_obj.Cluster.update(ctx, master_cluster.id,
                                       {'dependents': master_dependents})

    def _del_cluster_dependents(self, obj):
        ctx = context.get_service_context(user_id=obj.user,
                                          project_id=obj.project)
        master = self.properties[self.MASTER_CLUSTER]
        try:
            master_cluster = cluster_obj.Cluster.find(ctx, master)
        except exc.ResourceNotFound:
            msg = _("Cannot find the given cluster: %s") % master
            raise exc.BadRequest(msg=msg)

        if master_cluster:
            # remove kube master record kube node dependents
            master_dependents = master_cluster.dependents
            if master_dependents and 'kube-node' in master_dependents:
                master_dependents.pop('kube-node')
                cluster_obj.Cluster.update(ctx, master_cluster.id,
                                           {'dependents': master_dependents})

    def _get_cluster_data(self, obj):
        ctx = context.get_service_context(user_id=obj.user,
                                          project_id=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            return cluster.data

        return {}

    def do_cluster_create(self, obj):
        self._create_security_group(obj)
        self._set_cluster_dependents(obj)

    def do_cluster_delete(self, obj):
        self._delete_security_group(obj)
        self._del_cluster_dependents(obj)

    def do_validate(self, obj):
        """Validate if the spec has provided valid info for server creation.

        :param obj: The node object.
        """
        # validate flavor
        flavor = self.properties[self.FLAVOR]
        self._validate_flavor(obj, flavor)

        # validate image
        image = self.properties[self.IMAGE]
        if image is not None:
            self._validate_image(obj, image)

        # validate key_name
        keypair = self.properties[self.KEY_NAME]
        if keypair is not None:
            self._validate_keypair(obj, keypair)

        return True

    def do_create(self, obj):
        """Create a server for the node object.

        :param obj: The node object for which a server will be created.
        """
        kwargs = {}
        for key in self.KEYS:
            if self.properties[key] is not None:
                kwargs[key] = self.properties[key]

        image_ident = self.properties[self.IMAGE]
        if image_ident is not None:
            image = self._validate_image(obj, image_ident, 'create')
            kwargs.pop(self.IMAGE)
            kwargs['imageRef'] = image.id

        flavor_ident = self.properties[self.FLAVOR]
        flavor = self._validate_flavor(obj, flavor_ident, 'create')
        kwargs.pop(self.FLAVOR)
        kwargs['flavorRef'] = flavor.id

        keypair_name = self.properties[self.KEY_NAME]
        if keypair_name:
            keypair = self._validate_keypair(obj, keypair_name, 'create')
            kwargs['key_name'] = keypair.name

        kwargs['name'] = obj.name

        metadata = self._build_metadata(obj, {})
        kwargs['metadata'] = metadata

        sgid = self._get_security_group(obj)
        kwargs['security_groups'] = [{'name': sgid}]

        jj_vars = {}
        master_cluster = self._get_master_cluster_info(obj)
        kwargs['networks'] = [{'uuid': master_cluster[self.PRIVATE_NETWORK]}]
        jj_vars['KUBETOKEN'] = master_cluster[self.KUBEADM_TOKEN]
        jj_vars['MASTERIP'] = master_cluster[self.KUBE_MASTER_IP]

        block_device_mapping_v2 = self.properties[self.BLOCK_DEVICE_MAPPING_V2]
        if block_device_mapping_v2 is not None:
            kwargs['block_device_mapping_v2'] = self._resolve_bdm(
                obj, block_device_mapping_v2, 'create')

        user_data = base.loadScript('./scripts/worker.sh')
        if user_data is not None:
            # Use jinja2 to replace variables defined in user_data
            try:
                jj_t = jinja2.Template(user_data)
                user_data = jj_t.render(**jj_vars)
            except (jinja2.exceptions.UndefinedError, ValueError) as ex:
                # TODO(anyone) Handle jinja2 error
                pass
            ud = encodeutils.safe_encode(user_data)
            kwargs['user_data'] = encodeutils.safe_decode(base64.b64encode(ud))

        server = None
        resource_id = None
        try:
            server = self.compute(obj).server_create(**kwargs)
            self.compute(obj).wait_for_server(server.id)
            server = self.compute(obj).server_get(server.id)
            return server.id
        except exc.InternalError as ex:
            if server and server.id:
                resource_id = server.id
            raise exc.EResourceCreation(type='server',
                                        message=str(ex),
                                        resource_id=resource_id)

    def do_delete(self, obj, **params):
        """Delete the physical resource associated with the specified node.

        :param obj: The node object to operate on.
        :param kwargs params: Optional keyword arguments for the delete
                              operation.
        :returns: This operation always return True unless exception is
                  caught.
        :raises: `EResourceDeletion` if interaction with compute service fails.
        """
        if not obj.physical_id:
            return True

        server_id = obj.physical_id
        ignore_missing = params.get('ignore_missing', True)
        internal_ports = obj.data.get('internal_ports', [])
        force = params.get('force', False)

        try:
            driver = self.compute(obj)
            if force:
                driver.server_force_delete(server_id, ignore_missing)
            else:
                driver.server_delete(server_id, ignore_missing)
            driver.wait_for_server_delete(server_id)
            if internal_ports:
                ex = self._delete_ports(obj, internal_ports)
                if ex:
                    raise ex
            return True
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='server', id=server_id,
                                        message=str(ex))
