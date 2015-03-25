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

from openstack.compute.v2 import flavor
from openstack.compute.v2 import image
from openstack.compute.v2 import keypair
from openstack.compute.v2 import server
from openstack.compute.v2 import server_interface
from openstack.compute.v2 import server_ip
from openstack.compute.v2 import server_meta
from openstack.compute.v2 import server_metadata

from senlin.common import sdk
from senlin.drivers import base


class NovaClient(base.DriverBase):
    '''Nova V2 driver.'''

    def __init__(self, context):
        # TODO(anyone): Need to make the user_preferences work here.
        conn = sdk.create_connection(context)
        self.session = conn.session
        self.auth = self.session.authenticator

    def flavor_create(self, **params):
        obj = flavor.Flavor.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_get(self, **params):
        obj = flavor.Flavor.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_list(self, **params):
        try:
            return flavor.Flavor.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_update(self, **params):
        obj = flavor.Flavor.new(**params)
        try:
            return obj.update(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def flavor_delete(self, **params):
        obj = flavor.Flavor.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            sdk.ignore_not_found(ex)

    def flavor_detail_list(self, **params):
        try:
            return flavor.FlavorDetail.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_create(self, **params):
        raise NotImplemented

    def image_get(self, **params):
        obj = image.Image.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_list(self, **params):
        try:
            return image.Image.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def image_update(self, **params):
        raise NotImplemented

    def image_delete(self, **params):
        obj = image.Image.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            sdk.ignore_not_found(ex)

    def image_detail_list(self, **params):
        try:
            return image.ImageDetail.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_create(self, **params):
        obj = keypair.Keypair.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_get(self, **params):
        obj = keypair.Keypair.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_list(self, **params):
        try:
            return keypair.Keypair.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_update(self, **params):
        obj = keypair.Keypair.new(**params)
        try:
            return obj.update(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def keypair_delete(self, **params):
        obj = keypair.Keypair.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            sdk.ignore_not_found(ex)

    def server_create(self, **params):
        obj = server.Server.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_get(self, **params):
        obj = server.Server.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_list(self, **params):
        try:
            return server.Server.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_update(self, **params):
        obj = server.Server.new(**params)
        try:
            return obj.update(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_delete(self, **params):
        obj = server.Server.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            sdk.ignore_not_found(ex)

    def server_details_list(self, **params):
        try:
            return server.ServerDetail.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_create(self, **params):
        obj = server_interface.ServerInterface.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_get(self, **params):
        obj = server_interface.ServerInterface.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_list(self, **params):
        try:
            return server_interface.ServerInterface.list(self.session,
                                                         **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_interface_update(self, **params):
        raise NotImplemented

    def server_interface_delete(self, **params):
        obj = server_interface.ServerInterface.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            sdk.ignore_not_found(ex)

    def server_ip_list(self, **params):
        try:
            return server_ip.ServerIP.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_meta_create(self, **params):
        obj = server_meta.ServerMeta.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_meta_get(self, **params):
        obj = server_meta.ServerMeta.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_meta_list(self, **params):
        try:
            return server_meta.ServerMeta.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_meta_update(self, **params):
        obj = server_meta.ServerMeta.new(**params)
        try:
            return obj.update(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def server_meta_delete(self, **params):
        obj = server_meta.ServerMeta.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            sdk.ignore_not_found(ex)

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
