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
import six

from senlin.common import exception as exc
from senlin.drivers import base as driver_base
from senlin.engine import parser
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.triggers.ceilometer import alarm

threshold_alarm = """
  type: FakeTriggerType
  version: 1.0
  time_constraints:
    - start: '10 * * * * *'
      duration: 10
  repeat_actions: True
  rule:
    meter_name: cpu_util
    comparison_operator: lt
    threshold: 15
    period: 120
    evaluation_periods: 2
    statistic: avg
    query:
      - field: resource_metadata.cluster
        op: ==
        value: cluster1
"""


combination_alarm = """
  type: FakeTriggerType
  version: 1.0
  rule:
    operator: and
    alarm_ids:
      - alarm_001
      - alarm_002
"""

resource_alarm = """
  type: FakeTriggerType
  version: 1.0
  rule:
    metric: cpu_util
    comparison_operator: gt
    threshold: 75
    granularity: 61
    evaluation_periods: 3
    aggregation_method: avg
    resource_type: instance
    resource_id: 001-002-0003
"""

agg_metric_alarm = """
  type: FakeTriggerType
  version: 1.0
  rule:
    metrics:
      - disk.io.read.bytes
      - disk.io.write.bytes
    comparison_operator: lt
    threshold: 16384
    granularity: 62
    evaluation_periods: 2
    aggregation_method: avg
"""

agg_resource_alarm = """
  type: FakeTriggerType
  version: 1.0
  rule:
    metric: network.read.packets
    comparison_operator: lt
    threshold: 1024
    granularity: 65
    evaluation_periods: 5
    aggregation_method: avg
    resource_type: instance
    query: project_id==1234
"""


