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

import mock

from senlin.drivers.openstack import ceilometer_v2
from senlin.drivers.openstack import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestCeilometerV2(base.SenlinTestCase):

    def setUp(self):
        super(TestCeilometerV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.mock_conn = mock.Mock()
        self.mock_create = self.patchobject(
            sdk, 'create_connection',
            return_value=self.mock_conn)

    def test_init(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        self.mock_create.assert_called_once_with(self.conn_params)
        self.assertEqual(self.mock_conn, d.conn)

    def test_alarm_create(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        d.alarm_create(name='test_alarm')
        self.mock_conn.telemetry.create_alarm.assert_called_once_with(
            name='test_alarm')

    def test_alarm_delete(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        d.alarm_delete('foo', True)
        self.mock_conn.telemetry.delete_alarm.assert_called_once_with(
            'foo', True)

        self.mock_conn.telemetry.delete_alarm.reset_mock()

        d.alarm_delete('foo', False)
        self.mock_conn.telemetry.delete_alarm.assert_called_once_with(
            'foo', False)

        self.mock_conn.telemetry.delete_alarm.reset_mock()

        d.alarm_delete('foo')
        self.mock_conn.telemetry.delete_alarm.assert_called_once_with(
            'foo', True)

    def test_alarm_find(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        d.alarm_find('fakeid', True)
        self.mock_conn.telemetry.find_alarm.assert_called_once_with(
            'fakeid', True)

        self.mock_conn.telemetry.find_alarm.reset_mock()

        d.alarm_find('fakeid', False)
        self.mock_conn.telemetry.find_alarm.assert_called_once_with(
            'fakeid', False)

        self.mock_conn.telemetry.find_alarm.reset_mock()

        d.alarm_find('fakeid')
        self.mock_conn.telemetry.find_alarm.assert_called_once_with(
            'fakeid', True)

    def test_alarm_get(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        d.alarm_get('fakeid')
        self.mock_conn.telemetry.get_alarm.assert_called_once_with('fakeid')

    def test_alarm_list(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        d.alarm_list()
        self.mock_conn.telemetry.alarms.assert_called_once_with()

        self.mock_conn.telemetry.alarms.reset_mock()

        d.alarm_list(name='fakename')
        self.mock_conn.telemetry.alarms.assert_called_once_with(
            name='fakename')

    def test_alarm_update(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        attrs = {'enabled': False}
        d.alarm_update('fakeid', **attrs)
        self.mock_conn.telemetry.update_alarm.assert_called_once_with(
            'fakeid', **attrs)

    def test_sample_create(self):
        d = ceilometer_v2.CeilometerClient(self.conn_params)
        attrs = {'foo': 'bar'}
        d.sample_create(**attrs)
        self.mock_conn.telemetry.create_sample.assert_called_once_with(
            foo='bar')
