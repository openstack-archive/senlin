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

from senlin.common import sdk
from senlin.drivers import base
from senlin.openstack.orchestration.v1 import stack


class HeatClient(base.DriverBase):
    '''Heat V1 driver.'''

    def __init__(self, context):
        conn = sdk.create_connection(context)
        self.session = conn.session
        self.auth = self.session.authenticator

    def stack_create(self, **params):
        obj = stack.Stack.new(**params)
        try:
            return obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_get(self, **params):
        obj = stack.Stack.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_list(self, **params):
        try:
            return stack.Stack.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_update(self, **params):
        obj = stack.Stack.new(**params)
        try:
            return obj.update(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_delete(self, **params):
        obj = stack.Stack.new(**params)
        try:
            obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            raise ex