class TestCeilometerAlarm(base.SenlinTestCase):

    def setUp(self):
        super(TestCeilometerAlarm, self).setUp()
        self.ctx = utils.dummy_context()

    def test_init(self):
        spec = parser.simple_parse(threshold_alarm)
        a = alarm.Alarm('A1', spec)

        self.assertIsNotNone(a)
        self.assertEqual('FakeTriggerType', a.type_name)
        self.assertEqual('A1', a.name)
        self.assertEqual(spec, a.spec)

        props = a.alarm_properties
        tc = props[alarm.TIME_CONSTRAINTS][0]
        self.assertEqual('10 * * * * *', tc[alarm.TC_START])
        self.assertEqual(10, tc[alarm.TC_DURATION])
        self.assertIsNone(tc[alarm.TC_NAME])
        self.assertEqual('', tc[alarm.TC_TIMEZONE])

        self.assertTrue(props[alarm.REPEAT])

        # For base Alarm, the rule is ignored and set to None
        self.assertIsNone(a.rule)

    def test_validate_illegal_tc_start(self):
        spec = parser.simple_parse(threshold_alarm)
        spec['time_constraints'][0]['start'] = 'XYZ'
        a = alarm.Alarm('A1', spec)

        ex = self.assertRaises(exc.InvalidSpec, a.validate)
        expected = ("Invalid cron expression specified for property 'start' "
                    "(XYZ): Exactly 5 or 6 columns has to be specified for "
                    "iteratorexpression.")
        self.assertEqual(expected, six.text_type(ex))

    def test_validate_illegal_tc_timezone(self):
        spec = parser.simple_parse(threshold_alarm)
        spec['time_constraints'][0]['timezone'] = 'Moon/Back'
        a = alarm.Alarm('A1', spec)

        ex = self.assertRaises(exc.InvalidSpec, a.validate)
        expected = ("Invalid timezone value specified for property 'timezone' "
                    "(Moon/Back): 'Moon/Back'")
        self.assertEqual(expected, six.text_type(ex))

    def test_validate_no_time_constraints(self):
        spec = parser.simple_parse(threshold_alarm)
        spec.pop('time_constraints')
        a = alarm.Alarm('A1', spec)
        res = a.validate()
        self.assertIsNone(res)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_create(self, mock_senlindriver):
        cc = mock.Mock()
        sd = mock.Mock()
        sd.telemetry.return_value = cc
        mock_senlindriver.return_value = sd

        spec = parser.simple_parse(threshold_alarm)
        params = {
            'alarm_actions': ['http://url1'],
            'ok_actions': ['http://url2'],
            'insufficient_data_actions': ['http://url3']
        }

        a = alarm.ThresholdAlarm('A1', spec)
        res, alarm_dict = a.create(self.ctx, **params)

        self.assertTrue(res)

        sd.telemetry.assert_called_once_with(self.ctx.to_dict())
        values = {
            'name': 'A1',
            'description': '',
            'type': 'threshold',
            'state': 'insufficient_data',
            'severity': 'low',
            'enabled': True,
            'alarm_actions': ['http://url1'],
            'ok_actions': ['http://url2'],
            'insufficient_data_actions': ['http://url3'],
            'time_constraints': [{
                'name': None,
                'description': None,
                'start': '10 * * * * *',
                'duration': 10,
                'timezone': '',
            }],
            'repeat_actions': True,
            'threshold_rule': {
                'meter_name': 'cpu_util',
                'evaluation_periods': 2,
                'period': 120,
                'statistic': 'avg',
                'threshold': 15,
                'query': [{
                    'field': 'resource_metadata.cluster',
                    'value': 'cluster1',
                    'op': '=='}],
                'comparison_operator': 'lt',
            }
        }

        cc.alarm_create.assert_called_once_with(**values)
        self.assertIsNotNone(a.id)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_create_with_failure(self, mock_senlindriver):
        cc = mock.Mock()
        sd = mock.Mock()
        sd.telemetry.return_value = cc
        mock_senlindriver.return_value = sd
        cc.alarm_create.side_effect = exc.ResourceCreationFailure(
            rtype='Alarm')
        spec = parser.simple_parse(threshold_alarm)
        a = alarm.ThresholdAlarm('A1', spec)
        res, reason = a.create(self.ctx)

        self.assertFalse(res)
        self.assertEqual('Failed in creating Alarm.', reason)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_delete(self, mock_senlindriver):
        cc = mock.Mock()
        sd = mock.Mock()
        sd.telemetry.return_value = cc
        mock_senlindriver.return_value = sd
        spec = {
            'type': 'FakeAlarmType',
            'version': 1.0
        }
        a = alarm.Alarm('A1', spec)

        res, res1 = a.delete(self.ctx, 'FAKE_ID')

        self.assertTrue(res)
        sd.telemetry.assert_called_once_with(self.ctx)
        cc.alarm_delete.assert_called_once_with('FAKE_ID', True)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_delete_with_failure(self, mock_senlindriver):
        cc = mock.Mock()
        sd = mock.Mock()
        sd.telemetry.return_value = cc
        mock_senlindriver.return_value = sd
        cc.alarm_delete.side_effect = exc.ResourceDeletionFailure(resource='a')
        spec = {
            'type': 'FakeAlarmType',
            'version': 1.0
        }
        a = alarm.Alarm('A1', spec)

        res, reason = a.delete(self.ctx, 'FAKE_ID')

        self.assertFalse(res)
        self.assertEqual('Failed in deleting a.', reason)
        cc.alarm_delete.assert_called_once_with('FAKE_ID', True)

    def test_update(self):
        spec = {
            'type': 'FakeAlarmType',
            'version': 1.0
        }
        a = alarm.Alarm('A1', spec)
        self.assertEqual(NotImplemented, a.update('id', {}))

    def test_threshold_alarm(self):
        spec = parser.simple_parse(threshold_alarm)
        a = alarm.ThresholdAlarm('A1', spec)

        self.assertIsNotNone(a.rule)
        self.assertEqual('threshold', a.namespace)
        self.assertEqual('cpu_util', a.rule['meter_name'])
        self.assertEqual('lt', a.rule['comparison_operator'])
        self.assertEqual(15, a.rule['threshold'])
        self.assertEqual(120, a.rule['period'])
        self.assertEqual(2, a.rule['evaluation_periods'])
        self.assertEqual('avg', a.rule['statistic'])
        query = [{
            'field': 'resource_metadata.cluster',
            'op': '==',
            'value': 'cluster1'
        }]
        self.assertEqual(query, a.rule['query'])

    def test_combination_alarm(self):
        spec = parser.simple_parse(combination_alarm)
        a = alarm.CombinationAlarm('A1', spec)

        self.assertIsNotNone(a.rule)
        self.assertEqual('combination', a.namespace)
        self.assertEqual('and', a.rule['operator'])
        self.assertIn('alarm_001', a.rule['alarm_ids'])
        self.assertIn('alarm_001', a.rule['alarm_ids'])

    def test_resource_alarm(self):
        spec = parser.simple_parse(resource_alarm)
        a = alarm.ResourceAlarm('A1', spec)

        self.assertIsNotNone(a.rule)
        self.assertEqual('gnocchi_resources_threshold', a.namespace)
        self.assertEqual('cpu_util', a.rule['metric'])
        self.assertEqual('gt', a.rule['comparison_operator'])
        self.assertEqual(75, a.rule['threshold'])
        self.assertEqual(61, a.rule['granularity'])
        self.assertEqual(3, a.rule['evaluation_periods'])
        self.assertEqual('avg', a.rule['aggregation_method'])
        self.assertEqual('instance', a.rule['resource_type'])
        self.assertEqual('001-002-0003', a.rule['resource_id'])

    def test_agg_metric_alarm(self):
        spec = parser.simple_parse(agg_metric_alarm)
        a = alarm.AggregateByMetricsAlarm('A1', spec)

        self.assertIsNotNone(a.rule)
        self.assertEqual('gnocchi_aggregation_by_metrics_threshold',
                         a.namespace)
        self.assertIn('disk.io.read.bytes', a.rule['metrics'])
        self.assertIn('disk.io.write.bytes', a.rule['metrics'])
        self.assertEqual('lt', a.rule['comparison_operator'])
        self.assertEqual(16384, a.rule['threshold'])
        self.assertEqual(62, a.rule['granularity'])
        self.assertEqual(2, a.rule['evaluation_periods'])
        self.assertEqual('avg', a.rule['aggregation_method'])

    def test_agg_resource_alarm(self):
        spec = parser.simple_parse(agg_resource_alarm)
        a = alarm.AggregateByResourcesAlarm('A1', spec)

        self.assertIsNotNone(a.rule)
        self.assertEqual('gnocchi_aggregation_by_resources_threshold',
                         a.namespace)
        self.assertEqual('network.read.packets', a.rule['metric'])
        self.assertEqual('lt', a.rule['comparison_operator'])
        self.assertEqual(1024, a.rule['threshold'])
        self.assertEqual(65, a.rule['granularity'])
        self.assertEqual(5, a.rule['evaluation_periods'])
        self.assertEqual('avg', a.rule['aggregation_method'])
        self.assertEqual('instance', a.rule['resource_type'])
        self.assertEqual('project_id==1234', a.rule['query'])
