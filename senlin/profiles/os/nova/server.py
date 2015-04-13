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

from senlin.common.i18n import _
from senlin.common import schema
from senlin.drivers.openstack import nova_v2 as novaclient
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class ServerProfile(base.Profile):
    '''Profile for an OpenStack Nova server.'''

    KEYS = (
        ADMIN_PASS, AUTO_DISK_CONFIG, AVAILABILITY_ZONE,
        BLOCK_DEVICE_MAPPING,  # BLOCK_DEVICE_MAPPING_V2,
        CONFIG_DRIVE, FLAVOR, IMAGE, KEY_NAME, METADATA,
        NAME, NETWORKS, PERSONALITY, SECURITY_GROUPS,
        TIMEOUT, USER_DATA,
    ) = (
        'adminPass', 'auto_disk_config', 'availability_zone',
        'block_device_mapping',
        # 'block_device_mapping_v2',
        'config_drive', 'flavor', 'image', 'key_name', 'metadata',
        'name', 'networks', 'personality', 'security_groups',
        'timeout', 'user_data',
    )

    BDM_KEYS = (
        BDM_DEVICE_NAME, BDM_VOLUME_SIZE,
    ) = (
        'device_name',
        'volume_size',
    )

    NETWORK_KEYS = (
        PORT, FIXED_IP,
    ) = (
        'port', 'fixed-ip',
    )

    PERSONALITY_KEYS = (
        PATH, CONTENTS,
    ) = (
        'path', 'contents',
    )

    spec_schema = {
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
        CONFIG_DRIVE: schema.Boolean(
            _('Whether config drive should be enabled for the server.'),
        ),
        FLAVOR: schema.String(
            _('ID of flavor used for the server.'),
            required=True,
        ),
        IMAGE: schema.String(
            # IMAGE is not required, because there could be BDM or BDMv2
            # support and the corresponding settings effective
            _('ID of image to be used for the new server.'),
        ),
        KEY_NAME: schema.String(
            _('Name of Nova keypair to be injected to server.'),
        ),
        METADATA: schema.Map(
            _('A collection of key/value pairs to be associated with the '
              'server created. Both key and value should be <=255 chars.'),
        ),
        NAME: schema.String(
            _('Name of the server.'),
            required=True,
        ),
        NETWORKS: schema.List(
            _('List of networks for the server.'),
            schema=schema.Map(
                _('A map specifying the properties of a network for uses.'),
                schema={
                    PORT: schema.String(
                        _('Port ID to be used by the network.'),
                    ),
                    FIXED_IP: schema.String(
                        _('Port ID to be used by the network.'),
                    ),
                },
            ),
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
        SECURITY_GROUPS: schema.List(
            _('List of security groups.'),
            schema=schema.String(
                _('Name of a security group'),
                required=True,
            ),
        ),
        TIMEOUT: schema.Integer(
            _('Time out threshold for server operations.'),
            default=120,
        ),
        USER_DATA: schema.String(
            _('User data to be exposed by the metadata server.'),
        ),
    }

    def __init__(self, ctx, type_name, name, **kwargs):
        super(ServerProfile, self).__init__(ctx, type_name, name, **kwargs)

        self._nc = None
        self.server_id = None

    def nova(self):
        '''Construct heat client using the combined context.'''

        if self._nc is not None:
            return self._nc

        self._nc = novaclient.NovaClient(self.context)
        return self._nc

    def do_validate(self, obj):
        '''Validate if the spec has provided valid info for server creation.'''

        # TODO(Qiming): timeout must be less than default_action_timeout
        return True

    def do_create(self, obj):
        '''Create a server using the given profile.'''

        kwargs = {}
        for k in self.KEYS:
            if k in self.spec_data:
                if self.spec_data[k] is not None:
                    kwargs[k] = self.spec_data[k]

        if self.IMAGE in self.spec_data:
            image = self.nova().image_get(id=self.spec_data[self.IMAGE])
            kwargs[self.IMAGE] = image

        if self.FLAVOR in self.spec_data:
            flavor = self.nova().flavor_get(id=self.spec_data[self.FLAVOR])
            kwargs[self.FLAVOR] = flavor

        if obj.name is not None:
            kwargs[self.NAME] = obj.name

        LOG.info('Creating server: %s' % kwargs)
        server = self.nova().server_create(**kwargs)
        self.server_id = server.id

        return server.id

    def do_delete(self, obj):
        self.server_id = obj.physical_id

        try:
            self.nova().server_delete(id=self.server_id)
        except Exception as ex:
            raise ex

        return True

    def do_update(self, obj, new_profile):
        '''Perform update on the server.

        :param obj: the server to operate on
        :param new_profile: the new profile for the server.
        '''
        self.server_id = obj.physical_id
        if not self.server_id:
            return True

        # TODO(anyone): Validate the new profile
        # TODO(anyone): Do update based on the fields provided.

        # self.nova().server_update(**fields)
        return True

    def do_check(self, obj):
        # TODO(anyone): Check server status
        return True
