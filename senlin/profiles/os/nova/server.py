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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils
import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import schema
from senlin.common import utils
from senlin.drivers import base as driver_base
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class ServerProfile(base.Profile):
    '''Profile for an OpenStack Nova server.'''

    KEYS = (
        CONTEXT, ADMIN_PASS, AUTO_DISK_CONFIG, AVAILABILITY_ZONE,
        BLOCK_DEVICE_MAPPING,  # BLOCK_DEVICE_MAPPING_V2,
        CONFIG_DRIVE, FLAVOR, IMAGE, KEY_NAME, METADATA,
        NAME, NETWORKS, PERSONALITY, SECURITY_GROUPS,
        TIMEOUT, USER_DATA, SCHEDULER_HINTS,
    ) = (
        'context', 'adminPass', 'auto_disk_config', 'availability_zone',
        'block_device_mapping',
        # 'block_device_mapping_v2',
        'config_drive', 'flavor', 'image', 'key_name', 'metadata',
        'name', 'networks', 'personality', 'security_groups',
        'timeout', 'user_data', 'scheduler_hints',
    )

    BDM_KEYS = (
        BDM_DEVICE_NAME, BDM_VOLUME_SIZE,
    ) = (
        'device_name',
        'volume_size',
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
        TIMEOUT: schema.Integer(
            _('Time out threshold for server operations.'),
            default=120,
        ),
        USER_DATA: schema.String(
            _('User data to be exposed by the metadata server.'),
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(ServerProfile, self).__init__(type_name, name, **kwargs)

        self._novaclient = None
        self._neutronclient = None
        self.server_id = None

    def validate(self):
        super(ServerProfile, self).validate()

        if self.properties[self.TIMEOUT] > cfg.CONF.default_action_timeout:
            suggest = cfg.CONF.default_action_timeout
            err = _("Value of the 'timeout' property must be lower than the "
                    "upper limit (%s).") % suggest
            raise exception.InvalidSpec(message=err)

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
        '''Validate if the spec has provided valid info for server creation.'''
        return True

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
            image = self.nova(obj).image_get_by_name(name_or_id)
            # wait for new version of openstacksdk to fix this
            kwargs.pop(self.IMAGE)
            kwargs['imageRef'] = image.id

        flavor_id = self.properties[self.FLAVOR]
        flavor = self.nova(obj).flavor_find(flavor_id, False)

        # wait for new verson of openstacksdk to fix this
        kwargs.pop(self.FLAVOR)
        kwargs['flavorRef'] = flavor.id

        if obj.name is not None:
            kwargs[self.NAME] = obj.name + '-' + utils.random_name(8)

        metadata = self.properties[self.METADATA] or {}
        if obj.cluster_id is not None:
            metadata['cluster'] = obj.cluster_id
        kwargs['metadata'] = metadata

        scheduler_hint = self.properties[self.SCHEDULER_HINTS]
        if scheduler_hint is not None:
            kwargs['scheduler_hints'] = scheduler_hint

        user_data = self.properties[self.USER_DATA]
        if user_data is not None:
            ud = encodeutils.safe_encode(user_data)
            kwargs['user_data'] = encodeutils.safe_decode(base64.b64encode(ud))

        networks = self.properties[self.NETWORKS]
        if networks is not None:
            for network in networks:
                net_name_id = network.get(self.NETWORK)
                if net_name_id:
                    res = self.neutron(obj).network_get(net_name_id)
                    network['uuid'] = res.id
                    del network[self.NETWORK]
                    if network['port'] is None:
                        del network['port']
                    if network['fixed-ip'] is None:
                        del network['fixed-ip']
            kwargs['networks'] = networks

        if 'placement' in obj.data:
            kwargs['availability_zone'] = obj.data['placement']['zone']

        LOG.info('Creating server: %s' % kwargs)
        try:
            server = self.nova(obj).server_create(**kwargs)
            self.nova(obj).wait_for_server(server)
        except Exception as ex:
            LOG.exception(_('Failed in creating server: %s'),
                          six.text_type(ex))
            return False
        self.server_id = server.id

        return server.id

    def do_delete(self, obj):
        self.server_id = obj.physical_id

        if not obj.physical_id:
            return True

        try:
            self.nova(obj).server_delete(self.server_id)
            self.nova(obj).wait_for_server_delete(self.server_id)
        except Exception as ex:
            LOG.error('Error: %s' % six.text_type(ex))
            return False

        return True

    def do_update(self, obj, new_profile, **params):
        '''Perform update on the server.

        :param obj: the server to operate on
        :param new_profile: the new profile for the server.
        :param params: a dictionary of optional parameters.
        '''
        self.server_id = obj.physical_id
        if not self.server_id:
            return True

        # TODO(anyone): Validate the new profile
        # TODO(anyone): Do update based on the fields provided.

        # self.nova(obj).server_update(**fields)
        return True

    def do_check(self, obj):
        # TODO(anyone): Check server status
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

        server = self.nova(obj).server_get(obj.physical_id)
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
        for net in server_data['addresses']:
            network = '%s network' % net
            addresses = []
            for addr in server_data['addresses'][net]:
                addresses.append(addr['addr'])
            if len(addresses) == 0:
                details[network] = ''
            elif len(addresses) == 1:
                details[network] = addresses[0]
            else:
                details[network] = addresses

        # process security groups
        sgroups = []
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
            return {}

        metadata = self.nova(obj).server_metadata_get(
            server_id=obj.physical_id) or {}
        metadata['cluster'] = cluster_id
        return self.nova(obj).server_metadata_update(**metadata)

    def do_leave(self, obj):
        if not obj.physical_id:
            return

        metadata = self.nova(obj).server_metadata_get(
            server_id=obj.physical_id) or {}
        if 'cluster' in metadata:
            del metadata['cluster']
        return self.nova(obj).server_metadata_update(**metadata)
