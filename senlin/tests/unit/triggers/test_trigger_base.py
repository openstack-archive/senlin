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
from oslo_utils import timeutils
import six

from senlin.common import exception
from senlin.common import schema
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import environment
from senlin.engine import parser
from senlin.tests.unit.common import base as test_base
from senlin.tests.unit.common import utils
from senlin.triggers import base

sample_trigger = """
  type: FakeTriggerType
  version: 1.0
  rule:
    key1: value1
    key2: 2
"""


class FakeTriggerImpl(base.Trigger):
    rule_schema = {}

    def __init__(self, name, spec, **kwargs):
        super(FakeTriggerImpl, self).__init__(name, spec, **kwargs)
        self.rule = schema.Spec(self.rule_schema, spec['rule'])


class TestTriggerBase(test_base.SenlinTestCase):

    def setUp(self):

        super(TestTriggerBase, self).setUp()
        self.ctx = utils.dummy_context()
        environment.global_env().register_trigger('FakeTriggerType',
                                                  FakeTriggerImpl)

    def test_init(self):
        spec = parser.simple_parse(sample_trigger)
        trigger = base.Trigger('t1', spec)

        self.assertIsNone(trigger.id)
        self.assertIsNone(trigger.physical_id)
        self.assertEqual('', trigger.desc)
        self.assertEqual(base.INSUFFICIENT_DATA, trigger.state)
        self.assertTrue(trigger.enabled)
        self.assertEqual(base.S_LOW, trigger.severity)
        self.assertEqual({}, trigger.links)
        self.assertIsNone(trigger.created_time)
        self.assertIsNone(trigger.updated_time)
        self.assertIsNone(trigger.deleted_time)
        self.assertEqual(spec, trigger.spec)

        spec_data = trigger.spec_data
        self.assertEqual('FakeTriggerType', spec_data['type'])
        self.assertEqual('1.0', spec_data['version'])
        self.assertEqual({'key1': 'value1', 'key2': 2},
                         spec_data['rule'])

    def _create_db_trigger(self, trigger_id=None, **custom_values):

        values = {
            'id': trigger_id,
            'name': 'test-trigger',
            'type': 'FakeTriggerType',
            'desc': 'blah blah',
            'state': base.INSUFFICIENT_DATA,
            'enabled': True,
            'severity': base.S_CRITICAL,
            'links': {
                'alarm_actions': ['http://url1']
            },
            'spec': parser.simple_parse(sample_trigger),
            'user': self.ctx.user,
            'project': self.ctx.project,
            'domain': self.ctx.domain
        }
        values.update(custom_values)

        return db_api.trigger_create(self.ctx, values)

    def test_load(self):
        timestamp = timeutils.utcnow()
        spec = parser.simple_parse(sample_trigger)
        db_trigger = self._create_db_trigger('FAKE_ID',
                                             created_time=timestamp,
                                             updated_time=timestamp)

        self.assertIsNotNone(db_trigger)
        res = base.Trigger.load(self.ctx, trigger_id=db_trigger.id)

        self.assertIsInstance(res, base.Trigger)
        self.assertEqual('FAKE_ID', res.id)
        self.assertEqual('test-trigger', res.name)
        self.assertEqual('FakeTriggerType', res.type_name)
        self.assertEqual('blah blah', res.desc)
        self.assertEqual(base.INSUFFICIENT_DATA, res.state)
        self.assertTrue(res.enabled)
        self.assertEqual(base.S_CRITICAL, res.severity)
        self.assertEqual({'alarm_actions': ['http://url1']}, res.links)
        self.assertEqual(timestamp, res.created_time)
        self.assertEqual(timestamp, res.updated_time)
        self.assertIsNone(res.deleted_time)

        self.assertEqual(spec, res.spec)
        self.assertEqual(spec['type'], res.spec_data['type'])
        self.assertEqual(str(spec['version']), res.spec_data['version'])
        self.assertEqual(spec['rule'], res.spec_data['rule'])

        # load trigger via db trigger object
        res = base.Trigger.load(self.ctx, db_trigger=db_trigger)
        self.assertIsInstance(res, base.Trigger)
        self.assertEqual('FAKE_ID', res.id)

    def test_load_not_found(self):
        ex = self.assertRaises(exception.TriggerNotFound,
                               base.Trigger.load,
                               self.ctx, trigger_id='Bogus')
        self.assertEqual('The trigger (Bogus) could not be found.',
                         six.text_type(ex))

    def test_load_all(self):
        self._create_db_trigger('ID_1')
        self._create_db_trigger('ID_2')

        res = base.Trigger.load_all(self.ctx)
        ids = [t.id for t in res]
        self.assertEqual(2, len(ids))
        self.assertIn('ID_1', ids)
        self.assertIn('ID_2', ids)

    @mock.patch.object(db_api, 'trigger_get_all')
    def test_load_all_with_params(self, mock_get):
        mock_get.return_value = []

        # have to do a conversion here due to the generators used
        res = list(base.Trigger.load_all(self.ctx))
        self.assertEqual([], res)
        mock_get.assert_called_once_with(self.ctx, limit=None, marker=None,
                                         sort_keys=None, sort_dir=None,
                                         filters=None, project_safe=True,
                                         show_deleted=False)

        mock_get.reset_mock()

        res = list(base.Trigger.load_all(self.ctx, limit=1, marker='MARKER',
                                         sort_keys=['K1'], sort_dir='asc',
                                         filters={'enabled': True},
                                         show_deleted=False))
        self.assertEqual([], res)
        mock_get.assert_called_once_with(self.ctx, limit=1, marker='MARKER',
                                         sort_keys=['K1'], sort_dir='asc',
                                         filters={'enabled': True},
                                         project_safe=True,
                                         show_deleted=False)

    def test_delete(self):
        self._create_db_trigger('ID_1')
        res = base.Trigger.delete(self.ctx, 'ID_1')
        self.assertIsNone(res)

    def test_store_for_create(self):
        spec = parser.simple_parse(sample_trigger)
        trigger = base.Trigger('t1', spec)
        trigger_id = trigger.store(self.ctx)

        res = base.Trigger.load(self.ctx, trigger_id)
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.id)
        self.assertIsNotNone(res.created_time)
        self.assertIsNone(res.updated_time)
        self.assertIsNone(res.deleted_time)

    def test_store_for_update(self):
        spec = parser.simple_parse(sample_trigger)
        trigger = base.Trigger('t1', spec)
        trigger_id = trigger.store(self.ctx)
        trigger.name = 'new-name'
        trigger.desc = 'new desc'
        trigger.enabled = False
        new_trigger_id = trigger.store(self.ctx)

        self.assertEqual(trigger_id, new_trigger_id)

        res = base.Trigger.load(self.ctx, trigger_id)
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.id)
        self.assertIsNotNone(res.created_time)
        self.assertIsNotNone(res.updated_time)
        self.assertIsNone(res.deleted_time)
        self.assertEqual('new-name', res.name)
        self.assertEqual('new desc', res.desc)
        self.assertFalse(res.enabled)

    @mock.patch.object(schema.Spec, 'validate')
    def test_validate(self, mock_validate):
        spec = parser.simple_parse(sample_trigger)
        trigger = base.Trigger('t1', spec)
        trigger.validate()

        mock_validate.assert_has_calls([mock.call(), mock.call()])

    def test_get_schema(self):
        expected = {
            'rule': {
                'description': u'Rule collection for the trigger.',
                'readonly': False,
                'required': True,
                'type': 'Map'
            },
            'type': {
                'description': u'Type name of the trigger type.',
                'readonly': False,
                'required': True,
                'type': 'String'
            },
            'version': {
                'description': u'Version number string of the trigger type.',
                'readonly': False,
                'required': True,
                'type': 'String'
            }
        }

        res = base.Trigger.get_schema()
        self.assertEqual(expected, res)

    def test_to_dict(self):
        spec = parser.simple_parse(sample_trigger)
        trigger = base.Trigger('t1', spec, id='FAKE_ID', desc='DESC',
                               user=self.ctx.user, project=self.ctx.project,
                               domain=self.ctx.domain)

        expected = {
            'id': 'FAKE_ID',
            'name': 't1',
            'type': 'FakeTriggerType',
            'desc': 'DESC',
            'state': base.INSUFFICIENT_DATA,
            'enabled': True,
            'severity': base.S_LOW,
            'links': {},
            'spec': spec,
            'user': self.ctx.user,
            'project': self.ctx.project,
            'domain': self.ctx.domain,
            'created_time': None,
            'updated_time': None,
            'deleted_time': None
        }

        res = trigger.to_dict()

        self.assertEqual(expected, res)
