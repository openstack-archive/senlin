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

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared
from senlin.openstack.common import log as logging


def _create_action(context, action=shared.sample_action, **kwargs):
    data = parser.parse_action(action)
    data.update(kwargs)
    return db_api.action_create(context, data)


class DBAPIActionTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_action_create(self):
        data = parser.parse_action(shared.sample_action)
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

    def test_action_get(self):
        data = parser.parse_action(shared.sample_action)
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
            _create_action(self.ctx,
                           action=shared.sample_action,
                           **spec)

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
            _create_action(self.ctx,
                           action=shared.sample_action,
                           **spec)

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
        l = action.depended_by['l']
        self.assertEqual(3, len(l))
        self.assertIn(id_of['action_002'], l)
        self.assertIn(id_of['action_003'], l)
        self.assertIn(id_of['action_004'], l)
        self.assertIsNone(action.depends_on)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            l = action.depends_on['l']
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
        l = action.depends_on['l']
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
            l = action.depended_by['l']
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
        self.assertEqual(0, len(action.depends_on['l']))
        self.assertEqual(action.status, db_api.ACTION_READY)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(0, len(action.depended_by['l']))

    def test_action_del_dependency_dependent_list(self):
        id_of = self._check_action_add_dependency_dependent_list()
        db_api.action_del_dependency(self.ctx,
                                     id_of['action_001'],
                                     [id_of['action_002'],
                                      id_of['action_003'],
                                      id_of['action_004']])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        self.assertEqual(0, len(action.depended_by['l']))

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(0, len(action.depends_on['l']))
            self.assertEqual(action.status, db_api.ACTION_READY)

    def test_action_mark_succeeded(self):
        id_of = self._check_action_add_dependency_dependent_list()
        db_api.action_mark_succeeded(self.ctx, id_of['action_001'])

        action = db_api.action_get(self.ctx, id_of['action_001'])
        self.assertEqual(0, len(action.depended_by['l']))
        self.assertEqual(action.status, db_api.ACTION_SUCCEEDED)

        for id in [id_of['action_002'],
                   id_of['action_003'],
                   id_of['action_004']]:
            action = db_api.action_get(self.ctx, id)
            self.assertEqual(0, len(action.depends_on['l']))

    def test_action_start_work_on(self):
        action = _create_action(self.ctx)

        action = db_api.action_start_work_on(self.ctx, action.id, 'worker1')

        self.assertEqual(action.owner, 'worker1')
        self.assertEqual(action.status, db_api.ACTION_RUNNING)

        self.assertRaises(exception.ActionBeingWorked, db_api.action_start_work_on,
                          self.ctx, action.id, 'worker2')

    def test_action_delete(self):
        action = _create_action(self.ctx)
        self.assertIsNotNone(action)
        action_id = action.id
        db_api.action_delete(self.ctx, action.id)

        self.assertRaises(exception.NotFound, db_api.action_get,
                          self.ctx, action_id)
