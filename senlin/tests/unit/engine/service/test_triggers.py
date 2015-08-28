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

from oslo_messaging.rpc import dispatcher as rpc
import six

from senlin.common import exception
from senlin.engine import environment
from senlin.engine import parser
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes

trigger_spec = """
  type: TestTrigger
  version: 1.0
  rule:
    KEY1: a_string
    KEY2: 3
"""


class TriggerTest(base.SenlinTestCase):

    def setUp(self):
        super(TriggerTest, self).setUp()
        self.ctx = utils.dummy_context(project='trigger_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        environment.global_env().register_trigger('TestTrigger',
                                                  fakes.TestTrigger)

    def test_trigger_create(self):
        spec = parser.simple_parse(trigger_spec)
        result = self.eng.trigger_create(self.ctx, 't-1', spec)
        self.assertIsInstance(result, dict)
        self.assertIsNotNone(result['id'])
        self.assertEqual('t-1', result['name'])
        self.assertEqual('TestTrigger', result['type'])
        self.assertEqual('', result['desc'])
        self.assertEqual('insufficient_data', result['state'])
        self.assertEqual('low', result['severity'])
        self.assertEqual({}, result['links'])
        self.assertEqual(spec, result['spec'])
        self.assertEqual(self.ctx.user, result['user'])
        self.assertEqual(self.ctx.project, result['project'])
        self.assertEqual(self.ctx.domain, result['domain'])
        self.assertIsNotNone(result['created_time'])
        self.assertIsNone(result['updated_time'])
        self.assertIsNone(result['deleted_time'])

    def test_trigger_create_with_parameters(self):
        spec = parser.simple_parse(trigger_spec)
        result = self.eng.trigger_create(self.ctx, 't-1', spec,
                                         description='DESC',
                                         enabled=False,
                                         state='OK',
                                         severity='high')
        self.assertEqual(spec, result['spec'])
        self.assertEqual('DESC', result['desc'])
        self.assertFalse(result['enabled'])
        self.assertEqual('OK', result['state'])
        self.assertEqual('high', result['severity'])

    def test_trigger_create_type_not_found(self):
        spec = parser.simple_parse(trigger_spec)
        spec['type'] = 'Bogus'
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_create,
                               self.ctx, 't-1', spec)
        self.assertEqual(exception.TriggerTypeNotFound, ex.exc_info[0])

    def test_trigger_create_invalid_spec(self):
        spec = parser.simple_parse(trigger_spec)
        spec['KEY3'] = 'value3'
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_create,
                               self.ctx, 't-1', spec)
        self.assertEqual(exception.SpecValidationFailed, ex.exc_info[0])

    def test_trigger_create_failed_validation(self):
        spec = parser.simple_parse(trigger_spec)
        self.patchobject(fakes.TestTrigger, 'validate',
                         side_effect=exception.InvalidSpec(message='BOOM'))
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_create,
                               self.ctx, 't1', spec)
        self.assertEqual(exception.InvalidSpec, ex.exc_info[0])

    def test_trigger_get(self):
        spec = parser.simple_parse(trigger_spec)
        t = self.eng.trigger_create(self.ctx, 't-1', spec)

        for identity in [t['id'], t['id'][:6], 't-1']:
            result = self.eng.trigger_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(t['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_get, self.ctx, 'Bogus')
        self.assertEqual(exception.TriggerNotFound, ex.exc_info[0])

    def test_trigger_list(self):
        spec = parser.simple_parse(trigger_spec)
        t1 = self.eng.trigger_create(self.ctx, 't-1', spec)
        t2 = self.eng.trigger_create(self.ctx, 't-2', spec)
        result = self.eng.trigger_list(self.ctx)
        self.assertIsInstance(result, list)
        names = [t['name'] for t in result]
        ids = [t['id'] for t in result]
        self.assertIn(t1['name'], names)
        self.assertIn(t2['name'], names)
        self.assertIn(t1['id'], ids)
        self.assertIn(t2['id'], ids)

    def test_trigger_list_with_limit_marker(self):
        spec = parser.simple_parse(trigger_spec)
        t1 = self.eng.trigger_create(self.ctx, 't-1', spec)
        t2 = self.eng.trigger_create(self.ctx, 't-2', spec)

        result = self.eng.trigger_list(self.ctx, limit=0)

        self.assertEqual(0, len(result))
        result = self.eng.trigger_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.trigger_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.trigger_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.trigger_list(self.ctx, marker=t1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.trigger_list(self.ctx, marker=t2['id'])
        self.assertEqual(0, len(result))

        self.eng.trigger_create(self.ctx, 't-3', spec)
        result = self.eng.trigger_list(self.ctx, limit=1, marker=t1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.trigger_list(self.ctx, limit=2, marker=t1['id'])
        self.assertEqual(2, len(result))

    def test_trigger_list_with_sort_keys(self):
        spec = parser.simple_parse(trigger_spec)
        t1 = self.eng.trigger_create(self.ctx, 'TB', spec, severity='low')
        t2 = self.eng.trigger_create(self.ctx, 'TA', spec, severity='low')
        t3 = self.eng.trigger_create(self.ctx, 'TC', spec, severity='high')

        # default by created_time
        result = self.eng.trigger_list(self.ctx)
        self.assertEqual(t1['id'], result[0]['id'])
        self.assertEqual(t2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.trigger_list(self.ctx, sort_keys=['name'])
        self.assertEqual(t2['id'], result[0]['id'])
        self.assertEqual(t1['id'], result[1]['id'])

        # use permission for sorting
        result = self.eng.trigger_list(self.ctx, sort_keys=['severity'])
        self.assertEqual(t3['id'], result[0]['id'])

        # use name and permission for sorting
        result = self.eng.trigger_list(self.ctx,
                                       sort_keys=['severity', 'name'])
        self.assertEqual(t3['id'], result[0]['id'])
        self.assertEqual(t2['id'], result[1]['id'])
        self.assertEqual(t1['id'], result[2]['id'])

        # unknown keys will be ignored
        result = self.eng.trigger_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    def test_trigger_list_with_sort_dir(self):
        spec = parser.simple_parse(trigger_spec)
        t1 = self.eng.trigger_create(self.ctx, 'TB', spec, severity='low')
        t2 = self.eng.trigger_create(self.ctx, 'TA', spec, severity='low')
        t3 = self.eng.trigger_create(self.ctx, 'TC', spec, severity='high')

        # default by created_time, ascending
        result = self.eng.trigger_list(self.ctx)
        self.assertEqual(t1['id'], result[0]['id'])
        self.assertEqual(t2['id'], result[1]['id'])

        # sort by created_time, descending
        result = self.eng.trigger_list(self.ctx, sort_dir='desc')
        self.assertEqual(t3['id'], result[0]['id'])
        self.assertEqual(t2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.trigger_list(self.ctx, sort_keys=['name'],
                                       sort_dir='desc')
        self.assertEqual(t3['id'], result[0]['id'])
        self.assertEqual(t1['id'], result[1]['id'])

        ex = self.assertRaises(ValueError,
                               self.eng.trigger_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    def test_trigger_list_show_deleted(self):
        spec = parser.simple_parse(trigger_spec)
        t1 = self.eng.trigger_create(self.ctx, 't-1', spec)
        result = self.eng.trigger_list(self.ctx)
        self.assertEqual(1, len(result))
        self.assertEqual(t1['id'], result[0]['id'])

        self.eng.trigger_delete(self.ctx, t1['id'])

        result = self.eng.trigger_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.trigger_list(self.ctx, show_deleted=True)
        self.assertEqual(1, len(result))
        self.assertEqual(t1['id'], result[0]['id'])

    def test_trigger_list_with_filters(self):
        spec = parser.simple_parse(trigger_spec)
        self.eng.trigger_create(self.ctx, 'TB', spec, severity='low')
        self.eng.trigger_create(self.ctx, 'TA', spec, severity='low')
        self.eng.trigger_create(self.ctx, 'TC', spec, severity='high')

        result = self.eng.trigger_list(self.ctx, filters={'name': 'TB'})
        self.assertEqual(1, len(result))
        self.assertEqual('TB', result[0]['name'])

        result = self.eng.trigger_list(self.ctx, filters={'name': 'TD'})
        self.assertEqual(0, len(result))

        filters = {'severity': 'low'}
        result = self.eng.trigger_list(self.ctx, filters=filters)
        self.assertEqual(2, len(result))

    def test_trigger_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_list, self.ctx,
                               show_deleted='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_trigger_list_empty(self):
        result = self.eng.trigger_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    def test_trigger_find(self):
        spec = parser.simple_parse(trigger_spec)
        t = self.eng.trigger_create(self.ctx, 'T', spec)
        tid = t['id']

        result = self.eng.trigger_find(self.ctx, tid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.trigger_find(self.ctx, tid[:5])
        self.assertIsNotNone(result)

        # name
        result = self.eng.trigger_find(self.ctx, 'T')
        self.assertIsNotNone(result)

        # others
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_find, self.ctx, 'Bogus')
        self.assertEqual(exception.TriggerNotFound, ex.exc_info[0])

    def test_trigger_find_show_deleted(self):
        spec = parser.simple_parse(trigger_spec)
        t = self.eng.trigger_create(self.ctx, 'TT', spec)
        tid = t['id']
        self.eng.trigger_delete(self.ctx, tid)

        for identity in [tid, tid[:6], 'TT']:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.trigger_find, self.ctx, identity)
            self.assertEqual(exception.TriggerNotFound, ex.exc_info[0])

        # short id and name based finding does not support show_deleted
        for identity in [tid[:6], 'TT']:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.trigger_find, self.ctx,
                                   identity, show_deleted=True)
            self.assertEqual(exception.TriggerNotFound, ex.exc_info[0])

        # ID based finding is okay with show_deleted
        result = self.eng.trigger_find(self.ctx, tid, show_deleted=True)
        self.assertIsNotNone(result)

    def test_trigger_delete(self):
        spec = parser.simple_parse(trigger_spec)
        t1 = self.eng.trigger_create(self.ctx, 'T1', spec)
        tid = t1['id']
        result = self.eng.trigger_delete(self.ctx, tid)
        self.assertIsNone(result)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_get, self.ctx, tid)

        self.assertEqual(exception.TriggerNotFound, ex.exc_info[0])

    def test_trigger_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.trigger_get, self.ctx, 'Bogus')

        self.assertEqual(exception.TriggerNotFound, ex.exc_info[0])
