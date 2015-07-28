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

import time

from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

from openstack.compute.v2 import server_metadata

from senlin.common import exception
from senlin.drivers import base
from senlin.drivers.openstack import sdk

LOG = log.getLogger(__name__)


class NovaClient(base.DriverBase):
    '''Nova V2 driver.'''

    def __init__(self, params):
        self.conn = sdk.create_connection(params)
        self.session = self.conn.session

    def flavor_create(self, **params):
        try:
            return self.conn.compute.create_flavor(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_get(self, flavor_id):
        try:
            return self.conn.compute.get_flavor(flavor_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_get_by_name(self, flavor_name):
        try:
            return self.conn.compute.find_flavor(flavor_name)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_list(self, details=False, **query):
        try:
            return self.conn.compute.flavors(details=details, **query)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_update(self, flavor_id, **params):
        try:
            return self.conn.compute.update_flavor(flavor_id, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_delete(self, flavor_id, ignore_missing=True):
        try:
            self.conn.compute.delete_flavor(flavor_id,
                                            ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_create(self, **params):
        raise NotImplemented

    def image_get(self, image_id):
        try:
            return self.conn.compute.get_image(image_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_get_by_name(self, image_name):
        try:
            return self.conn.compute.find_image(image_name)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_list(self, details=False, **query):
        try:
            return self.conn.compute.images(details=details, **query)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_delete(self, image_id, ignore_missing=True):
        try:
            return self.conn.compute.delete_image(
                image_id, ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_create(self, **params):
        try:
            return self.conn.compute.create_keypair(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_get(self, keypair_id):
        try:
            return self.conn.compute.get_keypair(keypair_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_get_by_name(self, keypair_name):
        try:
            return self.conn.compute.find_keypair(keypair_name)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_list(self, details=False, **query):
        try:
            return self.conn.compute.keypairs(details=details, **query)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_update(self, keypair_id, **params):
        try:
            return self.conn.compute.update_keypair(keypair_id, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_delete(self, keypair_id, ignore_missing=True):
        try:
            self.conn.compute.delete_keypair(keypair_id,
                                             ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_create(self, **params):
        timeout = cfg.CONF.default_action_timeout
        if 'timeout' in params:
            timeout = params.pop('timeout')

        server_obj = None
        try:
            server_obj = self.conn.compute.create_server(**params)
        except sdk.exc.HttpException as ex:
            raise ex

        try:
            self.conn.compute.wait_for_server(server_obj, wait=timeout)
        except sdk.exc.ResourceFailure as ex:
            raise exception.ProfileOperationFailed(ex.message)
        except sdk.exc.ResourceTimeout as ex:
            raise exception.ProfileOperationTimeout(ex.message)

        return server_obj

    def server_get(self, server_id):
        try:
            return self.conn.compute.get_server(server_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_list(self, details=False, **query):
        try:
            return self.conn.compute.servers(details=details, **query)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_update(self, server_id, **params):
        try:
            return self.conn.compute.update_server(server_id, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_delete(self, server_id, ignore_missing=True):
        timeout = cfg.CONF.default_action_timeout

        try:
            self.conn.compute.delete_server(server_id,
                                            ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            raise ex

        stopwatch = timeutils.StopWatch(timeout)
        stopwatch.start()
        while not stopwatch.expired():
            try:
                self.server_get(server_id)
            except Exception as ex:
                sdk.ignore_not_found(ex)
                return
            time.sleep(1)

        raise exception.ProfileOperationTimeout(ex.message)

    def server_interface_create(self, **params):
        try:
            return self.conn.compute.create_server_interface(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_get(self, interface_id):
        try:
            return self.conn.compute.get_server_interface(interface_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_list(self):
        try:
            return self.conn.compute.server_interfaces()
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_update(self, interface_id, **params):
        try:
            return self.conn.compute.update_server_interface(interface_id,
                                                             **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_delete(self, interface_id, ignore_missing=True):
        try:
            self.conn.compute.delete_server_interface(
                interface_id, ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_ip_list(self, **params):
        try:
            return self.conn.compute.server_ips()
        except sdk.exc.HttpException as ex:
            raise ex

    def server_metadata_create(self, **params):
        obj = server_metadata.ServerMetadata.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_metadata_get(self, **params):
        obj = server_metadata.ServerMetadata.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_metadata_update(self, **params):
        obj = server_metadata.ServerMetadata.new(**params)
        try:
            return obj.update(self.session)
        except sdk.exc.HttpException as ex:
            raise ex
