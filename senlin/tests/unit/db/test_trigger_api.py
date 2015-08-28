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

from oslo_utils import timeutils

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


sample_trigger = '''
  type: CeilometerThresholdAlarm
  version: 1.0

  time_constraints:
    start: '10 * * * * *'
    duration: 5
    timezone: 'Asia/Shanghai'

  rule:
    meter_name: cpu_util
    comparison_operator: lt
    threshold: 15
    period: 60
    evaluation_periods: 1
    repeat_actions: True
    statistic: avg
'''


class DBAPITriggerTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPITriggerTest, self).setUp()
        self.ctx = utils.dummy_context()

    def _create_trigger(self, ctx, **kwargs):
        spec = parser.simple_parse(sample_trigger)
        data = {}
        data['id'] = None
        data['desc'] = 'a description'
        data['name'] = 'test_trigger'
        data['physical_id'] = None
        data['enabled'] = True
        data['state'] = 'ok'
        data['severity'] = 'low'
        data['links'] = {}
        data['type'] = spec['type']
        data['spec'] = spec
        data['user'] = ctx.user
        data['project'] = ctx.project
        data['domain'] = ctx.domain
        data.update(kwargs)

        return db_api.trigger_create(ctx, data)

    def test_trigger_create(self):
        trigger = self._create_trigger(self.ctx)
        self.assertIsNotNone(trigger.id)
        self.assertEqual('test_trigger', trigger.name)
        self.assertEqual('CeilometerThresholdAlarm', trigger.type)
        self.assertEqual('a description', trigger.desc)
        self.assertEqual('ok', trigger.state)
        self.assertTrue(trigger.enabled)
        self.assertEqual('low', trigger.severity)
        self.assertEqual({}, trigger.links)
        self.assertEqual(1.0, trigger.spec['version'])

    def test_trigger_get(self):
        trigger = self._create_trigger(self.ctx)
        retobj = db_api.trigger_get(self.ctx, trigger.id)
        self.assertEqual(trigger.id, retobj.id)
        self.assertEqual(trigger.spec, retobj.spec)

    def test_trigger_get_not_found(self):
        trigger = db_api.trigger_get(self.ctx, 'BOGUS_ID')
        self.assertIsNone(trigger)

    def test_trigger_get_show_deleted(self):
        trigger_id = self._create_trigger(self.ctx).id

        # check created
        trigger = db_api.trigger_get(self.ctx, trigger_id)
        self.assertIsNotNone(trigger)

        # Now, delete it
        db_api.trigger_delete(self.ctx, trigger_id)

        # default equivalent to false
        trigger = db_api.trigger_get(self.ctx, trigger_id)
        self.assertIsNone(trigger)

        # explicit false
        trigger = db_api.trigger_get(self.ctx, trigger_id, show_deleted=False)
        self.assertIsNone(trigger)

        # explicit true
        trigger = db_api.trigger_get(self.ctx, trigger_id, show_deleted=True)
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger_id, trigger.id)

    def test_trigger_get_by_name(self):
        trigger_name = 'my_best_trigger'

        # before creation
        trigger = db_api.trigger_get_by_name(self.ctx, trigger_name)
        self.assertIsNone(trigger)

        trigger = self._create_trigger(self.ctx, name=trigger_name)

        # after creation
        retobj = db_api.trigger_get_by_name(self.ctx, trigger_name)
        self.assertIsNotNone(retobj)
        self.assertEqual(trigger_name, retobj.name)

        # bad name
        retobj = db_api.trigger_get_by_name(self.ctx, 'non-exist')
        self.assertIsNone(retobj)

    def test_trigger_get_by_name_show_deleted(self):
        trigger_name = 'my_best_trigger'

        trigger_id = self._create_trigger(self.ctx, name=trigger_name).id

        db_api.trigger_delete(self.ctx, trigger_id)

        # default case
        trigger = db_api.trigger_get_by_name(self.ctx, trigger_name)
        self.assertIsNone(trigger)

        # explicit false
        trigger = db_api.trigger_get_by_name(self.ctx, trigger_name,
                                             show_deleted=False)
        self.assertIsNone(trigger)

        # explicit true
        trigger = db_api.trigger_get_by_name(self.ctx, trigger_name,
                                             show_deleted=True)
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger_id, trigger.id)

    def test_trigger_get_by_short_id(self):
        trigger_ids = ['same-part-unique-part',
                       'same-part-part-unique']

        for pid in trigger_ids:
            self._create_trigger(self.ctx, id=pid)

            # verify creation with set ID
            trigger = db_api.trigger_get(self.ctx, pid)
            self.assertIsNotNone(trigger)
            self.assertEqual(pid, trigger.id)

        # too short -> multiple choices
        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.trigger_get_by_short_id,
                              self.ctx, trigger_ids[0][:x])

        # ids are unique
        trigger = db_api.trigger_get_by_short_id(self.ctx, trigger_ids[0][:11])
        self.assertEqual(trigger_ids[0], trigger.id)
        trigger = db_api.trigger_get_by_short_id(self.ctx, trigger_ids[1][:11])
        self.assertEqual(trigger_ids[1], trigger.id)

        # bad ids
        res = db_api.trigger_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_trigger_get_all(self):
        ids = ['trigger1', 'trigger2']

        for pid in ids:
            self._create_trigger(self.ctx, id=pid)

        triggers = db_api.trigger_get_all(self.ctx)
        self.assertEqual(2, len(triggers))
        trigger_ids = [p.id for p in triggers]
        for pid in ids:
            self.assertIn(pid, trigger_ids)

        # test show_deleted here
        db_api.trigger_delete(self.ctx, triggers[1].id)

        # after delete one of them
        triggers = db_api.trigger_get_all(self.ctx)
        self.assertEqual(1, len(triggers))

        triggers = db_api.trigger_get_all(self.ctx, show_deleted=False)
        self.assertEqual(1, len(triggers))

        triggers = db_api.trigger_get_all(self.ctx, show_deleted=True)
        self.assertEqual(2, len(triggers))

        # after delete both triggers
        db_api.trigger_delete(self.ctx, triggers[0].id)

        triggers = db_api.trigger_get_all(self.ctx)
        self.assertEqual(0, len(triggers))
        triggers = db_api.trigger_get_all(self.ctx, show_deleted=True)
        self.assertEqual(2, len(triggers))

    def test_trigger_get_all_project_safe(self):
        self._create_trigger(self.ctx, id='ID1', project='P1')
        triggers = db_api.trigger_get_all(self.ctx)
        self.assertEqual(0, len(triggers))
        triggers = db_api.trigger_get_all(self.ctx, project_safe=True)
        self.assertEqual(0, len(triggers))
        triggers = db_api.trigger_get_all(self.ctx, project_safe=False)
        self.assertEqual(1, len(triggers))

        self.ctx.project = 'P1'
        triggers = db_api.trigger_get_all(self.ctx)
        self.assertEqual(1, len(triggers))
        triggers = db_api.trigger_get_all(self.ctx, project_safe=True)
        self.assertEqual(1, len(triggers))
        triggers = db_api.trigger_get_all(self.ctx, project_safe=False)
        self.assertEqual(1, len(triggers))

    def test_trigger_get_all_with_limit_marker(self):
        ids = ['trigger1', 'trigger2', 'trigger3']
        for pid in ids:
            timestamp = timeutils.utcnow()
            self._create_trigger(self.ctx, id=pid, created_time=timestamp)

        # different limit settings
        triggers = db_api.trigger_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(triggers))

        triggers = db_api.trigger_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(triggers))

        # a large limit
        triggers = db_api.trigger_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(triggers))

        # use marker here
        triggers = db_api.trigger_get_all(self.ctx, marker='trigger1')
        self.assertEqual(2, len(triggers))

        triggers = db_api.trigger_get_all(self.ctx, marker='trigger2')
        self.assertEqual(1, len(triggers))

        triggers = db_api.trigger_get_all(self.ctx, marker='trigger3')
        self.assertEqual(0, len(triggers))

        triggers = db_api.trigger_get_all(self.ctx, limit=1, marker='trigger1')
        self.assertEqual(1, len(triggers))

    def test_trigger_get_all_used_sort_keys(self):
        ids = ['trigger1', 'trigger2', 'trigger3']
        for pid in ids:
            self._create_trigger(self.ctx, id=pid)

        mock_paginate = self.patchobject(db_api.utils, 'paginate_query')
        sort_keys = ['created_time', 'id', 'name', 'type', 'updated_time']

        db_api.trigger_get_all(self.ctx, sort_keys=sort_keys)

        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        expected_keys = set(['id', 'type', 'name', 'created_time',
                             'updated_time'])
        self.assertEqual(expected_keys, used_sort_keys)

    def test_trigger_get_all_sort_keys_wont_change(self):
        sort_keys = ['id']
        db_api.trigger_get_all(self.ctx, sort_keys=sort_keys)
        self.assertEqual(['id'], sort_keys)

    def test_trigger_get_all_sort_keys_and_dir(self):
        values = [{'id': '001', 'name': 'trigger1', 'type': 'C'},
                  {'id': '002', 'name': 'trigger3', 'type': 'B'},
                  {'id': '003', 'name': 'trigger2', 'type': 'A'}]

        for v in values:
            self._create_trigger(self.ctx, **v)

        triggers = db_api.trigger_get_all(self.ctx, sort_keys=['name', 'type'],
                                          sort_dir='asc')
        self.assertEqual(3, len(triggers))
        # Sorted by name
        self.assertEqual('001', triggers[0].id)
        self.assertEqual('003', triggers[1].id)
        self.assertEqual('002', triggers[2].id)

        triggers = db_api.trigger_get_all(self.ctx, sort_keys=['type', 'name'],
                                          sort_dir='asc')
        self.assertEqual(3, len(triggers))
        # Sorted by levels (ascending)
        self.assertEqual('003', triggers[0].id)
        self.assertEqual('002', triggers[1].id)
        self.assertEqual('001', triggers[2].id)

        triggers = db_api.trigger_get_all(self.ctx, sort_keys=['type', 'name'],
                                          sort_dir='desc')
        self.assertEqual(3, len(triggers))
        # Sorted by statuses (descending)
        self.assertEqual('001', triggers[0].id)
        self.assertEqual('002', triggers[1].id)
        self.assertEqual('003', triggers[2].id)

    def test_trigger_get_all_default_sort_dir(self):
        triggers = []
        for x in range(3):
            trigger = self._create_trigger(self.ctx,
                                           created_time=timeutils.utcnow())
            triggers.append(trigger)

        results = db_api.trigger_get_all(self.ctx, sort_dir='asc')
        self.assertEqual(3, len(results))
        self.assertEqual(triggers[0].id, results[0].id)
        self.assertEqual(triggers[1].id, results[1].id)
        self.assertEqual(triggers[2].id, results[2].id)

    def test_trigger_get_all_with_filters(self):
        for name in ['trigger1', 'trigger2']:
            self._create_trigger(self.ctx, name=name)

        filters = {'name': ['trigger1', 'triggerx']}
        results = db_api.trigger_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('trigger1', results[0]['name'])

        filters = {'name': 'trigger1'}
        results = db_api.trigger_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('trigger1', results[0]['name'])

    def test_trigger_get_all_with_empty_filters(self):
        for name in ['trigger1', 'trigger2']:
            self._create_trigger(self.ctx, name=name)

        filters = None
        results = db_api.trigger_get_all(self.ctx, filters=filters)
        self.assertEqual(2, len(results))

    def test_trigger_update(self):
        new_fields = {
            'name': 'new_trigger',
            'type': 'CeilometerThresholdAlarm',
            'version': 1.0,
            'rule': {
                'meter_name': 'cpu_util',
                'threshold': 34,
            },
        }

        old_trigger = self._create_trigger(self.ctx)
        new_trigger = db_api.trigger_update(self.ctx, old_trigger.id,
                                            new_fields)

        self.assertEqual(old_trigger.id, new_trigger.id)
        self.assertEqual(new_fields['name'], new_trigger.name)
        self.assertEqual('new_trigger', new_trigger.name)

    def test_trigger_update_not_found(self):
        self.assertRaises(exception.TriggerNotFound,
                          db_api.trigger_update,
                          self.ctx, 'BogusID', {})

    def test_trigger_delete(self):
        trigger = self._create_trigger(self.ctx)
        self.assertIsNotNone(trigger)
        trigger_id = trigger.id
        db_api.trigger_delete(self.ctx, trigger_id)

        trigger = db_api.trigger_get(self.ctx, trigger_id)
        self.assertIsNone(trigger)

        # not found in delete is okay
        res = db_api.trigger_delete(self.ctx, trigger_id)
        self.assertIsNone(res)
