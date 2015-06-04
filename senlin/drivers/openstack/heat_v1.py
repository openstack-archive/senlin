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

from senlin.drivers import base
from senlin.drivers.openstack import sdk


class HeatClient(base.DriverBase):
    '''Heat V1 driver.'''

    def __init__(self, context):
        self.conn = sdk.create_connection(context)

    def stack_create(self, **params):
        try:
            return self.conn.orchestration.create_stack(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_get(self, **params):
        try:
            return self.conn.orchestration.get_stack(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_find(self, name_or_id):
        try:
            return self.conn.orchestration.find_stack(name_or_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_list(self, **params):
        try:
            return self.conn.orchestration.list_stacks(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_update(self, **params):
        # NOTE: This still doesn't work because sdk is not supporting
        # stack update yet
        try:
            return self.conn.orchestration.update_stack(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def stack_delete(self, value, ignore_missing=True):
        try:
            return self.conn.orchestration.delete_stack(value,
                                                        ignore_missing)
        except sdk.exc.HttpException as ex:
            raise ex
