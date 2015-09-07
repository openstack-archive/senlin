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

import time

import six

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared


def _create_action(context, action=shared.sample_action, **kwargs):
    data = parser.simple_parse(action)
    data.update(kwargs)
    return db_api.action_create(context, data)


class DBAPIActionTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_action_create(self):
        data = parser.simple_parse(shared.sample_action)
        action = db_api.action_create(self.ctx, data)

        self.assertIsNotNone(action)
        self.assertEqual(data['name'], action.name)
        self.assertEqual(data['target'], action.target)
        self.assertEqual(data['action'], action.action)
        self.assertEqual(data['cause'], action.cause)
        self.assertEqual(data['timeout'], action.timeout)
        self.assertEqual(data['status'], action.status)
        self.assertEqual(data['status_reason'], action.status_reason)
        self.assertEqual(10, action.inputs['max_size'])
        self.assertIsNone(action.outputs)

    def test_action_update(self):
        data = parser.simple_parse(shared.sample_action)
        action = db_api.action_create(self.ctx, data)
        values = {
            'status': 'ERROR',
            'status_reason': 'Cluster creation failed',
            'data': {'key1': 'value1', 'key2': 'value2'}
        }
        db_api.action_update(self.ctx, action.id, values)
        action = db_api.action_get(self.ctx, action.id)
        self.assertEqual('ERROR', action.status)
        self.assertEqual('Cluster creation failed', action.status_reason)
        self.assertEqual({'key1': 'value1', 'key2': 'value2'}, action.data)

        self.assertRaises(exception.ActionNotFound,
                          db_api.action_update, self.ctx, 'fake-uuid', values)

    def test_action_get(self):
        data = parser.simple_parse(shared.sample_action)
        action = _create_action(self.ctx)
        retobj = db_api.action_get(self.ctx, action.id)

        self.assertIsNotNone(retobj)
        self.assertEqual(data['name'], retobj.name)
        self.assertEqual(data['target'], retobj.target)
        self.assertEqual(data['action'], retobj.action)
        self.assertEqual(data['cause'], retobj.cause)
        self.assertEqual(data['timeout'], retobj.timeout)
        self.assertEqual(data['status'], retobj.status)
        self.assertEqual(data['status_reason'], retobj.status_reason)
        self.assertEqual(10, retobj.inputs['max_size'])
        self.assertIsNone(retobj.outputs)

    def test_action_get_1st_ready(self):
        specs = [
            {'name': 'action_001', 'status': 'INIT'},
            {'name': 'action_002', 'status': 'READY'},
            {'name': 'action_003', 'status': 'INIT'},
            {'name': 'action_004', 'status': 'READY'}
        ]

        for spec in specs:
            _create_action(self.ctx, action=shared.sample_action, **spec)

        action = db_api.action_get_1st_ready(self.ctx)
        self.assertTrue(action.name in ['action_002', 'action_004'])

    def test_action_get_all_ready(self):
        specs = [
            {'name': 'action_001', 'status': 'INIT'},
            {'name': 'action_002', 'status': 'READY'},
            {'name': 'action_003', 'status': 'INIT'},
            {'name': 'action_004', 'status': 'READY'}
        ]

        for spec in specs:
            _create_action(self.ctx,
                           action=shared.sample_action,
                           **spec)

        actions = db_api.action_get_all_ready(self.ctx)
        self.assertEqual(2, len(actions))
        names = [p.name for p in actions]
        for spec in ['action_002', 'action_004']:
            self.assertIn(spec, names)

    def test_action_get_all_by_owner(self):
        specs = [
            {'name': 'action_001', 'owner': 'work1'},
            {'name': 'action_002', 'owner': 'work2'},
            {'name': 'action_003', 'owner': 'work1'},
            {'name': 'action_004', 'owner': 'work3'}
        ]

        for spec in specs:
            _create_action(self.ctx,
                           action=shared.sample_action,
                           **spec)

        actions = db_api.action_get_all_by_owner(self.ctx, 'work1')
        self.assertEqual(2, len(actions))
        names = [p.name for p in actions]
        for spec in ['action_001', 'action_003']:
            self.assertIn(spec, names)

    def test_action_get_all(self):
        specs = [
            {'name': 'action_001', 'target': 'cluster_001'},
            {'name': 'action_002', 'target': 'node_001'},
        ]

        for spec in specs:
            _create_action(self.ctx, action=shared.sample_action, **spec)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(2, len(actions))
        names = [p.name for p in actions]
        for spec in specs:
            self.assertIn(spec['name'], names)

    def _check_action_add_dependency_dependent_list(self):
        specs = [
            {'name': 'action_001', 'target': 'cluster_001'},
            {'name': 'action_002', 'target': 'node_001'},
            {'name': 'action_003', 'target': 'node_002'},
            {'name': 'action_004', 'target': 'node_003'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx,
                                    action=shared.sample_action,
                                    **spec)
            id_of[spec['name']] = action.id

        db_api.action_add_dependency(self.ctx,
                                     id_of['action_001'],
                                     [id_of['action_002'],
                                      id_of['action_003'],
                                      id_of['action_004']])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        l = action.depended_by
        self.assertEqual(3, len(l))
        self.assertIn(id_of['action_002'], l)
        self.assertIn(id_of['action_003'], l)
        self.assertIn(id_of['action_004'], l)
        self.assertIsNone(action.depends_on)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            l = action.depends_on
            self.assertEqual(1, len(l))
            self.assertIn(id_of['action_001'], l)
            self.assertIsNone(action.depended_by)
            self.assertEqual(action.status, db_api.ACTION_WAITING)
        return id_of

    def _check_action_add_dependency_depended_list(self):
        specs = [
            {'name': 'action_001', 'target': 'cluster_001'},
            {'name': 'action_002', 'target': 'node_001'},
            {'name': 'action_003', 'target': 'node_002'},
            {'name': 'action_004', 'target': 'node_003'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx,
                                    action=shared.sample_action,
                                    **spec)
            id_of[spec['name']] = action.id

        db_api.action_add_dependency(self.ctx,
                                     [id_of['action_002'],
                                      id_of['action_003'],
                                      id_of['action_004']],
                                     id_of['action_001'])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        l = action.depends_on
        self.assertEqual(3, len(l))
        self.assertIn(id_of['action_002'], l)
        self.assertIn(id_of['action_003'], l)
        self.assertIn(id_of['action_004'], l)
        self.assertIsNone(action.depended_by)
        self.assertEqual(action.status, db_api.ACTION_WAITING)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            l = action.depended_by
            self.assertEqual(1, len(l))
            self.assertIn(id_of['action_001'], l)
            self.assertIsNone(action.depends_on)
        return id_of

    def test_action_add_dependency_depended_list(self):
        self._check_action_add_dependency_depended_list()

    def test_action_add_dependency_dependent_list(self):
        self._check_action_add_dependency_dependent_list()

    def test_action_del_dependency_depended_list(self):
        id_of = self._check_action_add_dependency_depended_list()
        db_api.action_del_dependency(self.ctx,
                                     [id_of['action_002'],
                                      id_of['action_003'],
                                      id_of['action_004']],
                                     id_of['action_001'])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        self.assertEqual(0, len(action.depends_on))
        self.assertEqual(action.status, db_api.ACTION_READY)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(0, len(action.depended_by))

    def test_action_del_dependency_dependent_list(self):
        id_of = self._check_action_add_dependency_dependent_list()
        db_api.action_del_dependency(self.ctx,
                                     id_of['action_001'],
                                     [id_of['action_002'],
                                      id_of['action_003'],
                                      id_of['action_004']])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        self.assertEqual(0, len(action.depended_by))

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(0, len(action.depends_on))
            self.assertEqual(db_api.ACTION_READY, action.status)

    def test_action_mark_succeeded(self):
        timestamp = time.time()
        id_of = self._check_action_add_dependency_dependent_list()
        db_api.action_mark_succeeded(self.ctx, id_of['action_001'], timestamp)

        action = db_api.action_get(self.ctx, id_of['action_001'])
        self.assertEqual(0, len(action.depended_by))
        self.assertEqual(db_api.ACTION_SUCCEEDED, action.status)
        self.assertEqual(db_api.ACTION_SUCCEEDED, action.status)
        self.assertEqual(timestamp, action.end_time)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(0, len(action.depends_on))

    def _prepare_action_mark_failed_cancel(self):
        specs = [
            {'name': 'action_001', 'status': 'INIT', 'target': 'cluster_001'},
            {'name': 'action_002', 'status': 'INIT', 'target': 'node_001'},
            {'name': 'action_003', 'status': 'INIT', 'target': 'node_002'},
            {'name': 'action_004', 'status': 'INIT', 'target': 'node_003'},
            {'name': 'action_005', 'status': 'INIT', 'target': 'cluster_002'},
            {'name': 'action_006', 'status': 'INIT', 'target': 'cluster_003'},
            {'name': 'action_007', 'status': 'INIT', 'target': 'cluster_004'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx, action=shared.sample_action,
                                    **spec)
            # action.status = db_api.ACTION_INIT
            id_of[spec['name']] = action.id

        db_api.action_add_dependency(self.ctx,
                                     [id_of['action_002'],
                                      id_of['action_003'],
                                      id_of['action_004']],
                                     id_of['action_001'])

        db_api.action_add_dependency(self.ctx,
                                     id_of['action_001'],
                                     [id_of['action_005'],
                                      id_of['action_006'],
                                      id_of['action_007']])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        l = action.depends_on
        self.assertEqual(3, len(l))
        self.assertIn(id_of['action_002'], l)
        self.assertIn(id_of['action_003'], l)
        self.assertIn(id_of['action_004'], l)
        self.assertEqual(db_api.ACTION_WAITING, action.status)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            l = action.depended_by
            self.assertEqual(1, len(l))
            self.assertIn(id_of['action_001'], l)
            self.assertIsNone(action.depends_on)

        action = db_api.action_get(self.ctx, id_of['action_001'])
        l = action.depended_by
        self.assertEqual(3, len(l))
        self.assertIn(id_of['action_005'], l)
        self.assertIn(id_of['action_006'], l)
        self.assertIn(id_of['action_007'], l)

        for id in [id_of['action_005'],
                   id_of['action_006'],
                   id_of['action_007']]:
            action = db_api.action_get(self.ctx, id)
            l = action.depends_on
            self.assertEqual(1, len(l))
            self.assertIn(id_of['action_001'], l)
            self.assertIsNone(action.depended_by)
            self.assertEqual(db_api.ACTION_WAITING, action.status)

        return id_of

    def test_action_mark_failed(self):
        timestamp = time.time()
        id_of = self._prepare_action_mark_failed_cancel()
        db_api.action_mark_failed(self.ctx, id_of['action_002'], timestamp)

        for id in [id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(db_api.ACTION_INIT, action.status)

        for id in [id_of['action_002'],
                   id_of['action_001'],
                   id_of['action_005'],
                   id_of['action_006'],
                   id_of['action_007']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(db_api.ACTION_FAILED, action.status)
            self.assertEqual(timestamp, action.end_time)

    def test_action_mark_cancelled(self):
        timestamp = time.time()
        id_of = self._prepare_action_mark_failed_cancel()
        db_api.action_mark_cancelled(self.ctx, id_of['action_002'], timestamp)

        for id in [id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(db_api.ACTION_INIT, action.status)

        for id in [id_of['action_002'],
                   id_of['action_001'],
                   id_of['action_005'],
                   id_of['action_006'],
                   id_of['action_007']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(db_api.ACTION_CANCELED, action.status)
            self.assertEqual(timestamp, action.end_time)

    def test_action_acquire(self):
        action = _create_action(self.ctx)
        action.status = 'READY'
        timestamp = time.time()
        action = db_api.action_acquire(self.ctx, action.id, 'worker1',
                                       timestamp)

        self.assertEqual('worker1', action.owner)
        self.assertEqual(db_api.ACTION_RUNNING, action.status)
        self.assertEqual(timestamp, action.start_time)

        action = db_api.action_acquire(self.ctx, action.id, 'worker2',
                                       timestamp)
        self.assertIsNone(action)

    def test_action_acquire_failed(self):
        action = _create_action(self.ctx)
        timestamp = time.time()
        action = db_api.action_acquire(self.ctx, action.id, 'worker1',
                                       timestamp)
        self.assertIsNone(action)

    def test_action_delete(self):
        action = _create_action(self.ctx)
        self.assertIsNotNone(action)
        res = db_api.action_delete(self.ctx, action.id)
        self.assertIsNone(res)

    def test_action_delete_action_in_use(self):
        for status in ('WAITING', 'RUNNING', 'SUSPENDED'):
            action = _create_action(self.ctx, status=status)
            self.assertIsNotNone(action)
            ex = self.assertRaises(exception.ResourceBusyError,
                                   db_api.action_delete,
                                   self.ctx, action.id)
            self.assertEqual('The action (%s) is busy now.' % action.id,
                             six.text_type(ex))
