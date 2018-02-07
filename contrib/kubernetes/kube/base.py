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

import os
import random
import string

from oslo_log import log as logging
import six

from senlin.common import context
from senlin.common import exception as exc
from senlin.objects import cluster as cluster_obj
from senlin.profiles.os.nova import server

LOG = logging.getLogger(__name__)


def GenKubeToken():
    token_id = ''.join([random.choice(
        string.digits + string.ascii_lowercase) for i in range(6)])
    token_secret = ''.join([random.choice(
        string.digits + string.ascii_lowercase) for i in range(16)])
    token = '.'.join(token_id, token_secret)
    return token


def loadScript(path):
    script_file = os.path.join(os.path.dirname(__file__), path)
    with open(script_file, "r") as f:
        content = f.read()
    return content


class KubeBaseProfile(server.ServerProfile):
    """Kubernetes Base Profile."""

    def __init__(self, type_name, name, **kwargs):
        super(KubeBaseProfile, self).__init__(type_name, name, **kwargs)
        self.server_id = None

    def _generate_kubeadm_token(self, obj):
        token = GenKubeToken()
        # store generated token

        ctx = context.get_service_context(user=obj.user, project=obj.project)
        data = obj.data
        data[self.KUBEADM_TOKEN] = token
        cluster_obj.Cluster.update(ctx, obj.id, {'data': data})
        return token

    def _get_kubeadm_token(self, obj):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            return cluster.data.get(self.KUBEADM_TOKEN)
        return None

    def _update_master_ip(self, obj, ip):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            cluster.data['kube_master_ip'] = ip
            cluster.update(ctx, obj.cluster_id, {'data': cluster.data})

    def _create_network(self, obj):
        client = self.network(obj)
        net = client.network_create()
        subnet = client.subnet_create(network_id=net.id, cidr='10.7.0.0/24',
                                      ip_version=4)
        pub_net = client.network_get(self.properties[self.PUBLIC_NETWORK])
        router = client.router_create(
            external_gateway_info={"network_id": pub_net.id})
        client.add_interface_to_router(router, subnet_id=subnet.id)
        fip = client.floatingip_create(floating_network_id=pub_net.id)

        ctx = context.get_service_context(user=obj.user, project=obj.project)
        data = obj.data
        data[self.PRIVATE_NETWORK] = net.id
        data[self.PRIVATE_SUBNET] = subnet.id
        data[self.PRIVATE_ROUTER] = router.id
        data[self.KUBE_MASTER_FLOATINGIP] = fip.floating_ip_address
        data[self.KUBE_MASTER_FLOATINGIP_ID] = fip.id

        cluster_obj.Cluster.update(ctx, obj.id, {'data': data})

        return net.id

    def _delete_network(self, obj):
        client = self.network(obj)
        fip_id = obj.data.get(self.KUBE_MASTER_FLOATINGIP_ID)
        client.floatingip_delete(fip_id)

        router = obj.data.get(self.PRIVATE_ROUTER)
        subnet = obj.data.get(self.PRIVATE_SUBNET)
        client.remove_interface_from_router(router, subnet_id=subnet)

        # delete router and network
        client.router_delete(router, ignore_missing=True)
        net = obj.data.get(self.PRIVATE_NETWORK)
        client.network_delete(net, ignore_missing=True)

    def _associate_floatingip(self, obj, server):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            fip = cluster.data.get(self.KUBE_MASTER_FLOATINGIP)
            self.compute(obj).server_floatingip_associate(server, fip)

    def _disassociate_floatingip(self, obj, server):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            fip = cluster.data.get(self.KUBE_MASTER_FLOATINGIP)
            try:
                self.compute(obj).server_floatingip_disassociate(server, fip)
            except Exception:
                pass

    def _get_cluster_data(self, obj):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            return cluster.data
        return {}

    def _get_network(self, obj):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            return cluster.data.get(self.PRIVATE_NETWORK)
        return None

    def _create_security_group(self, obj):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        sgid = obj.data.get(self.SECURITY_GROUP, None)
        if sgid:
            return sgid

        client = self.network(obj)
        try:
            sg = client.security_group_create(name=self.name)
        except Exception as ex:
            raise exc.EResourceCreation(type='kubernetes.master',
                                        message=six.text_type(ex))
        data = obj.data
        data[self.SECURITY_GROUP] = sg.id
        cluster_obj.Cluster.update(ctx, obj.id, {'data': data})
        self._set_security_group_rules(obj, sg.id)

        return sg.id

    def _get_security_group(self, obj):
        ctx = context.get_service_context(user=obj.user, project=obj.project)
        if obj.cluster_id:
            cluster = cluster_obj.Cluster.get(ctx, obj.cluster_id)
            return cluster.data.get(self.SECURITY_GROUP)
        return None

    def _set_security_group_rules(self, obj, sgid):
        client = self.network(obj)
        open_ports = {
            'tcp': [22, 80, 8000, 8080, 6443, 8001, 8443, 443,
                    179, 8082, 8086],
            'udp': [8285, 8472],
            'icmp': [None]
        }
        for p in open_ports.keys():
            for port in open_ports[p]:
                try:
                    client.security_group_rule_create(sgid, port, protocol=p)
                except Exception as ex:
                    raise exc.EResourceCreation(type='kubernetes.master',
                                                message=six.text_type(ex))

    def _delete_security_group(self, obj):
        sgid = obj.data.get(self.SECURITY_GROUP)
        if sgid:
            self.network(obj).security_group_delete(sgid, ignore_missing=True)

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
