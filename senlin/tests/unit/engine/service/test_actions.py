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
from oslo_messaging.rpc import dispatcher as rpc
import six

from senlin.common import exception
from senlin.engine.actions import base as action_base
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ActionTest(base.SenlinTestCase):

    def setUp(self):
        super(ActionTest, self).setUp()
        self.ctx = utils.dummy_context(project='action_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

        self.target = mock.Mock()
        self.target.id = 'Node1'
        self.target.user = 'USER1'
        self.target.project = 'PROJ1'
        self.target.domain = 'DOM1'

    def test_action_create_default(self):
        result = self.eng.action_create(self.ctx, 'a1', self.target,
                                        'OBJECT_ACTION')
        self.assertIsInstance(result, dict)
        self.assertIsNotNone(result['id'])
        self.assertEqual('a1', result['name'])
        self.assertEqual('Node1', result['target'])
        self.assertIsNone(result['inputs'])

    def test_action_get(self):
        a = self.eng.action_create(self.ctx, 'a1', self.target,
                                   'OBJECT_ACTION')

        for identity in [a['id'], a['id'][:6], 'a1']:
            result = self.eng.action_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(a['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_get, self.ctx, 'Bogus')
        self.assertEqual(exception.ActionNotFound, ex.exc_info[0])

    def test_action_list(self):
        a1 = self.eng.action_create(self.ctx, 'a1', self.target,
                                    'OBJECT_ACTION')
        a2 = self.eng.action_create(self.ctx, 'a2', self.target,
                                    'OBJECT_ACTION')
        result = self.eng.action_list(self.ctx)
        self.assertIsInstance(result, list)
        names = [a['name'] for a in result]
        ids = [a['id'] for a in result]
        self.assertIn(a1['name'], names)
        self.assertIn(a2['name'], names)
        self.assertIn(a1['id'], ids)
        self.assertIn(a2['id'], ids)

    def test_action_list_with_limit_marker(self):
        a1 = self.eng.action_create(self.ctx, 'a1', self.target,
                                    'OBJECT_ACTION')
        a2 = self.eng.action_create(self.ctx, 'a2', self.target,
                                    'OBJECT_ACTION')

        result = self.eng.action_list(self.ctx, limit=0)
        self.assertEqual(0, len(result))

        result = self.eng.action_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.action_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.action_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.action_list(self.ctx, marker=a1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.action_list(self.ctx, marker=a2['id'])
        self.assertEqual(0, len(result))

        self.eng.action_create(self.ctx, 'a3', self.target, 'OBJECT_ACTION')
        result = self.eng.action_list(self.ctx, limit=1, marker=a1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.action_list(self.ctx, limit=2, marker=a1['id'])
        self.assertEqual(2, len(result))

    def test_action_list_with_sort_keys(self):
        t1 = mock.Mock()
        t2 = mock.Mock()
        t1.id = 'Node1'
        t2.id = 'Node2'
        t1.user = t2.user = 'USER1'
        t1.project = t2.project = 'PROJ1'
        t1.domain = t2.domain = 'DOM1'

        a1 = self.eng.action_create(self.ctx, 'B', t2, 'CUST_ACT')
        a2 = self.eng.action_create(self.ctx, 'A', t2, 'CUST_ACT')
        a3 = self.eng.action_create(self.ctx, 'C', t1, 'CUST_ACT')

        # default by created_time
        result = self.eng.action_list(self.ctx)
        self.assertEqual(a1['id'], result[0]['id'])
        self.assertEqual(a2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.action_list(self.ctx, sort_keys=['name'])
        self.assertEqual(a2['id'], result[0]['id'])
        self.assertEqual(a1['id'], result[1]['id'])

        # use permission for sorting
        result = self.eng.action_list(self.ctx, sort_keys=['target'])
        self.assertEqual(a3['id'], result[0]['id'])

        # use name and permission for sorting
        result = self.eng.action_list(self.ctx, sort_keys=['target', 'name'])
        self.assertEqual(a3['id'], result[0]['id'])
        self.assertEqual(a2['id'], result[1]['id'])
        self.assertEqual(a1['id'], result[2]['id'])

        # unknown keys will be ignored
        result = self.eng.action_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    def test_action_list_with_sort_dir(self):
        t1 = mock.Mock()
        t2 = mock.Mock()
        t1.id = 'Node1'
        t2.id = 'Node2'
        t1.user = t2.user = 'USER1'
        t1.project = t2.project = 'PROJ1'
        t1.domain = t2.domain = 'DOM1'

        a1 = self.eng.action_create(self.ctx, 'B', t2, 'CUST_ACT')
        a2 = self.eng.action_create(self.ctx, 'A', t2, 'CUST_ACT')
        a3 = self.eng.action_create(self.ctx, 'C', t1, 'CUST_ACT')

        # default by created_time, ascending
        result = self.eng.action_list(self.ctx)
        self.assertEqual(a1['id'], result[0]['id'])
        self.assertEqual(a2['id'], result[1]['id'])

        # sort by created_time, descending
        result = self.eng.action_list(self.ctx, sort_dir='desc')
        self.assertEqual(a3['id'], result[0]['id'])
        self.assertEqual(a2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.action_list(self.ctx, sort_keys=['name'],
                                      sort_dir='desc')
        self.assertEqual(a3['id'], result[0]['id'])
        self.assertEqual(a1['id'], result[1]['id'])

        # use permission for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.action_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    def test_action_list_show_deleted(self):
        a1 = self.eng.action_create(self.ctx, 'a1', self.target, 'CUST_ACT')

        result = self.eng.action_list(self.ctx)

        self.assertEqual(1, len(result))
        self.assertEqual(a1['id'], result[0]['id'])

        self.eng.action_delete(self.ctx, a1['id'])

        result = self.eng.action_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.action_list(self.ctx, show_deleted=True)
        self.assertEqual(1, len(result))
        self.assertEqual(a1['id'], result[0]['id'])

    def test_action_list_with_filters(self):
        t1 = mock.Mock()
        t2 = mock.Mock()
        t1.id = 'Node1'
        t2.id = 'Node2'
        t1.user = t2.user = 'USER1'
        t1.project = t2.project = 'PROJ1'
        t1.domain = t2.domain = 'DOM1'

        self.eng.action_create(self.ctx, 'B', t2, 'CUST_ACT')
        self.eng.action_create(self.ctx, 'A', t2, 'CUST_ACT')
        self.eng.action_create(self.ctx, 'C', t1, 'CUST_ACT')

        result = self.eng.action_list(self.ctx, filters={'name': 'B'})
        self.assertEqual(1, len(result))
        self.assertEqual('B', result[0]['name'])

        result = self.eng.action_list(self.ctx, filters={'name': 'D'})
        self.assertEqual(0, len(result))

        filters = {'target': 'Node2'}
        result = self.eng.action_list(self.ctx, filters=filters)
        self.assertEqual(2, len(result))

    def test_action_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_list, self.ctx,
                               show_deleted='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_action_list_empty(self):
        result = self.eng.action_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    def test_action_find(self):
        a = self.eng.action_create(self.ctx, 'A', self.target, 'CUST_ACT')
        aid = a['id']

        result = self.eng.action_find(self.ctx, aid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.action_find(self.ctx, aid[:5])
        self.assertIsNotNone(result)

        # name
        result = self.eng.action_find(self.ctx, 'A')
        self.assertIsNotNone(result)

        # others
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_find, self.ctx, 'Bogus')
        self.assertEqual(exception.ActionNotFound, ex.exc_info[0])

    def test_action_delete(self):
        a1 = self.eng.action_create(self.ctx, 'A', self.target, 'CUST_ACT')
        aid = a1['id']
        result = self.eng.action_delete(self.ctx, aid)
        self.assertIsNone(result)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_get, self.ctx, aid)

        self.assertEqual(exception.ActionNotFound, ex.exc_info[0])

    @mock.patch.object(action_base.Action, 'delete')
    def test_action_delete_resource_busy(self, mock_delete):
        a1 = self.eng.action_create(self.ctx, 'A', self.target, 'CUST_ACT')
        aid = a1['id']
        ex = exception.ResourceBusyError(resource_type='action',
                                         resource_id=aid)
        mock_delete.side_effect = ex

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_delete, self.ctx, aid)

        self.assertEqual(exception.ResourceInUse, ex.exc_info[0])

    def test_action_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_delete, self.ctx, 'Bogus')

        self.assertEqual(exception.ActionNotFound, ex.exc_info[0])
