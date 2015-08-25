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

    def __init__(self, params):
        super(CeilometerClient, self).__init__(params)
        self.conn = sdk.create_connection(params)

    @sdk.translate_exception
    def alarm_create(self, **attrs):
        return self.conn.telemetry.create_alarm(**attrs)

    @sdk.translate_exception
    def alarm_delete(self, value, ignore_missing=True):
        return self.conn.telemetry.delete_alarm(value, ignore_missing)

    @sdk.translate_exception
    def alarm_find(self, name_or_id, ignore_missing=True):
        return self.conn.telemetry.find_alarm(name_or_id, ignore_missing)

    @sdk.translate_exception
    def alarm_get(self, value):
        return self.conn.telemetry.get_alarm(value)

    @sdk.translate_exception
    def alarm_list(self, **query):
        return self.conn.telemetry.alarms(**query)

    @sdk.translate_exception
    def alarm_update(self, value, **attrs):
        return self.conn.telemetry.update_alarm(value, **attrs)

    @sdk.translate_exception
    def sample_create(self, **attrs):
        return self.conn.telemetry.create_sample(**attrs)
