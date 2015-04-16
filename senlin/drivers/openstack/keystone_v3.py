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

from openstack.identity.v3 import trust
from openstack.identity.v3 import user

from senlin.drivers import base
from senlin.drivers.openstack import sdk


class KeystoneClient(base.DriverBase):
    '''Keystone V3 driver.'''

    def __init__(self, context):
        conn = sdk.create_connection(context)
        self.session = conn.session
        self.auth = self.session.authenticator

    def user_get(self, **params):
        obj = user.User.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def user_list(self, **params):
        try:
            return user.User.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def trust_create(self, **params):
        obj = trust.Trust.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def trust_list(self, **params):
        try:
            return trust.Trust.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def trust_delete(self, **params):
        obj = trust.Trust.new(**params)
        try:
            return obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            raise ex
