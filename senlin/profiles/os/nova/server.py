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
import copy

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils

from senlin.common import constraints
from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.objects import node as node_obj
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class ServerProfile(base.Profile):
    """Profile for an OpenStack Nova server."""

    VERSION = '1.2'
    VERSIONS = {
        '1.0': [
            {'status': consts.SUPPORTED, 'since': '2016.04'}
        ],
        '1.1': [
            {'status': consts.SUPPORTED, 'since': '2023.04'}
        ],
        '1.2': [
            {'status': consts.SUPPORTED, 'since': '2023.07'}
        ]
    }

    KEYS = (
        CONTEXT, ADMIN_PASS, AUTO_DISK_CONFIG, AVAILABILITY_ZONE,
        BLOCK_DEVICE_MAPPING_V2,
        CONFIG_DRIVE, FLAVOR, IMAGE, KEY_NAME, METADATA,
        NAME, NETWORKS, PERSONALITY, SECURITY_GROUPS,
        USER_DATA, SCHEDULER_HINTS,
    ) = (
        'context', 'admin_pass', 'auto_disk_config', 'availability_zone',
        'block_device_mapping_v2',
        'config_drive', 'flavor', 'image', 'key_name', 'metadata',
        'name', 'networks', 'personality', 'security_groups',
        'user_data', 'scheduler_hints',
    )

    BDM2_KEYS = (
        BDM2_UUID, BDM2_SOURCE_TYPE, BDM2_DESTINATION_TYPE,
        BDM2_DISK_BUS, BDM2_DEVICE_NAME, BDM2_VOLUME_SIZE,
        BDM2_GUEST_FORMAT, BDM2_BOOT_INDEX, BDM2_DEVICE_TYPE,
        BDM2_DELETE_ON_TERMINATION, BDM2_VOLUME_TYPE,
    ) = (
        'uuid', 'source_type', 'destination_type', 'disk_bus',
        'device_name', 'volume_size', 'guest_format', 'boot_index',
        'device_type', 'delete_on_termination', 'volume_type'
    )

    NETWORK_KEYS = (
        PORT, VNIC_TYPE, FIXED_IP, NETWORK, PORT_SECURITY_GROUPS,
        FLOATING_NETWORK, FLOATING_IP, SUBNET
    ) = (
        'port', 'vnic_type', 'fixed_ip', 'network', 'security_groups',
        'floating_network', 'floating_ip', 'subnet'
    )

    PERSONALITY_KEYS = (
        PATH, CONTENTS,
    ) = (
        'path', 'contents',
    )

    SCHEDULER_HINTS_KEYS = (
        GROUP,
    ) = (
        'group',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('Customized security context for operating servers.'),
        ),
        ADMIN_PASS: schema.String(
            _('Password for the administrator account.'),
        ),
        AUTO_DISK_CONFIG: schema.Boolean(
            _('Whether the disk partition is done automatically.'),
            default=True,
        ),
        AVAILABILITY_ZONE: schema.String(
            _('Name of availability zone for running the server.'),
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
                    BDM2_VOLUME_TYPE: schema.String(
                        _('Id or name of volume type.'),
                    ),
                }
            ),
        ),
        CONFIG_DRIVE: schema.Boolean(
            _('Whether config drive should be enabled for the server.'),
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
        METADATA: schema.Map(
            _('A collection of key/value pairs to be associated with the '
              'server created. Both key and value must be <=255 chars.'),
            updatable=True,
        ),
        NAME: schema.String(
            _('Name of the server. When omitted, the node name will be used.'),
            updatable=True,
        ),
        NETWORKS: schema.List(
            _('List of networks for the server.'),
            schema=schema.Map(
                _('A map specifying the properties of a network for uses.'),
                schema={
                    NETWORK: schema.String(
                        _('Name or ID of network to create a port on.'),
                    ),
                    PORT: schema.String(
                        _('Port ID to be used by the network.'),
                    ),
                    VNIC_TYPE: schema.String(
                        _('Define vnic_type to be used by port'),
                    ),
                    FIXED_IP: schema.String(
                        _('Fixed IP to be used by the network.'),
                    ),
                    PORT_SECURITY_GROUPS: schema.List(
                        _('A list of security groups to be attached to '
                          'this port.'),
                        schema=schema.String(
                            _('Name of a security group'),
                            required=True,
                        ),
                    ),
                    FLOATING_NETWORK: schema.String(
                        _('The network on which to create a floating IP'),
                    ),
                    FLOATING_IP: schema.String(
                        _('The floating IP address to be associated with '
                          'this port.'),
                    ),
                    SUBNET: schema.String(
                        _('Subnet in which to allocate the IP address for '
                          'this port.'),
                    ),
                },
            ),
            updatable=True,
        ),
        PERSONALITY: schema.List(
            _('List of files to be injected into the server, where each.'),
            schema=schema.Map(
                _('A map specifying the path & contents for an injected '
                  'file.'),
                schema={
                    PATH: schema.String(
                        _('In-instance path for the file to be injected.'),
                        required=True,
                    ),
                    CONTENTS: schema.String(
                        _('Contents of the file to be injected.'),
                        required=True,
                    ),
                },
            ),
        ),
        SCHEDULER_HINTS: schema.Map(
            _('A collection of key/value pairs to be associated with the '
              'Scheduler hints. Both key and value must be <=255 chars.'),
        ),

        SECURITY_GROUPS: schema.List(
            _('List of security groups.'),
            schema=schema.String(
                _('Name of a security group'),
                required=True,
            ),
        ),
        USER_DATA: schema.String(
            _('User data to be exposed by the metadata server.'),
        ),
    }

    OP_NAMES = (
        OP_REBOOT, OP_REBUILD, OP_CHANGE_PASSWORD, OP_PAUSE, OP_UNPAUSE,
        OP_SUSPEND, OP_RESUME, OP_LOCK, OP_UNLOCK, OP_START, OP_STOP,
        OP_RESCUE, OP_UNRESCUE, OP_EVACUATE, OP_MIGRATE,
    ) = (
        'reboot', 'rebuild', 'change_password', 'pause', 'unpause',
        'suspend', 'resume', 'lock', 'unlock', 'start', 'stop',
        'rescue', 'unrescue', 'evacuate', 'migrate',
    )

    ADMIN_PASSWORD = 'admin_pass'
    RESCUE_IMAGE = 'image_ref'
    EVACUATE_OPTIONS = (
        EVACUATE_HOST, EVACUATE_FORCE
    ) = (
        'host', 'force'
    )

    OPERATIONS = {
        OP_REBOOT: schema.Operation(
            _("Reboot the nova server."),
            schema={
                consts.REBOOT_TYPE: schema.StringParam(
                    _("Type of reboot which can be 'SOFT' or 'HARD'."),
                    default=consts.REBOOT_SOFT,
                    constraints=[
                        constraints.AllowedValues(consts.REBOOT_TYPES),
                    ]
                )
            }
        ),
        OP_REBUILD: schema.Operation(
            _("Rebuild the server using current image and admin password."),
        ),
        OP_CHANGE_PASSWORD: schema.Operation(
            _("Change the administrator password."),
            schema={
                ADMIN_PASSWORD: schema.StringParam(
                    _("New password for the administrator.")
                )
            }
        ),
        OP_PAUSE: schema.Operation(
            _("Pause the server from running."),
        ),
        OP_UNPAUSE: schema.Operation(
            _("Unpause the server to running state."),
        ),
        OP_SUSPEND: schema.Operation(
            _("Suspend the running of the server."),
        ),
        OP_RESUME: schema.Operation(
            _("Resume the running of the server."),
        ),
        OP_LOCK: schema.Operation(
            _("Lock the server."),
        ),
        OP_UNLOCK: schema.Operation(
            _("Unlock the server."),
        ),
        OP_START: schema.Operation(
            _("Start the server."),
        ),
        OP_STOP: schema.Operation(
            _("Stop the server."),
        ),
        OP_RESCUE: schema.Operation(
            _("Rescue the server."),
            schema={
                RESCUE_IMAGE: schema.StringParam(
                    _("A string referencing the image to use."),
                ),
            }
        ),
        OP_UNRESCUE: schema.Operation(
            _("Unrescue the server."),
        ),
        OP_EVACUATE: schema.Operation(
            _("Evacuate the server to a different host."),
            schema={
                EVACUATE_HOST: schema.StringParam(
                    _("The target host to evacuate the server."),
                ),
                EVACUATE_FORCE: schema.StringParam(
                    _("Whether the evacuation should be a forced one.")
                )
            }
        )
    }

    def __init__(self, type_name, name, **kwargs):
        super(ServerProfile, self).__init__(type_name, name, **kwargs)
        self.server_id = None
        self.stop_timeout = cfg.CONF.default_nova_timeout

    def _validate_az(self, obj, az_name, reason=None):
        try:
            res = self.compute(obj).validate_azs([az_name])
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=str(ex))
            else:
                raise

        if not res:
            msg = _("The specified %(key)s '%(value)s' could not be found"
                    ) % {'key': self.AVAILABILITY_ZONE, 'value': az_name}
            if reason == 'create':
                raise exc.EResourceCreation(type='server', message=msg)
            else:
                raise exc.InvalidSpec(message=msg)

        return az_name

    def _validate_flavor(self, obj, name_or_id, reason=None):
        flavor = None
        msg = ''
        try:
            flavor = self.compute(obj).flavor_find(name_or_id, False)
        except exc.InternalError as ex:
            msg = str(ex)
            if reason is None:  # reason is 'validate'
                if ex.code == 404:
                    msg = _("The specified %(k)s '%(v)s' could not be found."
                            ) % {'k': self.FLAVOR, 'v': name_or_id}
                    raise exc.InvalidSpec(message=msg)
                else:
                    raise

        if flavor is not None:
            if not flavor.is_disabled:
                return flavor
            msg = _("The specified %(k)s '%(v)s' is disabled"
                    ) % {'k': self.FLAVOR, 'v': name_or_id}

        if reason == 'create':
            raise exc.EResourceCreation(type='server', message=msg)
        elif reason == 'update':
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=msg)
        else:
            raise exc.InvalidSpec(message=msg)

    def _validate_image(self, obj, name_or_id, reason=None):
        try:
            return self.glance(obj).image_find(name_or_id, False)
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=str(ex))
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))
            elif ex.code == 404:
                msg = _("The specified %(k)s '%(v)s' could not be found."
                        ) % {'k': self.IMAGE, 'v': name_or_id}
                raise exc.InvalidSpec(message=msg)
            else:
                raise

    def _validate_keypair(self, obj, name_or_id, reason=None):
        try:
            return self.compute(obj).keypair_find(name_or_id, False)
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=str(ex))
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))
            elif ex.code == 404:
                msg = _("The specified %(k)s '%(v)s' could not be found."
                        ) % {'k': self.KEY_NAME, 'v': name_or_id}
                raise exc.InvalidSpec(message=msg)
            else:
                raise

    def _validate_volume(self, obj, name_or_id, reason=None):
        try:
            volume = self.block_storage(obj).volume_get(name_or_id)
            if volume.status == 'available':
                return volume

            msg = _("The volume %(k)s should be in 'available' status "
                    "but is in '%(v)s' status."
                    ) % {'k': name_or_id, 'v': volume.status}
            raise exc.InvalidSpec(message=msg)
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=str(ex))
            elif ex.code == 404:
                msg = _("The specified volume '%(k)s' could not be found."
                        ) % {'k': name_or_id}
                raise exc.InvalidSpec(message=msg)
            else:
                raise

    def _validate_volume_type(self, obj, name_or_id, reason=None):
        try:
            return self.block_storage(obj).volume_type_get(name_or_id, False)
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=str(ex))
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))
            elif ex.code == 404:
                msg = _("The specified volume type '%(k)s' could not be found."
                        ) % {'k': name_or_id}
                raise exc.InvalidSpec(message=msg)
            else:
                raise

    def do_validate(self, obj):
        """Validate if the spec has provided valid info for server creation.

        :param obj: The node object.
        """
        # validate availability_zone
        az_name = self.properties[self.AVAILABILITY_ZONE]
        if az_name is not None:
            self._validate_az(obj, az_name)

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

        # validate networks
        networks = self.properties[self.NETWORKS]
        for net in networks:
            self._validate_network(obj, net)

        return True

    def _resolve_bdm(self, obj, bdm, reason=None):
        for bd in bdm:
            for key in self.BDM2_KEYS:
                if bd[key] is None:
                    del bd[key]
            if 'volume_type' in bd:
                bd['volume_type'] = self._validate_volume_type(
                    bd['volume_type'])
            if 'uuid' in bd and 'source_type' in bd:
                if bd['source_type'] == 'image':
                    self._validate_image(obj, bd['uuid'], reason)
                elif bd['source_type'] == 'volume':
                    self._validate_volume(obj, bd['uuid'], reason)

        return bdm

    def _check_security_groups(self, nc, net_spec, result):
        """Check security groups.

        :param nc: network driver connection.
        :param net_spec: the specification to check.
        :param result: the result that is used as return value.
        :returns: None if succeeded or an error message if things go wrong.
        """
        sgs = net_spec.get(self.PORT_SECURITY_GROUPS)
        if not sgs:
            return

        res = []
        try:
            for sg in sgs:
                try:
                    # try to find sg scoped by project first
                    sg_obj = nc.security_group_find(
                        sg, project_id=self.project)
                except exc.InternalError:
                    # if it fails to find sg, try without project scope
                    sg_obj = nc.security_group_find(sg)
                res.append(sg_obj.id)
        except exc.InternalError as ex:
            return str(ex)

        result[self.PORT_SECURITY_GROUPS] = res
        return

    def _check_network(self, nc, net, result):
        """Check the specified network.

        :param nc: network driver connection.
        :param net: the name or ID of network to check.
        :param result: the result that is used as return value.
        :returns: None if succeeded or an error message if things go wrong.
        """
        if net is None:
            return
        try:
            net_obj = nc.network_get(net)
            if net_obj is None:
                return _("The specified network %s could not be found.") % net
            result[self.NETWORK] = net_obj.id
        except exc.InternalError as ex:
            return str(ex)

    def _check_subnet(self, nc, subnet, result):
        """Check the specified subnet.

        :param nc: network driver connection.
        :param subnet: the name or ID of subnet to check.
        :param result: the result that is used as return value.
        :returns: None if succeeded or an error message if things go wrong.
        """
        if subnet is None:
            return
        try:
            net_obj = nc.subnet_get(subnet)
            if net_obj is None:
                return _("The specified subnet %s could not be found."
                         ) % subnet
            result[self.SUBNET] = net_obj.id
        except exc.InternalError as ex:
            return str(ex)

    def _check_port(self, nc, port, result):
        """Check the specified port.

        :param nc: network driver connection.
        :param port: the name or ID of port to check.
        :param result: the result that is used as return value.
        :returns: None if succeeded or an error message if things go wrong.
        """
        if port is None:
            return

        try:
            port_obj = nc.port_find(port)
            if port_obj.status != 'DOWN':
                return _("The status of the port %(p)s must be DOWN"
                         ) % {'p': port}
            result[self.PORT] = port_obj.id
            return
        except exc.InternalError as ex:
            return str(ex)

    def _check_floating_ip(self, nc, net_spec, result):
        """Check floating IP and network, if specified.

        :param nc: network driver connection.
        :param net_spec: the specification to check.
        :param result: the result that is used as return value.
        :returns: None if succeeded or an error message if things go wrong.
        """
        net = net_spec.get(self.FLOATING_NETWORK)
        if net:
            try:
                net_obj = nc.network_get(net)
                if net_obj is None:
                    return _("The floating network %s could not be found."
                             ) % net
                result[self.FLOATING_NETWORK] = net_obj.id
            except exc.InternalError as ex:
                return str(ex)

        flt_ip = net_spec.get(self.FLOATING_IP)
        if not flt_ip:
            return

        try:
            # Find floating ip with this address
            fip = nc.floatingip_find(flt_ip)
            if fip:
                if fip.status == 'ACTIVE':
                    return _('the floating IP %s has been used.') % flt_ip
                result['floating_ip_id'] = fip.id

            # Create a floating IP with address if floating ip unspecified
            if not net:
                return _('Must specify a network to create floating IP')

            result[self.FLOATING_IP] = flt_ip
            return
        except exc.InternalError as ex:
            return str(ex)

    def _validate_network(self, obj, net_spec, reason=None):

        def _verify(error):
            if error is None:
                return

            if reason == 'create':
                raise exc.EResourceCreation(type='server', message=error)
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=error)
            else:
                raise exc.InvalidSpec(message=error)

        nc = self.network(obj)
        result = {}

        # check network
        net = net_spec.get(self.NETWORK)
        error = self._check_network(nc, net, result)
        _verify(error)

        # check subnet
        subnet_net = net_spec.get(self.SUBNET)
        error = self._check_subnet(nc, subnet_net, result)
        _verify(error)

        # check port
        port = net_spec.get(self.PORT)
        error = self._check_port(nc, port, result)
        _verify(error)

        if port is None and net is None:
            _verify(_("One of '%(p)s' and '%(n)s' must be provided"
                      ) % {'p': self.PORT, 'n': self.NETWORK})

        fixed_ip = net_spec.get(self.FIXED_IP)
        if fixed_ip:
            if port is not None:
                _verify(_("The '%(p)s' property and the '%(fip)s' property "
                          "cannot be specified at the same time"
                          ) % {'p': self.PORT, 'fip': self.FIXED_IP})
            result[self.FIXED_IP] = fixed_ip

        # Validate vnic_type input
        vnic_type = net_spec.get(self.VNIC_TYPE, None)
        if vnic_type is not None:
            if vnic_type not in ['normal', 'direct', 'macvtap']:
                _verify(_("vnic_type: '%(v)s' is not supported."
                          "(supported types are: normal, direct, macvtap)"
                          ) % {'v': vnic_type})
            result[self.VNIC_TYPE] = vnic_type

        # Check security_groups
        error = self._check_security_groups(nc, net_spec, result)
        _verify(error)

        # Check floating IP
        error = self._check_floating_ip(nc, net_spec, result)
        _verify(error)

        return result

    def _get_port(self, obj, net_spec):
        """Fetch or create a port.

        :param obj: The node object.
        :param net_spec: The parameters to create a port.
        :returns: Created port object and error message.
        """
        port_id = net_spec.get(self.PORT, None)
        if port_id:
            try:
                port = self.network(obj).port_find(port_id)
                return port, None
            except exc.InternalError as ex:
                return None, ex
        port_attr = {
            'network_id': net_spec.get(self.NETWORK),
        }
        fixed_ips = {}
        fixed_ip = net_spec.get(self.FIXED_IP, None)
        if fixed_ip:
            fixed_ips['fixed_ip'] = fixed_ip
        subnet = net_spec.get(self.SUBNET, None)
        if subnet:
            fixed_ips['subnet_id'] = subnet
        if fixed_ips:
            port_attr['fixed_ips'] = [fixed_ips]
        security_groups = net_spec.get(self.PORT_SECURITY_GROUPS, [])
        if security_groups:
            port_attr['security_groups'] = security_groups
        vnic_type = net_spec.get(self.VNIC_TYPE, None)
        if vnic_type:
            port_attr['binding_vnic_type'] = vnic_type
        try:
            port = self.network(obj).port_create(**port_attr)
            LOG.debug('Network port_attr : %s', port)
            return port, None
        except exc.InternalError as ex:
            return None, ex

    def _delete_ports(self, obj, ports):
        """Delete ports.

        :param obj: The node object
        :param ports: A list of internal ports.
        :returns: None for succeed or error for failure.
        """
        pp = copy.deepcopy(ports)
        for port in pp:
            # remove port created by senlin
            if port.get('remove', False):
                try:
                    # remove floating IP created by senlin
                    if port.get('floating', None) and port[
                            'floating'].get('remove', False):
                        self.network(obj).floatingip_delete(
                            port['floating']['id'])
                    self.network(obj).port_delete(port['id'])
                except exc.InternalError as ex:
                    return ex
                ports.remove(port)
        node_data = obj.data
        node_data['internal_ports'] = ports
        node_obj.Node.update(self.context, obj.id, {'data': node_data})

    def _get_floating_ip(self, obj, fip_spec, port_id):
        """Find or Create a floating IP.

        :param obj: The node object.
        :param fip_spec: The parameters to create a floating ip
        :param port_id: The port ID to associate with
        :returns: A floating IP object and error message.
        """
        floating_ip_id = fip_spec.get('floating_ip_id', None)
        if floating_ip_id:
            try:
                fip = self.network(obj).floatingip_find(floating_ip_id)
                if fip.port_id is None:
                    attr = {'port_id': port_id}
                    fip = self.network(obj).floatingip_update(fip, **attr)
                return fip, None
            except exc.InternalError as ex:
                return None, ex
        net_id = fip_spec.get(self.FLOATING_NETWORK)
        fip_addr = fip_spec.get(self.FLOATING_IP)
        attr = {
            'port_id': port_id,
            'floating_network_id': net_id,
        }
        if fip_addr:
            attr.update({'floating_ip_address': fip_addr})
        try:
            fip = self.network(obj).floatingip_create(**attr)
            return fip, None
        except exc.InternalError as ex:
            return None, ex

    def _create_ports_from_properties(self, obj, networks, action_type):
        """Create or find ports based on networks property.

        :param obj: The node object.
        :param networks: The networks property used for node.
        :param action_type: Either 'create' or 'update'.

        :returns: A list of created port's attributes.
        """
        internal_ports = obj.data.get('internal_ports', [])
        if not networks:
            return []

        for net_spec in networks:
            net = self._validate_network(obj, net_spec, action_type)
            # Create port
            port, ex = self._get_port(obj, net)
            # Delete created ports before raise error
            if ex:
                d_ex = self._delete_ports(obj, internal_ports)
                if d_ex:
                    raise d_ex
                else:
                    raise ex
            port_attrs = {
                'id': port.id,
                'network_id': port.network_id,
                'security_group_ids': port.security_group_ids,
                'fixed_ips': port.fixed_ips
            }
            if self.PORT not in net:
                port_attrs.update({'remove': True})
            # Create floating ip
            if 'floating_ip_id' in net or self.FLOATING_NETWORK in net:
                fip, ex = self._get_floating_ip(obj, net, port_attrs['id'])
                if ex:
                    d_ex = self._delete_ports(obj, internal_ports)
                    if d_ex:
                        raise d_ex
                    else:
                        raise ex
                port_attrs['floating'] = {
                    'id': fip.id,
                    'floating_ip_address': fip.floating_ip_address,
                    'floating_network_id': fip.floating_network_id,
                }
                if self.FLOATING_NETWORK in net:
                    port_attrs['floating'].update({'remove': True})
            internal_ports.append(port_attrs)
        if internal_ports:
            try:
                node_data = obj.data
                node_data.update(internal_ports=internal_ports)
                node_obj.Node.update(self.context, obj.id, {'data': node_data})
            except exc.ResourceNotFound:
                self._rollback_ports(obj, internal_ports)
                raise
        return internal_ports

    def _build_metadata(self, obj, usermeta):
        """Build custom metadata for server.

        :param obj: The node object to operate on.
        :return: A dictionary containing the new metadata.
        """
        metadata = usermeta or {}
        metadata['cluster_node_id'] = obj.id
        if obj.cluster_id:
            metadata['cluster_id'] = obj.cluster_id
            metadata['cluster_node_index'] = str(obj.index)

        return metadata

    def _update_zone_info(self, obj, server):
        """Update the actual zone placement data.

        :param obj: The node object associated with this server.
        :param server: The server object returned from creation.
        """
        if server.availability_zone:
            placement = obj.data.get('placement', None)
            if not placement:
                obj.data['placement'] = {'zone': server.availability_zone}
            else:
                obj.data['placement'].setdefault('zone',
                                                 server.availability_zone)
            # It is safe to use admin context here
            ctx = context.get_admin_context()
            node_obj.Node.update(ctx, obj.id, {'data': obj.data})

    def do_create(self, obj):
        """Create a server for the node object.

        :param obj: The node object for which a server will be created.
        """
        kwargs = self._generate_kwargs()

        admin_pass = self.properties[self.ADMIN_PASS]
        if admin_pass:
            kwargs.pop(self.ADMIN_PASS)
            kwargs['adminPass'] = admin_pass

        auto_disk_config = self.properties[self.AUTO_DISK_CONFIG]
        kwargs.pop(self.AUTO_DISK_CONFIG)
        kwargs['OS-DCF:diskConfig'] = 'AUTO' if auto_disk_config else 'MANUAL'

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

        kwargs['name'] = self.properties[self.NAME] or obj.name

        metadata = self._build_metadata(obj, self.properties[self.METADATA])
        kwargs['metadata'] = metadata

        block_device_mapping_v2 = self.properties[self.BLOCK_DEVICE_MAPPING_V2]
        if block_device_mapping_v2 is not None:
            kwargs['block_device_mapping_v2'] = self._resolve_bdm(
                obj, block_device_mapping_v2, 'create')

        user_data = self.properties[self.USER_DATA]
        if user_data is not None:
            ud = encodeutils.safe_encode(user_data)
            kwargs['user_data'] = encodeutils.safe_decode(base64.b64encode(ud))

        networks = self.properties[self.NETWORKS]
        ports = None
        if networks is not None:
            ports = self._create_ports_from_properties(
                obj, networks, 'create')
            kwargs['networks'] = [
                {'port': port['id']} for port in ports]

        secgroups = self.properties[self.SECURITY_GROUPS]
        if secgroups:
            kwargs['security_groups'] = [{'name': sg} for sg in secgroups]

        if 'placement' in obj.data:
            if 'zone' in obj.data['placement']:
                kwargs['availability_zone'] = obj.data['placement']['zone']

            if 'servergroup' in obj.data['placement']:
                group_id = obj.data['placement']['servergroup']
                hints = self.properties.get(self.SCHEDULER_HINTS) or {}
                hints.update({'group': group_id})
                kwargs['scheduler_hints'] = hints

        server = None
        resource_id = None
        try:
            server = self.compute(obj).server_create(**kwargs)
            self.compute(obj).wait_for_server(
                server.id, timeout=cfg.CONF.default_nova_timeout)
            server = self.compute(obj).server_get(server.id)
            # Update zone placement info if available
            self._update_zone_info(obj, server)
            return server.id
        except exc.ResourceNotFound:
            self._rollback_ports(obj, ports)
            self._rollback_instance(obj, server)
            raise
        except exc.InternalError as ex:
            if server and server.id:
                resource_id = server.id
                LOG.debug('Deleting server %s that is ERROR state after'
                          ' create.', server.id)

                try:
                    obj.physical_id = server.id
                    self.do_delete(obj, internal_ports=ports)
                except Exception:
                    LOG.error('Failed to delete server %s', server.id)
                    pass
            elif ports:
                self._delete_ports(obj, ports)
            raise exc.EResourceCreation(type='server',
                                        message=str(ex),
                                        resource_id=resource_id)

    def _generate_kwargs(self):
        """Generate the base kwargs for a server.

        :return:
        """
        kwargs = {}
        for key in self.KEYS:
            # context is treated as connection parameters
            if key == self.CONTEXT:
                continue

            if self.properties[key] is not None:
                kwargs[key] = self.properties[key]
        return kwargs

    def _rollback_ports(self, obj, ports):
        """Rollback any ports created after a ResourceNotFound exception.

        :param obj: The node object.
        :param ports: A list of ports which attached to this server.
        :return:
        """
        if not ports:
            return

        LOG.warning(
            'Rolling back ports for Node %s.',
            obj.id
        )

        for port in ports:
            if not port.get('remove', False):
                continue
            try:
                if (port.get('floating') and
                        port['floating'].get('remove', False)):
                    self.network(obj).floatingip_delete(
                        port['floating']['id']
                    )
                self.network(obj).port_delete(port['id'])
            except exc.InternalError as ex:
                LOG.debug(
                    'Failed to delete port %s during rollback for Node %s: %s',
                    port['id'], obj.id, ex
                )

    def _rollback_instance(self, obj, server):
        """Rollback an instance created after a ResourceNotFound exception.

        :param obj: The node object.
        :param server: A server.
        :return:
        """
        if not server or not server.id:
            return

        LOG.warning(
            'Rolling back instance %s for Node %s.',
            server.id, obj.id
        )

        try:
            self.compute(obj).server_force_delete(server.id, True)
        except exc.InternalError as ex:
            LOG.debug(
                'Failed to delete instance %s during rollback for Node %s: %s',
                server.id, obj.id, ex
            )

    def do_delete(self, obj, **params):
        """Delete the physical resource associated with the specified node.

        :param obj: The node object to operate on.
        :param kwargs params: Optional keyword arguments for the delete
                              operation.
        :returns: This operation always return True unless exception is
                  caught.
        :raises: `EResourceDeletion` if interaction with compute service fails.
        """
        server_id = obj.physical_id
        ignore_missing = params.get('ignore_missing', True)
        internal_ports = obj.data.get('internal_ports', [])
        force = params.get('force', False)
        timeout = params.get('timeout', cfg.CONF.default_nova_timeout)

        try:
            if server_id:
                driver = self.compute(obj)
                if force:
                    driver.server_force_delete(server_id, ignore_missing)
                else:
                    driver.server_delete(server_id, ignore_missing)

                driver.wait_for_server_delete(server_id, timeout=timeout)
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='server', id=server_id,
                                        message=str(ex))
        finally:
            if internal_ports:
                ex = self._delete_ports(obj, internal_ports)
                if ex:
                    raise exc.EResourceDeletion(type='server', d=server_id,
                                                message=str(ex))
        return True

    def _check_server_name(self, obj, profile):
        """Check if there is a new name to be assigned to the server.

        :param obj: The node object to operate on.
        :param new_profile: The new profile which may contain a name for
                            the server instance.
        :return: A tuple consisting a boolean indicating whether the name
                 needs change and the server name determined.
        """
        old_name = self.properties[self.NAME] or obj.name
        new_name = profile.properties[self.NAME] or obj.name
        if old_name == new_name:
            return False, new_name
        return True, new_name

    def _update_name(self, obj, new_name):
        """Update the name of the server.

        :param obj: The node object to operate.
        :param new_name: The new name for the server instance.
        :return: ``None``.
        :raises: ``EResourceUpdate``.
        """
        try:
            self.compute(obj).server_update(obj.physical_id, name=new_name)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))

    def _check_password(self, obj, new_profile):
        """Check if the admin password has been changed in the new profile.

        :param obj: The server node to operate, not used currently.
        :param new_profile: The new profile which may contain a new password
                            for the server instance.
        :return: A tuple consisting a boolean indicating whether the password
                 needs a change and the password determined which could be
                 '' if new password is not set.
        """
        old_passwd = self.properties.get(self.ADMIN_PASS) or ''
        new_passwd = new_profile.properties[self.ADMIN_PASS] or ''
        if old_passwd == new_passwd:
            return False, new_passwd
        return True, new_passwd

    def _update_password(self, obj, new_password):
        """Update the admin password for the server.

        :param obj: The node object to operate.
        :param new_password: The new password for the server instance.
        :return: ``None``.
        :raises: ``EResourceUpdate``.
        """
        try:
            self.compute(obj).server_change_password(obj.physical_id,
                                                     new_password)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))

    def _update_metadata(self, obj, new_profile):
        """Update the server metadata.

        :param obj: The node object to operate on.
        :param new_profile: The new profile that may contain some changes to
                            the metadata.
        :returns: ``None``
        :raises: `EResourceUpdate`.
        """
        old_meta = self._build_metadata(obj, self.properties[self.METADATA])
        new_meta = self._build_metadata(obj,
                                        new_profile.properties[self.METADATA])
        if new_meta == old_meta:
            return

        try:
            self.compute(obj).server_metadata_update(obj.physical_id, new_meta)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))

    def _update_flavor(self, obj, new_profile):
        """Update server flavor.

        :param obj: The node object to operate on.
        :param old_flavor: The identity of the current flavor.
        :param new_flavor: The identity of the new flavor.
        :returns: Returns true if the flavor was updated or false otherwise.
        :raises: `EResourceUpdate` when operation was a failure.
        """
        old_flavor = self.properties[self.FLAVOR]
        new_flavor = new_profile.properties[self.FLAVOR]
        cc = self.compute(obj)
        oldflavor = self._validate_flavor(obj, old_flavor, 'update')
        newflavor = self._validate_flavor(obj, new_flavor, 'update')
        if oldflavor.id == newflavor.id:
            return False

        try:
            # server has to be active or stopped in order to resize
            # stop server if it is active
            server = cc.server_get(obj.physical_id)
            if server.status == consts.VS_ACTIVE:
                cc.server_stop(obj.physical_id)
                cc.wait_for_server(obj.physical_id, consts.VS_SHUTOFF,
                                   timeout=self.stop_timeout)
            elif server.status != consts.VS_SHUTOFF:
                raise exc.InternalError(
                    message='Server needs to be ACTIVE or STOPPED in order to'
                            ' update flavor.')
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))

        try:
            cc.server_resize(obj.physical_id, newflavor.id)
            cc.wait_for_server(obj.physical_id, 'VERIFY_RESIZE')
        except exc.InternalError as ex:
            msg = str(ex)
            try:
                server = cc.server_get(obj.physical_id)
                if server.status == 'RESIZE':
                    cc.server_resize_revert(obj.physical_id)
                    cc.wait_for_server(obj.physical_id, consts.VS_SHUTOFF)

                # start server back up in case of exception during resize
                cc.server_start(obj.physical_id)
                cc.wait_for_server(obj.physical_id, consts.VS_ACTIVE)
            except exc.InternalError as ex1:
                msg = str(ex1)
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=msg)

        try:
            cc.server_resize_confirm(obj.physical_id)
            cc.wait_for_server(obj.physical_id, consts.VS_SHUTOFF)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))

        return True

    def _update_image(self, obj, new_profile, new_name, new_password):
        """Update image used by server node.

        :param obj: The node object to operate on.
        :param new_profile: The profile which may contain a new image name or
                            ID to use.
        :param new_name: The name for the server node.
        :param newn_password: The new password for the administrative account
                              if provided.
        :returns: A boolean indicating whether the image needs an update.
        :raises: ``InternalError`` if operation was a failure.
        """
        new_image = new_profile.properties[self.IMAGE]
        if not new_image:
            msg = _("Updating Nova server with image set to None is not "
                    "supported by Nova")
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=msg)
        # check the new image first
        img_new = self._validate_image(obj, new_image, reason='update')
        new_image_id = img_new.id

        driver = self.compute(obj)

        try:
            server = driver.server_get(obj.physical_id)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))
        old_image_id = self._get_image_id(obj, server, 'updating')

        if new_image_id == old_image_id:
            return False

        try:
            # server has to be active or stopped in order to resize
            # stop server if it is active
            if server.status == consts.VS_ACTIVE:
                driver.server_stop(obj.physical_id)
                driver.wait_for_server(obj.physical_id, consts.VS_SHUTOFF,
                                       timeout=self.stop_timeout)
            elif server.status != consts.VS_SHUTOFF:
                raise exc.InternalError(
                    message='Server needs to be ACTIVE or STOPPED in order to'
                            ' update image.')

            driver.server_rebuild(obj.physical_id, new_image_id,
                                  new_name, new_password)
            driver.wait_for_server(obj.physical_id, consts.VS_SHUTOFF)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))
        return True

    def _update_network_add_port(self, obj, networks):
        """Create new interfaces for the server node.

        :param obj: The node object to operate.
        :param networks: A list containing information about new network
                         interfaces to be created.
        :returns: ``None``.
        :raises: ``EResourceUpdate`` if interaction with drivers failed.
        """
        cc = self.compute(obj)
        try:
            server = cc.server_get(obj.physical_id)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))

        ports = self._create_ports_from_properties(
            obj, networks, 'update')
        for port in ports:
            params = {'port_id': port['id']}
            try:
                cc.server_interface_create(server, **params)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server',
                                          id=obj.physical_id,
                                          message=str(ex))

    def _find_port_by_net_spec(self, obj, net_spec, ports):
        """Find existing ports match with specific network properties.

        :param obj: The node object.
        :param net_spec: Network property of this profile.
        :param ports: A list of ports which attached to this server.
        :returns: A list of candidate ports matching this network spec.
        """
        # TODO(anyone): handle security_groups
        net = self._validate_network(obj, net_spec, 'update')
        selected_ports = []
        for p in ports:
            floating = p.get('floating', {})
            floating_network = net.get(self.FLOATING_NETWORK, None)
            if floating_network and floating.get(
                    'floating_network_id') != floating_network:
                continue
            floating_ip_address = net.get(self.FLOATING_IP, None)
            if floating_ip_address and floating.get(
                    'floating_ip_address') != floating_ip_address:
                continue
            # If network properties didn't contain floating ip,
            # then we should better not make a port with floating ip
            # as candidate.
            if (floating and not floating_network and not floating_ip_address):
                continue
            port_id = net.get(self.PORT, None)
            if port_id and p['id'] != port_id:
                continue
            fixed_ip = net.get(self.FIXED_IP, None)
            if fixed_ip:
                fixed_ips = [ff['ip_address'] for ff in p['fixed_ips']]
                if fixed_ip not in fixed_ips:
                    continue
            network = net.get(self.NETWORK, None)
            if network:
                net_id = self.network(obj).network_get(network).id
                if p['network_id'] != net_id:
                    continue
            selected_ports.append(p)
        return selected_ports

    def _update_network_remove_port(self, obj, networks):
        """Delete existing interfaces from the node.

        :param obj: The node object to operate.
        :param networks: A list containing information about network
                         interfaces to be created.
        :returns: ``None``
        :raises: ``EResourceUpdate``
        """
        cc = self.compute(obj)
        nc = self.network(obj)
        internal_ports = obj.data.get('internal_ports', [])

        if networks:
            try:
                # stop server if it is active
                server = cc.server_get(obj.physical_id)
                if server.status == consts.VS_ACTIVE:
                    cc.server_stop(obj.physical_id)
                    cc.wait_for_server(obj.physical_id, consts.VS_SHUTOFF,
                                       timeout=self.stop_timeout)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))

        for n in networks:
            candidate_ports = self._find_port_by_net_spec(
                obj, n, internal_ports)
            port = candidate_ports[0]
            try:
                # Detach port from server
                cc.server_interface_delete(port['id'], obj.physical_id)
                # delete port if created by senlin
                if port.get('remove', False):
                    nc.port_delete(port['id'], ignore_missing=True)
                # delete floating IP if created by senlin
                if (port.get('floating', None) and
                        port['floating'].get('remove', False)):
                    nc.floatingip_delete(port['floating']['id'],
                                         ignore_missing=True)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))
            internal_ports.remove(port)
        obj.data['internal_ports'] = internal_ports
        node_obj.Node.update(self.context, obj.id, {'data': obj.data})

    def _nw_compare(self, n1, n2, property):
        return n1.get(property, None) == n2.get(property, None)

    def _update_network_update_port(self, obj, networks):
        """Update existing port in network from the node.

           Currently only update to security group is supported.

        :param obj: The node object to operate.
        :param networks: A list networks that contain updated security groups.
        :returns: ``None``
        :raises: ``EResourceUpdate``
        """
        nc = self.network(obj)
        internal_ports = obj.data.get('internal_ports', [])

        # process each network to be updated
        for n in networks:
            # verify network properties and resolve names into ids
            net = self._validate_network(obj, n, 'update')

            # find existing port that matches network
            candidate_ports = self._find_port_by_net_spec(
                obj, net, internal_ports)
            port = candidate_ports[0]
            try:
                # set updated security groups for port
                port_attr = {
                    'security_groups': net.get(self.PORT_SECURITY_GROUPS, []),
                }
                LOG.debug("Setting security groups %s for port %s",
                          port_attr, port['id'])
                nc.port_update(port['id'], **port_attr)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))

    def _update_network(self, obj, new_profile):
        """Updating server network interfaces.

        :param obj: The node object to operate.
        :param new_profile: The new profile which may contain new network
                            settings.
        :return: Returns a tuple of booleans if network was created or deleted.
        :raises: ``EResourceUpdate`` if there are driver failures.
        """
        networks_current = self.properties[self.NETWORKS]
        networks_create = new_profile.properties[self.NETWORKS]
        networks_delete = copy.deepcopy(networks_current)
        networks_update = []

        for nw in networks_current:
            if nw in networks_create:
                # network already exist.  no need to create or delete it.
                LOG.debug("Network %s already exists, skip create/delete", nw)
                networks_create.remove(nw)
                networks_delete.remove(nw)

        # find networks for which only security group changed
        for nw in networks_current:
            # networks to be created with only sg changes
            sg_create_nw = [n for n in networks_create
                            if (self._nw_compare(n, nw, 'network') and
                                self._nw_compare(n, nw, 'port') and
                                self._nw_compare(n, nw, 'fixed_ip') and
                                self._nw_compare(n, nw, 'floating_network') and
                                self._nw_compare(n, nw, 'floating_ip') and
                                self._nw_compare(n, nw, 'subnet'))]
            for n in sg_create_nw:
                # don't create networks with only security group changes
                LOG.debug("Network %s only has security group changes, "
                          "don't create/delete it.  Only update it.", n)
                networks_create.remove(n)
                networks_update.append(n)
                if nw in networks_delete:
                    networks_delete.remove(nw)

        # update network
        if networks_update:
            self._update_network_update_port(obj, networks_update)

        # Detach some existing interfaces
        if networks_delete:
            self._update_network_remove_port(obj, networks_delete)

        # Attach new interfaces
        if networks_create:
            self._update_network_add_port(obj, networks_create)

        return networks_create, networks_delete

    def do_update(self, obj, new_profile=None, **params):
        """Perform update on the server.

        :param obj: the server to operate on
        :param new_profile: the new profile for the server.
        :param params: a dictionary of optional parameters.
        :returns: True if update was successful or False otherwise.
        :raises: `EResourceUpdate` if operation fails.
        """
        if not obj.physical_id:
            return False

        if not new_profile:
            return False

        if not self.validate_for_update(new_profile):
            return False

        self.stop_timeout = params.get('cluster.stop_timeout_before_update',
                                       cfg.CONF.default_nova_timeout)

        if not isinstance(self.stop_timeout, int):
            raise exc.EResourceUpdate(
                type='server', id=obj.physical_id,
                message='cluster.stop_timeout_before_update value must be of '
                        'type int.')

        name_changed, new_name = self._check_server_name(obj, new_profile)
        passwd_changed, new_passwd = self._check_password(obj, new_profile)
        # Update server image: may have side effect of changing server name
        # and/or admin password
        image_changed = self._update_image(obj, new_profile, new_name,
                                           new_passwd)
        if not image_changed:
            # we do this separately only when rebuild wasn't performed
            if name_changed:
                self._update_name(obj, new_name)
            if passwd_changed:
                self._update_password(obj, new_passwd)

        # Update server flavor: note that flavor is a required property
        flavor_changed = self._update_flavor(obj, new_profile)
        network_created, network_deleted = self._update_network(
            obj, new_profile)

        # TODO(Yanyan Hu): Update block_device properties
        # Update server metadata
        self._update_metadata(obj, new_profile)

        # start server if it was stopped as part of this update operation
        if image_changed or flavor_changed or network_deleted:
            cc = self.compute(obj)
            try:
                server = cc.server_get(obj.physical_id)
                if server.status == consts.VS_SHUTOFF:
                    cc.server_start(obj.physical_id)
                    cc.wait_for_server(obj.physical_id, consts.VS_ACTIVE)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=str(ex))

        return True

    def do_get_details(self, obj):
        known_keys = {
            'OS-DCF:diskConfig',
            'OS-EXT-AZ:availability_zone',
            'OS-EXT-STS:power_state',
            'OS-EXT-STS:vm_state',
            'accessIPv4',
            'accessIPv6',
            'config_drive',
            'created',
            'hostId',
            'id',
            'key_name',
            'locked',
            'metadata',
            'name',
            'os-extended-volumes:volumes_attached',
            'progress',
            'status',
            'updated'
        }
        if obj.physical_id is None or obj.physical_id == '':
            return {}

        driver = self.compute(obj)
        try:
            server = driver.server_get(obj.physical_id)
        except exc.InternalError as ex:
            return {
                'Error': {
                    'code': ex.code,
                    'message': str(ex)
                }
            }

        if server is None:
            return {}
        server_data = server.to_dict()
        if 'id' in server_data['image']:
            image_id = server_data['image']['id']
        else:
            image_id = server_data['image']
        attached_volumes = []
        if ('attached_volumes' in server_data and
                len(server_data['attached_volumes']) > 0):
            for volume in server_data['attached_volumes']:
                attached_volumes.append(volume['id'])
        details = {
            'image': image_id,
            'attached_volumes': attached_volumes,
            'flavor': self._get_flavor_id(obj, server_data),
        }
        for key in known_keys:
            if key in server_data:
                details[key] = server_data[key]

        # process special keys like 'OS-EXT-STS:task_state': these keys have
        # a default value '-' when not existing
        special_keys = [
            'OS-EXT-STS:task_state',
            'OS-SRV-USG:launched_at',
            'OS-SRV-USG:terminated_at',
        ]
        for key in special_keys:
            if key in server_data:
                val = server_data[key]
                details[key] = val if val else '-'

        # process network addresses
        details['addresses'] = copy.deepcopy(server_data['addresses'])

        # process security groups
        sgroups = []
        if 'security_groups' in server_data:
            if server_data['security_groups'] is not None:
                for sg in server_data['security_groups']:
                    sgroups.append(sg['name'])
        # when we have multiple nics the info will include the
        # security groups N times where N == number of nics. Be nice
        # and only display it once.
        sgroups = list(set(sgroups))
        if len(sgroups) == 0:
            details['security_groups'] = ''
        elif len(sgroups) == 1:
            details['security_groups'] = sgroups[0]
        else:
            details['security_groups'] = sgroups

        return dict((k, details[k]) for k in sorted(details))

    def _get_flavor_id(self, obj, server):
        """Get flavor id.

        :param obj: The node object.
        :param dict server: The server object.
        :return: The flavor_id for the server.
        """
        flavor = server['flavor']
        flavor_name = flavor.get('name') or flavor.get('original_name')
        return self.compute(obj).flavor_find(flavor_name, False).id

    def _get_image_id(self, obj, server, op):
        """Get image id.

        :param obj: The node object.
        :param server: The server object.
        :param op: The operate on the node.
        :return: The image_id for the server.
        """
        image_id = None

        if server.image:
            image_id = server.image['id'] or server.image
        # when booting a nova server from volume, the image property
        # can be ignored.
        # we try to find a volume which is bootable and use its image_id
        # for the server.
        elif server.attached_volumes:
            cinder_driver = self.block_storage(obj)
            for volume_ids in server.attached_volumes:
                try:
                    vs = cinder_driver.volume_get(volume_ids['id'])
                    if vs.is_bootable:
                        image_id = vs.volume_image_metadata['image_id']
                except exc.InternalError as ex:
                    raise exc.EResourceOperation(op=op, type='server',
                                                 id=obj.physical_id,
                                                 message=str(ex))
        else:
            msg = _("server doesn't have an image and it has no "
                    "bootable volume")
            raise exc.EResourceOperation(op=op, type="server",
                                         id=obj.physical_id,
                                         message=msg)
        return image_id

    def _handle_generic_op(self, obj, driver_func_name,
                           op_name, expected_server_status=None,
                           **kwargs):
        """Generic handler for standard server operations."""
        if not obj.physical_id:
            return False
        server_id = obj.physical_id
        nova_driver = self.compute(obj)

        try:
            driver_func = getattr(nova_driver, driver_func_name)
            driver_func(server_id, **kwargs)
            if expected_server_status:
                nova_driver.wait_for_server(server_id, expected_server_status)
            return True
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op=op_name, type='server',
                                         id=server_id,
                                         message=str(ex))

    def do_adopt(self, obj, overrides=None, snapshot=False):
        """Adopt an existing server node for management.

        :param obj: A node object for this operation. It could be a puppet
            node that provides only 'user', 'project' and 'physical_id'
            properties when doing a preview. It can be a real Node object for
            node adoption.
        :param overrides: A dict containing the properties that will be
            overridden when generating a profile for the server.
        :param snapshot: A boolean flag indicating whether the profile should
            attempt a snapshot operation before adopting the server. If set to
            True, the ID of the snapshot will be used as the image ID.

        :returns: A dict containing the spec created from the server object or
            a dict containing error information if failure occurred.
        """
        driver = self.compute(obj)

        # TODO(Qiming): Add snapshot support
        # snapshot = driver.snapshot_create(...)

        error = {}
        try:
            server = driver.server_get(obj.physical_id)
        except exc.InternalError as ex:
            error = {'code': ex.code, 'message': str(ex)}

        if error:
            return {'Error': error}

        spec = {}
        # Context?
        # TODO(Qiming): Need to fetch admin password from a different API
        spec[self.AUTO_DISK_CONFIG] = server.disk_config == 'AUTO'

        spec[self.AVAILABILITY_ZONE] = server.availability_zone

        # TODO(Anyone): verify if this needs a format conversion
        bdm = server.block_device_mapping or []
        spec[self.BLOCK_DEVICE_MAPPING_V2] = bdm

        spec[self.CONFIG_DRIVE] = server.has_config_drive or False
        spec[self.FLAVOR] = server.flavor['id']
        spec[self.IMAGE] = self._get_image_id(obj, server, 'adopting')
        spec[self.KEY_NAME] = server.key_name

        # metadata
        metadata = server.metadata or {}
        metadata.pop('cluster_id', None)
        metadata.pop('cluster_node_id', None)
        metadata.pop('cluster_node_index', None)
        spec[self.METADATA] = metadata

        # name
        spec[self.NAME] = server.name

        networks = server.addresses
        net_list = []
        for network, interfaces in networks.items():
            for intf in interfaces:
                ip_type = intf.get('OS-EXT-IPS:type')
                net = {self.NETWORK: network}
                if ip_type == 'fixed' and net not in net_list:
                    net_list.append({self.NETWORK: network})

        spec[self.NETWORKS] = net_list
        # NOTE: the personality attribute is missing for ever.
        spec[self.SECURITY_GROUPS] = [
            sg['name'] for sg in server.security_groups
        ]
        # TODO(Qiming): get server user_data and parse it.
        # Note: user_data is returned in 2.3 microversion API, in a different
        # property name.
        # spec[self.USER_DATA] = server.user_data

        if overrides:
            spec.update(overrides)

        return spec

    def do_join(self, obj, cluster_id):
        if not obj.physical_id:
            return False

        driver = self.compute(obj)
        try:
            metadata = {}
            metadata['cluster_id'] = cluster_id
            metadata['cluster_node_index'] = str(obj.index)
            driver.server_metadata_update(obj.physical_id, metadata)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=str(ex))
        return super(ServerProfile, self).do_join(obj, cluster_id)

    def do_leave(self, obj):
        if not obj.physical_id:
            return False

        keys = ['cluster_id', 'cluster_node_index']
        try:
            self.compute(obj).server_metadata_delete(obj.physical_id, keys)
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='server', id=obj.physical_id,
                                        message=str(ex))
        return super(ServerProfile, self).do_leave(obj)

    def do_check(self, obj):
        if not obj.physical_id:
            return False

        try:
            server = self.compute(obj).server_get(obj.physical_id)
        except exc.InternalError as ex:
            if ex.code == 404:
                raise exc.EServerNotFound(type='server',
                                          id=obj.physical_id,
                                          message=str(ex))
            else:
                raise exc.EResourceOperation(op='checking', type='server',
                                             id=obj.physical_id,
                                             message=str(ex))

        if (server is None or server.status != consts.VS_ACTIVE):
            return False

        return True

    def do_healthcheck(self, obj, health_check_type):
        """Healthcheck operation.

        This method checks if a node is healthy.  If health check type is
        NODE_STATUS_POLLING it will check the server status.  If health check
        type is HYPERVISOR_STATUS_POLLING it will check the hypervisor state
        and status.

        :param obj: The node object to operate on.
        :param health_check_type: The type of health check.  Either
        NODE_STATUS_POLLING or HYPERVISOR_STATUS_POLLING.
        :return status: True indicates node is healthy, False indicates
            it is unhealthy.
        """

        if not obj.physical_id:
            if obj.status == 'BUILD' or obj.status == 'CREATING':
                return True

            LOG.info('%s for %s: server has no physical ID.',
                     consts.POLL_STATUS_FAIL, obj.name)
            return False

        try:
            server = self.compute(obj).server_get(obj.physical_id)
        except Exception as ex:
            if isinstance(ex, exc.InternalError) and ex.code == 404:
                # treat resource not found exception as unhealthy
                LOG.info('%s for %s: server was not found.',
                         consts.POLL_STATUS_FAIL, obj.name)
                return False
            else:
                # treat all other exceptions as healthy
                LOG.info(
                    '%s for %s: Exception when trying to get server info but '
                    'ignoring this error: %s.',
                    consts.POLL_STATUS_PASS, obj.name, ex.message)
                return True

        if server is None:
            # no server information is available, treat the node as healthy
            LOG.info(
                '%s for %s: No server information was returned but ignoring '
                'this error.',
                consts.POLL_STATUS_PASS, obj.name)
            return True

        if health_check_type == consts.NODE_STATUS_POLLING:
            return self._do_healthcheck_server(obj, server)
        elif health_check_type == consts.HYPERVISOR_STATUS_POLLING:
            return self._do_healthcheck_hypervisor(obj, server)
        else:
            LOG.info('%s for %s: ignoring invalid health check type %s',
                     consts.POLL_STATUS_PASS, obj.name, health_check_type)
            return True

    def _do_healthcheck_server(self, obj, server):
        """Healthcheck operation based on server.

        This method checks if a server node is healthy by getting the server
        status from nova.  A server is considered unhealthy if it does not
        exist or its status is one of the following:
        - ERROR
        - SHUTOFF
        - DELETED

        :param obj: The node object to operate on.
        :param server: The server object associated with the node.
        :return status: True indicates node is healthy, False indicates
            it is unhealthy.
        """

        unhealthy_server_status = [consts.VS_ERROR, consts.VS_SHUTOFF,
                                   consts.VS_DELETED]

        if server.status in unhealthy_server_status:
            LOG.info('%s for %s: server status is unhealthy.',
                     consts.POLL_STATUS_FAIL, obj.name)
            return False

        LOG.info('%s for %s', consts.POLL_STATUS_PASS, obj.name)
        return True

    def _do_healthcheck_hypervisor(self, obj, server):
        """Healthcheck operation based on hypervisor.

        This method checks if a server node is healthy by getting the
        hypervisor state and status from nova.  A server is considered
        unhealthy if the hypervisor it is running on has a state that is down
        or a status that is disabled.

        :param obj: The node object to operate on.
        :param server: The server object associated with the node.
        :return status: True indicates node is healthy, False indicates
            it is unhealthy.
        """

        if server.hypervisor_hostname != "":
            try:
                hv = self.compute(obj).hypervisor_find(
                    server.hypervisor_hostname)
            except Exception as ex:
                if isinstance(ex, exc.InternalError) and ex.code == 404:
                    # treat resource not found exception as unhealthy
                    LOG.info('%s for %s: hypervisor %s was not found.',
                             consts.POLL_STATUS_FAIL, obj.name,
                             server.hypervisor_hostname)
                    return False
                else:
                    # treat all other exceptions as healthy
                    LOG.info(
                        '%s for %s: Exception when trying to get hypervisor '
                        'info for %s, but ignoring this error: %s.',
                        consts.POLL_STATUS_PASS, obj.name,
                        server.hypervisor_hostname, ex.message)
                    return True

            if hv is None:
                # no hypervisor information is available, treat the node as
                # healthy
                LOG.info(
                    '%s for %s: No hypervisor information was returned but '
                    'ignoring this error.',
                    consts.POLL_STATUS_PASS, obj.name)
                return True

            if hv.state == 'down':
                LOG.info('%s for %s: server status is unhealthy because '
                         'hypervisor %s state is down',
                         consts.POLL_STATUS_FAIL, obj.name,
                         server.hypervisor_hostname)
                return False

            if hv.status == 'disabled':
                LOG.info('%s for %s: server status is unhealthy because '
                         'hypervisor %s status is disabled',
                         consts.POLL_STATUS_FAIL, obj.name,
                         server.hypervisor_hostname)
                return False

        LOG.info('%s for %s', consts.POLL_STATUS_PASS, obj.name)
        return True

    def do_recover(self, obj, **options):
        """Handler for recover operation.

        :param obj: The node object.
        :param dict options: A list for operations each of which has a name
            and optionally a map from parameter to values.
        :return id: New id of the recovered resource or None if recovery
            failed.
        :return status: True indicates successful recovery, False indicates
            failure.
        """

        # default is recreate if not specified
        if 'operation' not in options or not options['operation']:
            options['operation'] = consts.RECOVER_RECREATE

        operation = options.get('operation')

        if operation.upper() not in consts.RECOVERY_ACTIONS:
            LOG.error("The operation '%s' is not supported",
                      operation)
            return obj.physical_id, False

        op_params = options.get('operation_params', {})
        if operation.upper() == consts.RECOVER_REBOOT:
            # default to hard reboot if operation_params was not specified
            if not isinstance(op_params, dict):
                op_params = {}
            if consts.REBOOT_TYPE not in op_params.keys():
                op_params[consts.REBOOT_TYPE] = consts.REBOOT_HARD

        if operation.upper() == consts.RECOVER_RECREATE:
            # recreate is implemented in base class
            return super(ServerProfile, self).do_recover(obj, **options)
        else:
            method = getattr(self, "handle_" + operation.lower())
            return method(obj, **op_params)

    def handle_reboot(self, obj, **options):
        """Handler for the reboot operation."""
        if not obj.physical_id:
            return None, False

        server_id = obj.physical_id
        reboot_type = options.get(consts.REBOOT_TYPE, consts.REBOOT_SOFT)
        if (not isinstance(reboot_type, str) or
                reboot_type.upper() not in consts.REBOOT_TYPES):
            return server_id, False

        nova_driver = self.compute(obj)
        try:
            server = nova_driver.server_get(server_id)
            if server is None:
                return None, False
            nova_driver.server_reboot(server_id, reboot_type)
            nova_driver.wait_for_server(obj.physical_id,
                                        consts.VS_ACTIVE)
            return server_id, True
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebooting', type='server',
                                         id=server_id,
                                         message=str(ex))

    def handle_rebuild(self, obj, **options):
        """Handler for the rebuild operation.

        :param obj: The node object.
        :param dict options: A list for operations each of which has a name
            and optionally a map from parameter to values.
        :return id: New id of the recovered resource or None if recovery
            failed.
        :return status: True indicates successful recovery, False indicates
            failure.
        """
        if not obj.physical_id:
            return None, False

        server_id = obj.physical_id
        nova_driver = self.compute(obj)
        try:
            server = nova_driver.server_get(server_id)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebuilding', type='server',
                                         id=server_id,
                                         message=str(ex))

        if server is None:
            return None, False
        image_id = options.get(self.IMAGE, None)
        if not image_id:
            image_id = self._get_image_id(obj, server, 'rebuilding')

        admin_pass = self.properties.get(self.ADMIN_PASS)
        name = self.properties[self.NAME] or obj.name
        try:
            nova_driver.server_rebuild(server_id, image_id,
                                       name, admin_pass)
            nova_driver.wait_for_server(server_id, consts.VS_ACTIVE)
            return server_id, True
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebuilding', type='server',
                                         id=server_id,
                                         message=str(ex))

    def handle_change_password(self, obj, **options):
        """Handler for the change_password operation."""
        password = options.get(self.ADMIN_PASSWORD, None)
        if (password is None or not isinstance(password, str)):
            return False
        return self._handle_generic_op(obj, 'server_change_password',
                                       'change_password',
                                       new_password=password)

    def handle_suspend(self, obj):
        """Handler for the suspend operation."""
        return self._handle_generic_op(obj, 'server_suspend',
                                       'suspend', consts.VS_SUSPENDED)

    def handle_resume(self, obj):
        """Handler for the resume operation."""
        return self._handle_generic_op(obj, 'server_resume',
                                       'resume', consts.VS_ACTIVE)

    def handle_start(self, obj):
        """Handler for the start operation."""
        return self._handle_generic_op(obj, 'server_start',
                                       'start', consts.VS_ACTIVE)

    def handle_stop(self, obj):
        """Handler for the stop operation."""
        return self._handle_generic_op(obj, 'server_stop',
                                       'stop', consts.VS_SHUTOFF)

    def handle_lock(self, obj):
        """Handler for the lock operation."""
        return self._handle_generic_op(obj, 'server_lock',
                                       'lock')

    def handle_unlock(self, obj):
        """Handler for the unlock operation."""
        return self._handle_generic_op(obj, 'server_unlock',
                                       'unlock')

    def handle_pause(self, obj):
        """Handler for the pause operation."""
        return self._handle_generic_op(obj, 'server_pause',
                                       'pause', consts.VS_PAUSED)

    def handle_unpause(self, obj):
        """Handler for the unpause operation."""
        return self._handle_generic_op(obj, 'server_unpause',
                                       'unpause', consts.VS_ACTIVE)

    def handle_rescue(self, obj, **options):
        """Handler for the rescue operation."""
        password = options.get(self.ADMIN_PASSWORD, None)
        image = options.get(self.IMAGE, None)
        if not image:
            return False

        self._validate_image(obj, image)
        return self._handle_generic_op(obj, 'server_rescue',
                                       'rescue', consts.VS_RESCUE,
                                       admin_pass=password,
                                       image_ref=image)

    def handle_unrescue(self, obj):
        """Handler for the unrescue operation."""
        return self._handle_generic_op(obj, 'server_unrescue',
                                       'unrescue', consts.VS_ACTIVE)

    def handle_migrate(self, obj):
        """Handler for the migrate operation."""
        return self._handle_generic_op(obj, 'server_migrate',
                                       'migrate', consts.VS_ACTIVE)

    def handle_snapshot(self, obj):
        """Handler for the snapshot operation."""
        return self._handle_generic_op(obj, 'server_create_image',
                                       'snapshot', consts.VS_ACTIVE,
                                       name=obj.name)

    def handle_restore(self, obj, **options):
        """Handler for the restore operation."""
        image = options.get(self.IMAGE, None)
        if not image:
            return False
        return self.handle_rebuild(obj, **options)
