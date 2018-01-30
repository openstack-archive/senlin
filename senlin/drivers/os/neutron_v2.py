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

from oslo_utils import uuidutils

from senlin.drivers import base
from senlin.drivers import sdk


class NeutronClient(base.DriverBase):
    '''Neutron V2 driver.'''

    def __init__(self, params):
        super(NeutronClient, self).__init__(params)
        self.conn = sdk.create_connection(params)

    @sdk.translate_exception
    def network_get(self, name_or_id, ignore_missing=False):
        # There are cases where network have the same names
        # we have to do client side search by ourselves
        if uuidutils.is_uuid_like(name_or_id):
            return self.conn.network.find_network(name_or_id, ignore_missing)

        networks = [n for n in self.conn.network.networks(name=name_or_id)]
        if len(networks) > 0:
            return networks[0]
        return None

    @sdk.translate_exception
    def network_create(self, **attr):
        network = self.conn.network.create_network(**attr)
        return network

    @sdk.translate_exception
    def network_delete(self, network, ignore_missing=False):
        ret = self.conn.network.delete_network(
            network, ignore_missing=ignore_missing)
        return ret

    @sdk.translate_exception
    def port_find(self, name_or_id, ignore_missing=False):
        port = self.conn.network.find_port(name_or_id, ignore_missing)
        return port

    @sdk.translate_exception
    def security_group_find(self, name_or_id, ignore_missing=False):
        sg = self.conn.network.find_security_group(name_or_id, ignore_missing)
        return sg

    @sdk.translate_exception
    def security_group_create(self, name, description=''):
        attr = {
            'name': name,
            'description': description,
        }
        sg = self.conn.network.create_security_group(**attr)
        return sg

    @sdk.translate_exception
    def security_group_delete(self, security_group_id, ignore_missing=False):
        sg = self.conn.network.delete_security_group(
            security_group_id, ignore_missing)
        return sg

    @sdk.translate_exception
    def security_group_rule_create(self, security_group_id, port_range_min,
                                   port_range_max=None, ethertype='IPv4',
                                   remote_ip_prefix='0.0.0.0/0',
                                   direction='ingress', protocol='tcp'):
        if port_range_max is None:
            port_range_max = port_range_min
        attr = {
            'direction': direction,
            'remote_ip_prefix': remote_ip_prefix,
            'protocol': protocol,
            'port_range_max': port_range_max,
            'port_range_min': port_range_min,
            'security_group_id': security_group_id,
            'ethertype': ethertype,
        }
        rule = self.conn.network.create_security_group_rule(**attr)
        return rule

    @sdk.translate_exception
    def subnet_get(self, name_or_id, ignore_missing=False):
        subnet = self.conn.network.find_subnet(name_or_id, ignore_missing)
        return subnet

    @sdk.translate_exception
    def subnet_create(self, **attr):
        subnet = self.conn.network.create_subnet(**attr)
        return subnet

    @sdk.translate_exception
    def router_create(self, **attr):
        router = self.conn.network.create_router(**attr)
        return router

    @sdk.translate_exception
    def router_delete(self, router, ignore_missing=False):
        ret = self.conn.network.delete_router(
            router, ignore_missing=ignore_missing)
        return ret

    @sdk.translate_exception
    def add_interface_to_router(self, router, subnet_id=None, port_id=None):
        interface = self.conn.network.add_interface_to_router(
            router, subnet_id=subnet_id, port_id=port_id)
        return interface

    @sdk.translate_exception
    def remove_interface_from_router(self, router, subnet_id=None,
                                     port_id=None):
        interface = self.conn.network.remove_interface_from_router(
            router, subnet_id=subnet_id, port_id=port_id)
        return interface

    @sdk.translate_exception
    def port_create(self, **attr):
        res = self.conn.network.create_port(**attr)
        return res

    @sdk.translate_exception
    def port_delete(self, port, ignore_missing=True):
        res = self.conn.network.delete_port(
            port=port, ignore_missing=ignore_missing)
        return res

    @sdk.translate_exception
    def port_update(self, port, **attr):
        res = self.conn.network.update_port(port, **attr)
        return res

    @sdk.translate_exception
    def floatingip_find(self, name_or_id, ignore_missing=False):
        res = self.conn.network.find_ip(
            name_or_id, ignore_missing=ignore_missing)
        return res

    @sdk.translate_exception
    def floatingip_list(self, fixed_ip=None,
                        floating_ip=None, floating_network=None,
                        port=None, router=None, status=None):
        filters = {}
        if fixed_ip:
            filters['fixed_ip_address'] = fixed_ip
        if floating_ip:
            filters['floating_ip_address'] = floating_ip
        if floating_network:
            filters['floating_network_id'] = floating_network
        if port:
            filters['port_id'] = port
        if router:
            filters['router_id'] = router
        if status:
            filters['status'] = status
        res = self.conn.network.ips(**filters)
        return list(res)

    @sdk.translate_exception
    def floatingip_create(self, **attr):
        res = self.conn.network.create_ip(**attr)
        return res

    @sdk.translate_exception
    def floatingip_delete(self, floating_ip, ignore_missing=True):
        res = self.conn.network.delete_ip(
            floating_ip, ignore_missing=ignore_missing)
        return res

    @sdk.translate_exception
    def floatingip_update(self, floating_ip, **attr):
        res = self.conn.network.update_ip(floating_ip, **attr)
        return res
