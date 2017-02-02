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

from oslo_utils import encodeutils
import six

from senlin.common import constraints
from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.objects import node as node_obj
from senlin.profiles import base


class ServerProfile(base.Profile):
    """Profile for an OpenStack Nova server."""

    VERSIONS = {
        '1.0': [
            {'status': consts.SUPPORTED, 'since': '2016.04'}
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
        BDM2_DELETE_ON_TERMINATION,
    ) = (
        'uuid', 'source_type', 'destination_type', 'disk_bus',
        'device_name', 'volume_size', 'guest_format', 'boot_index',
        'device_type', 'delete_on_termination',
    )

    NETWORK_KEYS = (
        PORT, FIXED_IP, NETWORK,
    ) = (
        'port', 'fixed_ip', 'network',
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
                        _('Volume source type, should be image, snapshot, '
                          'volume or blank'),
                        required=True,
                    ),
                    BDM2_DESTINATION_TYPE: schema.String(
                        _('Volume destination type, should be volume or '
                          'local'),
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
              'server created. Both key and value should be <=255 chars.'),
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
                    FIXED_IP: schema.String(
                        _('Fixed IP to be used by the network.'),
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
              'Scheduler hints. Both key and value should be <=255 chars.'),
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
        OP_RESCUE, OP_UNRESCUE, OP_EVACUATE,
    ) = (
        'reboot', 'rebuild', 'change_password', 'pause', 'unpause',
        'suspend', 'resume', 'lock', 'unlock', 'start', 'stop',
        'rescue', 'unrescue', 'evacuate',
    )

    REBOOT_TYPE = 'type'
    REBOOT_TYPES = (REBOOT_SOFT, REBOOT_HARD) = ('SOFT', 'HARD')
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
                REBOOT_TYPE: schema.StringParam(
                    _("Type of reboot which can be 'SOFT' or 'HARD'."),
                    default=REBOOT_SOFT,
                    constraints=[
                        constraints.AllowedValues(REBOOT_TYPES),
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

    def _validate_az(self, obj, az_name, reason=None):
        try:
            res = self.compute(obj).validate_azs([az_name])
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=six.text_type(ex))
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
            msg = six.text_type(ex)
            if reason is None:  # reaons is 'validate'
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
            return self.compute(obj).image_find(name_or_id, False)
        except exc.InternalError as ex:
            if reason == 'create':
                raise exc.EResourceCreation(type='server',
                                            message=six.text_type(ex))
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=six.text_type(ex))
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
                                            message=six.text_type(ex))
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=six.text_type(ex))
            elif ex.code == 404:
                msg = _("The specified %(k)s '%(v)s' could not be found."
                        ) % {'k': self.KEY_NAME, 'v': name_or_id}
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

    def _resolve_bdm(self, bdm):
        for bd in bdm:
            for key in self.BDM2_KEYS:
                if bd[key] is None:
                    del bd[key]
        return bdm

    def _validate_network(self, obj, network, reason=None):
        result = {}
        error = None
        # check network
        net_ident = network.get(self.NETWORK)
        if net_ident:
            try:
                net = self.network(obj).network_get(net_ident)
                if reason == 'update':
                    result['net_id'] = net.id
                else:
                    result['uuid'] = net.id
            except exc.InternalError as ex:
                error = six.text_type(ex)

        # check port
        port_ident = network.get(self.PORT)
        if not error and port_ident:
            try:
                port = self.network(obj).port_find(port_ident)
                if port.status != 'DOWN':
                    error = _("The status of the port %(port)s must be DOWN"
                              ) % {'port': port_ident}

                if reason == 'update':
                    result['port_id'] = port.id
                else:
                    result['port'] = port.id
            except exc.InternalError as ex:
                error = six.text_type(ex)
        elif port_ident is None and net_ident is None:
            error = _("'%(port)s' is required if '%(net)s' is omitted"
                      ) % {'port': self.PORT, 'net': self.NETWORK}

        fixed_ip = network.get(self.FIXED_IP)
        if not error and fixed_ip:
            if port_ident is not None:
                error = _("The '%(port)s' property and the '%(fixed_ip)s' "
                          "property cannot be specified at the same time"
                          ) % {'port': self.PORT, 'fixed_ip': self.FIXED_IP}
            else:
                if reason == 'update':
                    result['fixed_ips'] = [{'ip_address': fixed_ip}]
                else:
                    result['fixed_ip'] = fixed_ip

        if error:
            if reason == 'create':
                raise exc.EResourceCreation(type='server', message=error)
            elif reason == 'update':
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=error)
            else:
                raise exc.InvalidSpec(message=error)

        return result

    def _build_metadata(self, obj, usermeta):
        """Build custom metadata for server.

        :param obj: The node object to operate on.
        :return: A dictionary containing the new metadata.
        """
        metadata = usermeta or {}
        metadata['cluster_node_id'] = obj.id
        if obj.cluster_id:
            metadata['cluster_id'] = obj.cluster_id
            metadata['cluster_node_index'] = six.text_type(obj.index)

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
        kwargs = {}
        for key in self.KEYS:
            # context is treated as connection parameters
            if key == self.CONTEXT:
                continue

            if self.properties[key] is not None:
                kwargs[key] = self.properties[key]

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
                block_device_mapping_v2)

        user_data = self.properties[self.USER_DATA]
        if user_data is not None:
            ud = encodeutils.safe_encode(user_data)
            kwargs['user_data'] = encodeutils.safe_decode(base64.b64encode(ud))

        networks = self.properties[self.NETWORKS]
        if networks is not None:
            kwargs['networks'] = []
            for net_spec in networks:
                net = self._validate_network(obj, net_spec, 'create')
                kwargs['networks'].append(net)

        secgroups = self.properties[self.SECURITY_GROUPS]
        if secgroups:
            kwargs['security_groups'] = [{'name': sg} for sg in secgroups]

        if 'placement' in obj.data:
            if 'zone' in obj.data['placement']:
                kwargs['availability_zone'] = obj.data['placement']['zone']

            if 'servergroup' in obj.data['placement']:
                group_id = obj.data['placement']['servergroup']
                hints = self.properties.get(self.SCHEDULER_HINTS, {})
                hints.update({'group': group_id})
                kwargs['scheduler_hints'] = hints

        server = None
        resource_id = 'UNKNOWN'
        try:
            server = self.compute(obj).server_create(**kwargs)
            self.compute(obj).wait_for_server(server.id)
            # Update zone placement info if available
            self._update_zone_info(obj, server)
            return server.id
        except exc.InternalError as ex:
            if server and server.id:
                resource_id = server.id
            raise exc.EResourceCreation(type='server', message=ex.message,
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
        force = params.get('force', False)

        try:
            driver = self.compute(obj)
            if force:
                driver.server_force_delete(server_id, ignore_missing)
            else:
                driver.server_delete(server_id, ignore_missing)
            driver.wait_for_server_delete(server_id)
            return True
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='server', id=server_id,
                                        message=six.text_type(ex))

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
                                      message=six.text_type(ex))

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
                                      message=six.text_type(ex))

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
                                      message=six.text_type(ex))

    def _update_flavor(self, obj, new_profile):
        """Update server flavor.

        :param obj: The node object to operate on.
        :param old_flavor: The identity of the current flavor.
        :param new_flavor: The identity of the new flavor.
        :returns: ``None``.
        :raises: `EResourceUpdate` when operation was a failure.
        """
        old_flavor = self.properties[self.FLAVOR]
        new_flavor = new_profile.properties[self.FLAVOR]
        cc = self.compute(obj)
        oldflavor = self._validate_flavor(obj, old_flavor, 'update')
        newflavor = self._validate_flavor(obj, new_flavor, 'update')
        if oldflavor.id == newflavor.id:
            return

        try:
            cc.server_resize(obj.physical_id, newflavor.id)
            cc.wait_for_server(obj.physical_id, 'VERIFY_RESIZE')
        except exc.InternalError as ex:
            msg = six.text_type(ex)
            try:
                cc.server_resize_revert(obj.physical_id)
                cc.wait_for_server(obj.physical_id, 'ACTIVE')
            except exc.InternalError as ex1:
                msg = six.text_type(ex1)
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=msg)

        try:
            cc.server_resize_confirm(obj.physical_id)
            cc.wait_for_server(obj.physical_id, 'ACTIVE')
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=six.text_type(ex))

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
        old_image = self.properties[self.IMAGE]
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
        if old_image:
            img_old = self._validate_image(obj, old_image, reason='update')
            old_image_id = img_old.id
        else:
            try:
                server = driver.server_get(obj.physical_id)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                          message=six.text_type(ex))
            # Still, this 'old_image_id' could be empty, but it doesn't matter
            # because the comparison below would fail if that is the case
            old_image_id = server.image.get('id', None)

        if new_image_id == old_image_id:
            return False

        try:
            driver.server_rebuild(obj.physical_id, new_image_id,
                                  new_name, new_password)
            driver.wait_for_server(obj.physical_id, 'ACTIVE')
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=six.text_type(ex))
        return True

    def _create_interfaces(self, obj, networks):
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
                                      message=six.text_type(ex))

        for net_spec in networks:
            net_attrs = self._validate_network(obj, net_spec, 'update')
            if net_attrs:
                try:
                    cc.server_interface_create(server, **net_attrs)
                except exc.InternalError as ex:
                    raise exc.EResourceUpdate(type='server',
                                              id=obj.physical_id,
                                              message=six.text_type(ex))

    def _delete_interfaces(self, obj, networks):
        """Delete existing interfaces from the node.

        :param obj: The node object to operate.
        :param networks: A list containing information about network
                         interfaces to be created.
        :returns: ``None``
        :raises: ``EResourceUpdate``
        """
        def _get_network(nc, net_id, server_id):
            try:
                net = nc.network_get(net_id)
                return net.id
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=server_id,
                                          message=six.text_type(ex))

        def _do_delete(port_id, server_id):
            try:
                cc.server_interface_delete(port_id, server_id)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=server_id,
                                          message=six.text_type(ex))

        cc = self.compute(obj)
        nc = self.network(obj)
        try:
            existing = list(cc.server_interface_list(obj.physical_id))
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=obj.physical_id,
                                      message=six.text_type(ex))

        ports = []
        for intf in existing:
            fixed_ips = [addr['ip_address'] for addr in intf.fixed_ips]
            ports.append({
                'id': intf.port_id,
                'net': intf.net_id,
                'ips': fixed_ips
            })

        for n in networks:
            network = n.get('network', None)
            port = n.get('port', None)
            fixed_ip = n.get('fixed_ip', None)
            if port:
                for p in ports:
                    if p['id'] == port:
                        ports.remove(p)
                        _do_delete(port, obj.physical_id)
            elif fixed_ip:
                net_id = _get_network(nc, network, obj.physical_id)
                for p in ports:
                    if (fixed_ip in p['ips'] and net_id == p['net']):
                        ports.remove(p)
                        _do_delete(p['id'], obj.physical_id)
            elif port is None and fixed_ip is None:
                net_id = _get_network(nc, network, obj.physical_id)
                for p in ports:
                    if p['net'] == net_id:
                        ports.remove(p)
                        _do_delete(p['id'], obj.physical_id)

    def _update_network(self, obj, new_profile):
        """Updating server network interfaces.

        :param obj: The node object to operate.
        :param new_profile: The new profile which may contain new network
                            settings.
        :return: ``None``
        :raises: ``EResourceUpdate`` if there are driver failures.
        """
        networks_current = self.properties[self.NETWORKS]
        networks_create = new_profile.properties[self.NETWORKS]
        networks_delete = copy.deepcopy(networks_current)
        for network in networks_current:
            if network in networks_create:
                networks_create.remove(network)
                networks_delete.remove(network)

        # Detach some existing interfaces
        if networks_delete:
            self._delete_interfaces(obj, networks_delete)

        # Attach new interfaces
        if networks_create:
            self._create_interfaces(obj, networks_create)
        return

    def do_update(self, obj, new_profile=None, **params):
        """Perform update on the server.

        :param obj: the server to operate on
        :param new_profile: the new profile for the server.
        :param params: a dictionary of optional parameters.
        :returns: True if update was successful or False otherwise.
        :raises: `EResourceUpdate` if operation fails.
        """
        self.server_id = obj.physical_id
        if not self.server_id:
            return False

        if not new_profile:
            return False

        if not self.validate_for_update(new_profile):
            return False

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
        self._update_flavor(obj, new_profile)
        self._update_network(obj, new_profile)

        # TODO(Yanyan Hu): Update block_device properties
        # Update server metadata
        self._update_metadata(obj, new_profile)

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
                    'message': six.text_type(ex)
                }
            }

        if server is None:
            return {}
        server_data = server.to_dict()
        details = {
            'image': server_data['image']['id'],
            'flavor': server_data['flavor']['id'],
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
            for sg in server_data['security_groups']:
                sgroups.append(sg['name'])
        if len(sgroups) == 0:
            details['security_groups'] = ''
        elif len(sgroups) == 1:
            details['security_groups'] = sgroups[0]
        else:
            details['security_groups'] = sgroups

        return dict((k, details[k]) for k in sorted(details))

    def do_join(self, obj, cluster_id):
        if not obj.physical_id:
            return False

        driver = self.compute(obj)
        metadata = driver.server_metadata_get(obj.physical_id) or {}
        metadata['cluster_id'] = cluster_id
        metadata['cluster_node_index'] = six.text_type(obj.index)
        driver.server_metadata_update(obj.physical_id, metadata)
        return super(ServerProfile, self).do_join(obj, cluster_id)

    def do_leave(self, obj):
        if not obj.physical_id:
            return False

        keys = ['cluster_id', 'cluster_node_index']
        self.compute(obj).server_metadata_delete(obj.physical_id, keys)
        return super(ServerProfile, self).do_leave(obj)

    def do_check(self, obj):
        if not obj.physical_id:
            return False

        try:
            server = self.compute(obj).server_get(obj.physical_id)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='checking', type='server',
                                         id=obj.physical_id,
                                         message=six.text_type(ex))

        if (server is None or server.status != 'ACTIVE'):
            return False

        return True

    def do_recover(self, obj, **options):
        # NOTE: We do a 'get' not a 'pop' here, because the operations may
        #       get fall back to the base class for handling
        operation = options.get('operation', None)

        if operation and not isinstance(operation, six.string_types):
            operation = operation[0]

        if operation == 'REBUILD':
            return self.handle_rebuild(obj)

        return super(ServerProfile, self).do_recover(obj, **options)

    def handle_reboot(self, obj, **options):
        """Handler for the reboot operation."""
        if not obj.physical_id:
            return False

        reboot_type = options.get(self.REBOOT_TYPE, self.REBOOT_SOFT)
        if (not isinstance(reboot_type, six.string_types) or
                reboot_type not in self.REBOOT_TYPES):
            return False

        self.compute(obj).server_reboot(obj.physical_id, reboot_type)
        self.compute(obj).wait_for_server(obj.physical_id, 'ACTIVE')
        return True

    def handle_rebuild(self, obj, **options):
        if not obj.physical_id:
            return False

        server_id = obj.physical_id
        driver = self.compute(obj)
        try:
            server = driver.server_get(server_id)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebuilding', type='server',
                                         id=server_id,
                                         message=six.text_type(ex))

        if server is None or server.image is None:
            return False

        image_id = server.image['id']
        admin_pass = self.properties.get(self.ADMIN_PASS)
        try:
            driver.server_rebuild(server_id, image_id,
                                  self.properties.get(self.NAME),
                                  admin_pass)
            driver.wait_for_server(server_id, 'ACTIVE')
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebuilding', type='server',
                                         id=server_id,
                                         message=six.text_type(ex))
        return True

    def handle_change_password(self, obj, **options):
        """Handler for the change_password operation."""
        if not obj.physical_id:
            return False

        password = options.get(self.ADMIN_PASSWORD, None)
        if (password is None or not isinstance(password, six.string_types)):
            return False

        self.compute(obj).server_change_password(obj.physical_id, password)
        return True
