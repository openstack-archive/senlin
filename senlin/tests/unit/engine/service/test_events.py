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
from oslo_utils import timeutils
import six

from senlin.common import exception
from senlin.engine import event as event_mod
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class EventTest(base.SenlinTestCase):

    def setUp(self):
        super(EventTest, self).setUp()
        self.ctx = utils.dummy_context(project='event_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

    def test_event_list(self):
        ts = timeutils.utcnow()
        e1 = event_mod.Event(ts, 50, status='GOOD', context=self.ctx)
        eid1 = e1.store(self.ctx)
        e2 = event_mod.Event(ts, 50, status='BAD', context=self.ctx)
        eid2 = e2.store(self.ctx)

        result = self.eng.event_list(self.ctx)

        self.assertIsInstance(result, list)
        statuses = [e['status'] for e in result]
        ids = [p['id'] for p in result]
        self.assertIn(e1.status, statuses)
        self.assertIn(e2.status, statuses)
        self.assertIn(eid1, ids)
        self.assertIn(eid2, ids)

    def test_event_list_with_limit_marker(self):
        e1 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        e1.store(self.ctx)
        e2 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        e2.store(self.ctx)

        result = self.eng.event_list(self.ctx, limit=0)

        self.assertEqual(0, len(result))
        result = self.eng.event_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.event_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.event_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.event_list(self.ctx, marker=e1.id)
        self.assertEqual(1, len(result))
        result = self.eng.event_list(self.ctx, marker=e2.id)
        self.assertEqual(0, len(result))

        e3 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        e3.store(self.ctx)
        result = self.eng.event_list(self.ctx, limit=1, marker=e1.id)
        self.assertEqual(1, len(result))
        result = self.eng.event_list(self.ctx, limit=2, marker=e1.id)
        self.assertEqual(2, len(result))

    def test_event_list_with_sort_keys(self):
        e1 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        e1.store(self.ctx)
        e2 = event_mod.Event(timeutils.utcnow(), 40, status='GOOD',
                             context=self.ctx)
        e2.store(self.ctx)
        e3 = event_mod.Event(timeutils.utcnow(), 60, status='BAD',
                             context=self.ctx)
        e3.store(self.ctx)

        # default by timestamp
        result = self.eng.event_list(self.ctx)
        self.assertEqual(e1.id, result[0]['id'])
        self.assertEqual(e2.id, result[1]['id'])

        # use level for sorting
        result = self.eng.event_list(self.ctx, sort_keys=['level'])
        self.assertEqual(e2.id, result[0]['id'])
        self.assertEqual(e1.id, result[1]['id'])

        # use status for sorting
        result = self.eng.event_list(self.ctx, sort_keys=['status'])
        self.assertEqual(e3.id, result[2]['id'])

        # use level and status for sorting
        result = self.eng.event_list(self.ctx,
                                     sort_keys=['status', 'level'])
        self.assertEqual(e3.id, result[2]['id'])
        self.assertEqual(e2.id, result[0]['id'])
        self.assertEqual(e1.id, result[1]['id'])

        # unknown keys will be ignored
        result = self.eng.event_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    def test_event_list_with_sort_dir(self):
        e1 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        e1.store(self.ctx)
        e2 = event_mod.Event(timeutils.utcnow(), 40, status='GOOD',
                             context=self.ctx)
        e2.store(self.ctx)
        e3 = event_mod.Event(timeutils.utcnow(), 60, status='BAD',
                             context=self.ctx)
        e3.store(self.ctx)

        # default by timestamp , ascending
        result = self.eng.event_list(self.ctx)
        self.assertEqual(e1.id, result[0]['id'])
        self.assertEqual(e2.id, result[1]['id'])

        # sort by created_time, descending
        result = self.eng.event_list(self.ctx, sort_dir='desc')
        self.assertEqual(e3.id, result[0]['id'])
        self.assertEqual(e2.id, result[1]['id'])

        # use name for sorting, descending
        result = self.eng.event_list(self.ctx, sort_keys=['name'],
                                     sort_dir='desc')
        self.assertEqual(e3.id, result[0]['id'])
        self.assertEqual(e1.id, result[2]['id'])

        # use permission for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.event_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    def test_event_list_with_filters(self):
        e1 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        e1.store(self.ctx)
        e2 = event_mod.Event(timeutils.utcnow(), 40, status='GOOD',
                             context=self.ctx)
        e2.store(self.ctx)
        e3 = event_mod.Event(timeutils.utcnow(), 60, status='BAD',
                             context=self.ctx)
        e3.store(self.ctx)

        result = self.eng.event_list(self.ctx, filters={'level': 50})
        self.assertEqual(1, len(result))

        result = self.eng.event_list(self.ctx, filters={'level': 10})
        self.assertEqual(0, len(result))

        filters = {'status': 'GOOD'}
        result = self.eng.event_list(self.ctx, filters=filters)
        self.assertEqual(2, len(result))

    def test_event_list_empty(self):
        result = self.eng.event_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    def test_event_find(self):
        e1 = event_mod.Event(timeutils.utcnow(), 50, status='GOOD',
                             context=self.ctx)
        eid = e1.store(self.ctx)

        result = self.eng.event_find(self.ctx, eid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.event_find(self.ctx, eid[:5])
        self.assertIsNotNone(result)

        # others
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.event_find, self.ctx, 'Bogus')
        self.assertEqual(exception.EventNotFound, ex.exc_info[0])
