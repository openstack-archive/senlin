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

from oslo_log import log as logging
from oslo_utils import encodeutils
import six

from senlin.common import constraints
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.drivers import base as driver_base
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class ServerProfile(base.Profile):
    '''Profile for an OpenStack Nova server.'''

    KEYS = (
        CONTEXT, ADMIN_PASS, AUTO_DISK_CONFIG, AVAILABILITY_ZONE,
        BLOCK_DEVICE_MAPPING, BLOCK_DEVICE_MAPPING_V2,
        CONFIG_DRIVE, FLAVOR, IMAGE, KEY_NAME, METADATA,
        NAME, NETWORKS, PERSONALITY, SECURITY_GROUPS,
        USER_DATA, SCHEDULER_HINTS,
    ) = (
        'context', 'adminPass', 'auto_disk_config', 'availability_zone',
        'block_device_mapping', 'block_device_mapping_v2',
        'config_drive', 'flavor', 'image', 'key_name', 'metadata',
        'name', 'networks', 'personality', 'security_groups',
        'user_data', 'scheduler_hints',
    )

    BDM_KEYS = (
        BDM_DEVICE_NAME, BDM_VOLUME_SIZE,
    ) = (
        'device_name',
        'volume_size',
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
        'port', 'fixed-ip', 'network',
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
        BLOCK_DEVICE_MAPPING: schema.List(
            _('A list specifying the properties of block devices to be used '
              'for this server.'),
            schema=schema.Map(
                _('A map specifying the properties of a block device to be '
                  'used by the server.'),
                schema={
                    BDM_DEVICE_NAME: schema.String(
                        _('Block device name, should be <=255 chars.'),
                    ),
                    BDM_VOLUME_SIZE: schema.Integer(
                        _('Block device size in GB.'),
                    ),
                }
            ),
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
            _('Name of the server.'),
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
        OP_REBOOT, OP_CHANGE_PASSWORD,
    ) = (
        'reboot', 'change_password',
    )

    REBOOT_TYPE = 'type'
    REBOOT_TYPES = (REBOOT_SOFT, REBOOT_HARD) = ('SOFT', 'HARD')
    ADMIN_PASSWORD = 'adminPass'

    OPERATIONS = {
        OP_REBOOT: schema.Operation(
            _("Reboot the nova server."),
            schema={
                REBOOT_TYPE: schema.String(
                    _("Type of reboot which can be 'SOFT' or 'HARD'."),
                    default=REBOOT_SOFT,
                    constraints=[
                        constraints.AllowedValues(REBOOT_TYPES),
                    ]
                )
            }
        ),
        OP_CHANGE_PASSWORD: schema.Operation(
            _("Change the administrator password."),
            schema={
                ADMIN_PASSWORD: schema.String(
                    _("New password for the administrator.")
                )
            }
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(ServerProfile, self).__init__(type_name, name, **kwargs)

        self._novaclient = None
        self._neutronclient = None
        self.server_id = None

    def nova(self, obj):
        '''Construct nova client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        '''

        if self._novaclient is not None:
            return self._novaclient
        params = self._build_conn_params(obj.user, obj.project)
        self._novaclient = driver_base.SenlinDriver().compute(params)
        return self._novaclient

    def neutron(self, obj):
        '''Construct neutron client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        '''

        if self._neutronclient is not None:
            return self._neutronclient
        params = self._build_conn_params(obj.user, obj.project)
        self._neutronclient = driver_base.SenlinDriver().network(params)
        return self._neutronclient

    def do_validate(self, obj):
        """Validate if the spec has provided valid info for server creation.

        :param obj: The node object.
        """
        # validate availability_zone
        az_name = self.properties[self.AVAILABILITY_ZONE]
        if az_name is not None:
            res = self.nova(obj).validate_azs([az_name])
            if not res:
                msg = _("The specified %(key)s '%(value)s' could not be "
                        "found.") % {'key': self.AVAILABILITY_ZONE,
                                     'value': az_name}
                raise exc.InvalidSpec(message=msg)

        # validate flavor
        flavor = self.properties[self.FLAVOR]
        valid_flavors = self.nova(obj).flavor_list()
        found = False
        for f in valid_flavors:
            if not f.is_disabled and (flavor == f.id or flavor == f.name):
                found = True
        if not found:
            msg = _("The specified %(key)s '%(value)s' could not be found."
                    ) % {'key': self.FLAVOR, 'value': flavor}
            raise exc.InvalidSpec(message=msg)

        # validate image
        image = self.properties[self.IMAGE]
        if image is not None:
            valid_images = self.nova(obj).image_list()
            found = False
            for img in valid_images:
                if image == img.id or image == img.name:
                    found = True
            if not found:
                msg = _("The specified %(key)s '%(value)s' could not be "
                        "found.") % {'key': self.IMAGE, 'value': image}
                raise exc.InvalidSpec(message=msg)

        # validate key_name
        keypair = self.properties[self.KEY_NAME]
        if keypair is not None:
            valid_keys = self.nova(obj).keypair_list()
            found = False
            for key in valid_keys:
                if keypair == key.name:
                    found = True
            if not found:
                msg = _("The specified %(key)s '%(value)s' could not be "
                        "found.") % {'key': self.KEY_NAME, 'value': keypair}
                raise exc.InvalidSpec(message=msg)

        # validate bdm conflicts
        bdm = self.properties[self.BLOCK_DEVICE_MAPPING]
        bdmv2 = self.properties[self.BLOCK_DEVICE_MAPPING_V2]
        if all((bdm, bdmv2)):
            msg = _("Only one of '%(key1)s' or '%(key2)s' can be specified, "
                    "not both.") % {'key1': self.BLOCK_DEVICE_MAPPING,
                                    'key2': self.BLOCK_DEVICE_MAPPING_V2}
            raise exc.InvalidSpec(message=msg)

        return True

    def _resolve_bdm(self, bdm):
        for bd in bdm:
            for key in self.BDM2_KEYS:
                if bd[key] is None:
                    del bd[key]
        return bdm

    def _resolve_network(self, networks, client):
        for network in networks:
            net_name_id = network.get(self.NETWORK)
            if net_name_id:
                res = client.network_get(net_name_id)
                network['uuid'] = res.id
                del network[self.NETWORK]
                if network['port'] is None:
                    del network['port']
                if network['fixed-ip'] is None:
                    del network['fixed-ip']
        return networks

    def do_create(self, obj):
        '''Create a server using the given profile.'''
        kwargs = {}
        for key in self.KEYS:
            # context is treated as connection parameters
            if key == self.CONTEXT:
                continue

            if self.properties[key] is not None:
                kwargs[key] = self.properties[key]

        name_or_id = self.properties[self.IMAGE]
        if name_or_id is not None:
            image = self.nova(obj).image_find(name_or_id)
            # wait for new version of openstacksdk to fix this
            kwargs.pop(self.IMAGE)
            kwargs['imageRef'] = image.id

        flavor_id = self.properties[self.FLAVOR]
        flavor = self.nova(obj).flavor_find(flavor_id, False)

        # wait for new verson of openstacksdk to fix this
        kwargs.pop(self.FLAVOR)
        kwargs['flavorRef'] = flavor.id

        name = self.properties[self.NAME]
        if name:
            kwargs['name'] = name
        else:
            kwargs['name'] = obj.name

        metadata = self.properties[self.METADATA] or {}
        metadata['cluster_node_id'] = obj.id
        if obj.cluster_id:
            metadata['cluster_id'] = obj.cluster_id
            metadata['cluster_node_index'] = six.text_type(obj.index)

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
            kwargs['networks'] = self._resolve_network(networks,
                                                       self.neutron(obj))

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

        try:
            server = self.nova(obj).server_create(**kwargs)
            self.nova(obj).wait_for_server(server.id)
            return server.id
        except exc.InternalError as ex:
            raise exc.EResourceCreation(type='server', message=ex.message)

    def do_delete(self, obj, **params):
        """Delete the physical resource associated with the specified node.

        :param obj: The node object to operate on.
        :param kwargs params: Optional keyword arguments for the delete
                              operation.
        :returns: This operation always return True unless exception is
                  caught.
        :raises: `EResourceDeletion` if interaction with nova fails.
        """
        if not obj.physical_id:
            return True

        server_id = obj.physical_id
        ignore_missing = params.get('ignore_missing', True)
        force = params.get('force', False)

        try:
            if force:
                self.nova(obj).server_force_delete(server_id, ignore_missing)
            else:
                self.nova(obj).server_delete(server_id, ignore_missing)
            self.nova(obj).wait_for_server_delete(server_id)
            return True
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='server', id=server_id,
                                        message=six.text_type(ex))

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

        # TODO(Yanyan Hu): Update block_device properties

        # Update basic properties of server
        try:
            self._update_basic_properties(obj, new_profile)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='server', id=self.server_id,
                                      message=ex.message)

        # Update server flavor
        flavor = self.properties[self.FLAVOR]
        new_flavor = new_profile.properties[self.FLAVOR]
        if new_flavor != flavor:
            try:
                self._update_flavor(obj, flavor, new_flavor)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=self.server_id,
                                          message=ex.message)

        # Update server image
        old_passwd = self.properties.get(self.ADMIN_PASS)
        passwd = old_passwd
        if new_profile.properties[self.ADMIN_PASS] is not None:
            passwd = new_profile.properties[self.ADMIN_PASS]
        image = self.properties[self.IMAGE]
        new_image = new_profile.properties[self.IMAGE]
        if new_image != image:
            try:
                self._update_image(obj, image, new_image, passwd)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=self.server_id,
                                          message=ex.message)

        elif old_passwd != passwd:
            # TODO(Jun Xu): update server admin password
            pass

        # Update server network
        networks_current = self.properties[self.NETWORKS]
        networks_create = new_profile.properties[self.NETWORKS]
        networks_delete = copy.deepcopy(networks_current)
        for network in networks_current:
            if network in networks_create:
                networks_create.remove(network)
                networks_delete.remove(network)
        if networks_create or networks_delete:
            # We have network interfaces to be deleted and/or created
            try:
                self._update_network(obj, networks_create, networks_delete)
            except exc.InternalError as ex:
                raise exc.EResourceUpdate(type='server', id=self.server_id,
                                          message=ex.message)
        return True

    def _update_basic_properties(self, obj, new_profile):
        """Updating basic server properties including name, metadata.

        :param obj: The node object to operate on.
        :param new_profile: The new profile that may contain some changes of
                            basic properties for update.
        :returns: None
        :raises: `InternalError` if the nova call fails.
        """
        # Update server metadata
        metadata = self.properties[self.METADATA]
        new_metadata = new_profile.properties[self.METADATA]
        if new_metadata != metadata:
            if new_metadata is None:
                new_metadata = {}
            self.nova(obj).server_metadata_update(self.server_id, new_metadata)

        # Update server name
        name = self.properties[self.NAME]
        new_name = new_profile.properties[self.NAME]
        if new_name != name:
            attrs = {'name': new_name if new_name else obj.name}
            self.nova(obj).server_update(self.server_id, **attrs)

        return

    def _update_flavor(self, obj, old_flavor, new_flavor):
        """Update server flavor.

        :param obj: The node object to operate on.
        :param old_flavor: The identity of the current flavor.
        :param new_flavor: The identity of the new flavor.
        :returns: ``None``.
        :raises: `InternalError` when operation was a failure.
        """
        res = self.nova(obj).flavor_find(old_flavor)
        old_flavor_id = res.id
        res = self.nova(obj).flavor_find(new_flavor)
        new_flavor_id = res.id
        if new_flavor_id == old_flavor_id:
            return

        try:
            self.nova(obj).server_resize(obj.physical_id, new_flavor_id)
            self.nova(obj).wait_for_server(obj.physical_id, 'VERIFY_RESIZE')
        except exc.InternalError:
            try:
                self.nova(obj).server_resize_revert(obj.physical_id)
                self.nova(obj).wait_for_server(obj.physical_id, 'ACTIVE')
            except exc.InternalError:
                raise
            else:
                raise

        try:
            self.nova(obj).server_resize_confirm(obj.physical_id)
            self.nova(obj).wait_for_server(obj.physical_id, 'ACTIVE')
        except exc.InternalError:
            raise

    def _update_image(self, obj, old_image, new_image, admin_password):
        """Update image used by server node.

        :param old: The node object to operate on.
        :param old_image: The identity of the image currently used.
        :param new_image: The identity of the new image to use.
        :param admin_password: The new password for the administrative account
                               if provided.
        :returns: ``None``.
        :raises: ``InternalError`` if operation was a failure.
        """
        if old_image:
            res = self.nova(obj).image_find(old_image)
            image_id = res.id
        else:
            server = self.nova(obj).server_get(obj.physical_id)
            image_id = server.image['id']

        if not new_image:
            # TODO(Yanyan Hu): Allow server update with new_image
            # set to None if Nova service supports it
            message = _("Updating Nova server with image set to None is "
                        "not supported by Nova.")
            raise exc.InternalError(code=500, message=message)

        res = self.nova(obj).image_find(new_image)
        new_image_id = res.id
        if new_image_id != image_id:
            # (Jun Xu): Not update name here if name changed,
            # it should be updated in do_update
            self.nova(obj).server_rebuild(obj.physical_id, new_image_id,
                                          self.properties.get(self.NAME),
                                          admin_password)
            self.nova(obj).wait_for_server(obj.physical_id, 'ACTIVE')

        return

    def _update_network(self, obj, networks_create, networks_delete):
        '''Updating server network interfaces'''

        server = self.nova(obj).server_get(self.server_id)
        ports_existing = list(self.nova(obj).server_interface_list(server))
        ports = []
        for p in ports_existing:
            fixed_ips = []
            for addr in p['fixed_ips']:
                fixed_ips.append(addr['ip_address'])
            ports.append({'port_id': p['port_id'], 'net_id': p['net_id'],
                          'fixed_ips': fixed_ips})

        # Detach some existing ports
        # Step1. Accurately search port with port_id or fixed-ip/net_id
        for n in networks_delete:
            if n['port'] is not None:
                for p in ports:
                    if p['port_id'] == n['port']:
                        ports.remove(p)
                        break
                res = self.nova(obj).server_interface_delete(n['port'],
                                                             server)
            elif n['fixed-ip'] is not None:
                res = self.neutron(obj).network_get(n['network'])
                net_id = res.id
                for p in ports:
                    if (n['fixed-ip'] in p['fixed_ips']) and (
                            p['net_id'] == net_id):
                        res = self.nova(obj).server_interface_delete(
                            p['port_id'], server)
                        ports.remove(p)
                        break

        # Step2. Fuzzy search port with net_id
        for n in networks_delete:
            if n['port'] is None and n['fixed-ip'] is None:
                res = self.neutron(obj).network_get(n['network'])
                net_id = res.id
                for p in ports:
                    if p['net_id'] == net_id:
                        res = self.nova(obj).server_interface_delete(
                            p['port_id'], server)
                        ports.remove(p)
                        break

        # Attach new ports added in new network definition
        for n in networks_create:
            net_name_id = n.get(self.NETWORK, None)
            if net_name_id:
                res = self.neutron(obj).network_get(net_name_id)
                n['net_id'] = res.id
                if n['fixed-ip'] is not None:
                    n['fixed_ips'] = [
                        {'ip_address': n['fixed-ip']}]
            if n['port'] is not None:
                n['port_id'] = n['port']
            del n['network']
            del n['port']
            del n['fixed-ip']
            self.nova(obj).server_interface_create(server, **n)

        return

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

        try:
            server = self.nova(obj).server_get(obj.physical_id)
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

        metadata = self.nova(obj).server_metadata_get(obj.physical_id) or {}
        metadata['cluster_id'] = cluster_id
        metadata['cluster_node_index'] = six.text_type(obj.index)
        self.nova(obj).server_metadata_update(obj.physical_id, metadata)
        return super(ServerProfile, self).do_join(obj, cluster_id)

    def do_leave(self, obj):
        if not obj.physical_id:
            return False

        keys = ['cluster_id', 'cluster_node_index']
        self.nova(obj).server_metadata_delete(obj.physical_id, keys)
        return super(ServerProfile, self).do_leave(obj)

    def do_rebuild(self, obj):
        if not obj.physical_id:
            return False

        self.server_id = obj.physical_id

        try:
            server = self.nova(obj).server_get(self.server_id)
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebuilding', type='server',
                                         id=self.server_id,
                                         message=six.text_type(ex))

        if server is None or server.image is None:
            return False

        image_id = server.image['id']
        admin_pass = self.properties.get(self.ADMIN_PASS)
        try:
            self.nova(obj).server_rebuild(self.server_id, image_id,
                                          self.properties.get(self.NAME),
                                          admin_pass)
            self.nova(obj).wait_for_server(self.server_id, 'ACTIVE')
        except exc.InternalError as ex:
            raise exc.EResourceOperation(op='rebuilding', type='server',
                                         id=self.server_id,
                                         message=six.text_type(ex))
        return True

    def do_check(self, obj):
        if not obj.physical_id:
            return False

        try:
            server = self.nova(obj).server_get(obj.physical_id)
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
        # TODO(Qiming): Handle the case that the operation contains other
        #               alternative recover operation
        # Depends-On: https://review.openstack.org/#/c/359676/
        if operation == 'REBUILD':
            return self.do_rebuild(obj)

        return super(ServerProfile, self).do_recover(obj, **options)

    def handle_reboot(self, obj, **options):
        """Handler for the reboot operation."""
        if not obj.physical_id:
            return False

        reboot_type = options.get(self.REBOOT_TYPE, self.REBOOT_SOFT)
        if (not isinstance(reboot_type, six.string_types) or
                reboot_type not in self.REBOOT_TYPES):
            return False

        self.nova(obj).server_reboot(obj.physical_id, reboot_type)
        self.nova(obj).wait_for_server(obj.physical_id, 'ACTIVE')
        return True

    def handle_change_password(self, obj, **options):
        """Handler for the change_password operation."""
        if not obj.physical_id:
            return False

        password = options.get(self.ADMIN_PASSWORD, None)
        if (password is None or not isinstance(password, six.string_types)):
            return False

        self.nova(obj).server_change_password(obj.physical_id, password)
        return True
