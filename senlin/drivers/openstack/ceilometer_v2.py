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


class CeilometerClient(base.DriverBase):
    '''Ceilometer V2 driver.'''

    def __init__(self, context):
        self.conn = sdk.create_connection(context)

    def alarm_create(self, **params):
        try:
            return self.conn.telemetry.create_alarm(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def alarm_delete(self, value, ignore_not_found=True):
        try:
            return self.conn.telemetry.delete_alarm(value, ignore_not_found)
        except sdk.exc.HttpException as ex:
            raise ex

    def alarm_find(self, name_or_id):
        try:
            return self.conn.telemetry.find(name_or_id)
        except sdk.exc.HttpException as ex:
            raise ex

    def alarm_get(self, **params):
        try:
            return self.conn.telemetry.get_alarm(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def alarm_list(self):
        try:
            return self.conn.telemetry.list_alarms()
        except sdk.exc.HttpException as ex:
            raise ex

    def alarm_update(self, **params):
        try:
            return self.conn.telemetry.update_alarm(**params)
        except sdk.exc.HttpException as ex:
            raise ex

    def sample_create(self, **params):
        try:
            return self.conn.telemetry.create_sample(**params)
        except sdk.exc.HttpException as ex:
            raise ex
