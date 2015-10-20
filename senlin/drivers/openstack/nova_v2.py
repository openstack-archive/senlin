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

from oslo_config import cfg

from openstack.compute.v2 import server_metadata

from senlin.drivers import base
from senlin.drivers.openstack import sdk


class NovaClient(base.DriverBase):
    '''Nova V2 driver.'''

    def __init__(self, params):
        super(NovaClient, self).__init__(params)
        self.conn = sdk.create_connection(params)
        self.session = self.conn.session

    @sdk.translate_exception
    def flavor_create(self, **attrs):
        return self.conn.compute.create_flavor(**attrs)

    @sdk.translate_exception
    def flavor_get(self, value):
        return self.conn.compute.get_flavor(value)

    @sdk.translate_exception
    def flavor_find(self, name_or_id, ignore_missing=False):
        return self.conn.compute.find_flavor(name_or_id, ignore_missing)

    @sdk.translate_exception
    def flavor_list(self, details=True, **query):
        return self.conn.compute.flavors(details, **query)

    @sdk.translate_exception
    def flavor_update(self, value, **attrs):
        return self.conn.compute.update_flavor(value, **attrs)

    @sdk.translate_exception
    def flavor_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_flavor(value, ignore_missing)

    @sdk.translate_exception
    def image_get(self, value):
        return self.conn.compute.get_image(value)

    @sdk.translate_exception
    def image_get_by_name(self, name_or_id, ignore_missing=False):
        return self.conn.compute.find_image(name_or_id, ignore_missing)

    @sdk.translate_exception
    def image_list(self, details=True, **query):
        return self.conn.compute.images(details, **query)

    @sdk.translate_exception
    def image_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_image(value, ignore_missing)

    @sdk.translate_exception
    def keypair_create(self, **attrs):
        return self.conn.compute.create_keypair(**attrs)

    @sdk.translate_exception
    def keypair_get(self, value):
        return self.conn.compute.get_keypair(value)

    @sdk.translate_exception
    def keypair_get_by_name(self, name_or_id, ignore_missing=False):
        return self.conn.compute.find_keypair(name_or_id, ignore_missing)

    @sdk.translate_exception
    def keypair_list(self, **query):
        return self.conn.compute.keypairs(**query)

    @sdk.translate_exception
    def keypair_update(self, value, **attrs):
        return self.conn.compute.update_keypair(value, **attrs)

    @sdk.translate_exception
    def keypair_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_keypair(value, ignore_missing)

    @sdk.translate_exception
    def server_create(self, **attrs):
        server_obj = self.conn.compute.create_server(**attrs)
        return server_obj

    @sdk.translate_exception
    def wait_for_server(self, value, timeout=None):
        '''Wait for server creation complete'''
        if timeout is None:
            timeout = cfg.CONF.default_action_timeout

        self.conn.compute.wait_for_server(value, wait=timeout)
        return

    @sdk.translate_exception
    def server_get(self, value):
        return self.conn.compute.get_server(value)

    @sdk.translate_exception
    def server_list(self, details=True, **query):
        return self.conn.compute.servers(details, **query)

    @sdk.translate_exception
    def server_update(self, value, **attrs):
        return self.conn.compute.update_server(value, **attrs)

    @sdk.translate_exception
    def server_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_server(value, ignore_missing)

    @sdk.translate_exception
    def wait_for_server_delete(self, value, timeout=None):
        '''Wait for server deleting complete'''
        if timeout is None:
            timeout = cfg.CONF.default_action_timeout

        server_obj = self.conn.compute.find_server(value, True)
        if server_obj:
            self.conn.compute.wait_for_delete(server_obj, wait=timeout)

        return

    @sdk.translate_exception
    def server_interface_create(self, **attrs):
        return self.conn.compute.create_server_interface(**attrs)

    @sdk.translate_exception
    def server_interface_get(self, value):
        return self.conn.compute.get_server_interface(value)

    @sdk.translate_exception
    def server_interface_list(self, **query):
        return self.conn.compute.server_interfaces(**query)

    @sdk.translate_exception
    def server_interface_update(self, value, **attrs):
        return self.conn.compute.update_server_interface(value, **attrs)

    @sdk.translate_exception
    def server_interface_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_server_interface(value, ignore_missing)

    @sdk.translate_exception
    def server_ip_list(self, **query):
        return self.conn.compute.server_ips(**query)

    @sdk.translate_exception
    def server_metadata_get(self, **params):
        obj = server_metadata.ServerMetadata.new(**params)
        return obj.get(self.session)

    @sdk.translate_exception
    def server_metadata_update(self, **params):
        obj = server_metadata.ServerMetadata.new(**params)
        return obj.update(self.session)

    @sdk.translate_exception
    def availability_zone_list(self, **query):
        return self.conn.compute.availability_zones(**query)
