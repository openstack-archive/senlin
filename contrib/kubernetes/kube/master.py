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
import six

from kube import base
from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema

LOG = logging.getLogger(__name__)


class ServerProfile(base.KubeBaseProfile):
    """Profile for an kubernetes master server."""

    VERSIONS = {
        '1.0': [
            {'status': consts.EXPERIMENTAL, 'since': '2017.10'}
        ]
    }

    KEYS = (
        CONTEXT, FLAVOR, IMAGE, KEY_NAME,
        PUBLIC_NETWORK,
    ) = (
        'context', 'flavor', 'image', 'key_name',
        'public_network',
    )

    INTERNAL_KEYS = (
        KUBEADM_TOKEN, KUBE_MASTER_IP, SECURITY_GROUP,
        PRIVATE_NETWORK, PRIVATE_SUBNET, PRIVATE_ROUTER,
        KUBE_MASTER_FLOATINGIP, KUBE_MASTER_FLOATINGIP_ID,
        SCALE_OUT_RECV_ID, SCALE_OUT_URL,
    ) = (
        'kubeadm_token', 'kube_master_ip', 'security_group',
        'private_network', 'private_subnet', 'private_router',
        'kube_master_floatingip', 'kube_master_floatingip_id',
        'scale_out_recv_id', 'scale_out_url',
    )

    NETWORK_KEYS = (
        PORT, FIXED_IP, NETWORK, PORT_SECURITY_GROUPS,
        FLOATING_NETWORK, FLOATING_IP,
    ) = (
        'port', 'fixed_ip', 'network', 'security_groups',
        'floating_network', 'floating_ip',
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
        PUBLIC_NETWORK: schema.String(
            _('Public network for kubernetes.'),
            required=True,
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(ServerProfile, self).__init__(type_name, name, **kwargs)
        self.server_id = None

    def do_cluster_create(self, obj):
        self._generate_kubeadm_token(obj)
        self._create_security_group(obj)
        self._create_network(obj)

    def do_cluster_delete(self, obj):
        self._delete_network(obj)
        self._delete_security_group(obj)

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

        jj_vars = {}
        cluster_data = self._get_cluster_data(obj)
        kwargs['networks'] = [{'uuid': cluster_data[self.PRIVATE_NETWORK]}]

        # Get user_data parameters from metadata
        jj_vars['KUBETOKEN'] = cluster_data[self.KUBEADM_TOKEN]
        jj_vars['MASTER_FLOATINGIP'] = cluster_data[
            self.KUBE_MASTER_FLOATINGIP]

        # user_data = self.properties[self.USER_DATA]
        user_data = base.loadScript('./scripts/master.sh')
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

        sgid = self._get_security_group(obj)
        kwargs['security_groups'] = [{'name': sgid}]

        server = None
        resource_id = None
        try:
            server = self.compute(obj).server_create(**kwargs)
            self.compute(obj).wait_for_server(server.id)
            server = self.compute(obj).server_get(server.id)
            self._update_master_ip(obj, server.addresses[''][0]['addr'])
            self._associate_floatingip(obj, server)
            LOG.info("Created master node: %s" % server.id)
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
        internal_ports = obj.data.get('internal_ports', [])
        force = params.get('force', False)

        try:
            self._disassociate_floatingip(obj, server_id)
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
                                        message=six.text_type(ex))
