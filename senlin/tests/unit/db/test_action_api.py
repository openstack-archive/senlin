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

import six
import time

from oslo_utils import timeutils as tu
from senlin.common import consts
from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared


def _create_action(context, action_json=shared.sample_action, **kwargs):
    data = parser.simple_parse(action_json)
    data['user'] = context.user_id
    data['project'] = context.project_id
    data['domain'] = context.domain_id
    data.update(kwargs)
    return db_api.action_create(context, data)


class DBAPIActionTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_action_create(self):
        data = parser.simple_parse(shared.sample_action)
        action = _create_action(self.ctx)

        self.assertIsNotNone(action)
        self.assertEqual(data['name'], action.name)
        self.assertEqual(data['target'], action.target)
        self.assertEqual(data['action'], action.action)
        self.assertEqual(data['cause'], action.cause)
        self.assertEqual(data['timeout'], action.timeout)
        self.assertEqual(data['status'], action.status)
        self.assertEqual(data['status_reason'], action.status_reason)
        self.assertEqual(10, action.inputs['max_size'])
        self.assertEqual(self.ctx.user_id, action.user)
        self.assertEqual(self.ctx.project_id, action.project)
        self.assertEqual(self.ctx.domain_id, action.domain)
        self.assertIsNone(action.outputs)

    def test_action_update(self):
        action = _create_action(self.ctx)
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

        self.assertRaises(exception.ResourceNotFound,
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

    def test_action_get_with_invalid_id(self):
        retobj = db_api.action_get(self.ctx, 'fake-uuid')
        self.assertIsNone(retobj)

    def test_action_get_by_name(self):
        data = parser.simple_parse(shared.sample_action)
        _create_action(self.ctx)
        retobj = db_api.action_get_by_name(self.ctx, data['name'])

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

    def test_action_get_by_name_duplicated(self):
        data = parser.simple_parse(shared.sample_action)
        action = _create_action(self.ctx)
        another_action = _create_action(self.ctx)

        self.assertIsNotNone(action)
        self.assertIsNotNone(another_action)
        self.assertNotEqual(action.id, another_action.id)
        self.assertRaises(exception.MultipleChoices,
                          db_api.action_get_by_name,
                          self.ctx, data['name'])

    def test_action_get_by_name_invalid(self):
        retobj = db_api.action_get_by_name(self.ctx, 'fake-name')
        self.assertIsNone(retobj)

    def test_action_get_by_short_id(self):
        spec1 = {'id': 'same-part-unique-part'}
        spec2 = {'id': 'same-part-part-unique'}
        action1 = _create_action(self.ctx, **spec1)
        action2 = _create_action(self.ctx, **spec2)

        ret_action1 = db_api.action_get_by_short_id(self.ctx, spec1['id'][:11])
        self.assertEqual(ret_action1.id, action1.id)
        ret_action2 = db_api.action_get_by_short_id(self.ctx, spec2['id'][:11])
        self.assertEqual(ret_action2.id, action2.id)

        self.assertRaises(exception.MultipleChoices,
                          db_api.action_get_by_short_id,
                          self.ctx, 'same-part-')

    def test_action_get_project_safe(self):
        parser.simple_parse(shared.sample_action)
        action = _create_action(self.ctx)
        new_ctx = utils.dummy_context(project='another-project')
        retobj = db_api.action_get(new_ctx, action.id, project_safe=True)
        self.assertIsNone(retobj)
        retobj = db_api.action_get(new_ctx, action.id, project_safe=False)
        self.assertIsNotNone(retobj)

    def test_action_get_with_admin_context(self):
        parser.simple_parse(shared.sample_action)
        action = _create_action(self.ctx)
        new_ctx = utils.dummy_context(project='another-project', is_admin=True)
        retobj = db_api.action_get(new_ctx, action.id, project_safe=True)
        self.assertIsNone(retobj)
        retobj = db_api.action_get(new_ctx, action.id, project_safe=False)
        self.assertIsNotNone(retobj)

    def test_acquire_first_ready_none(self):
        data = {'created_at': tu.utcnow(True)}

        _create_action(self.ctx, **data)
        result = db_api.action_acquire_first_ready(self.ctx, 'fake_o',
                                                   tu.utcnow(True))
        self.assertIsNone(result)

    def test_acquire_first_ready_one(self):
        data = {'created_at': tu.utcnow(True)}
        _create_action(self.ctx, **data)

        result = db_api.action_acquire_first_ready(self.ctx, 'fake_o',
                                                   tu.utcnow(True))
        self.assertIsNone(result)

    def test_acquire_first_ready_mult(self):
        data = {
            'created_at': tu.utcnow(True),
            'status': 'READY',
        }
        action1 = _create_action(self.ctx, **data)
        time.sleep(1)

        data['created_at'] = tu.utcnow(True)
        _create_action(self.ctx, **data)

        result = db_api.action_acquire_first_ready(self.ctx, 'fake_o',
                                                   time.time())
        self.assertEqual(action1.id, result.id)

    def test_action_acquire_random_ready(self):
        specs = [
            {'name': 'A01', 'status': 'INIT'},
            {'name': 'A02', 'status': 'READY', 'owner': 'worker1'},
            {'name': 'A03', 'status': 'INIT'},
            {'name': 'A04', 'status': 'READY'}
        ]

        for spec in specs:
            _create_action(self.ctx, **spec)

        worker = 'worker2'
        timestamp = time.time()
        action = db_api.action_acquire_random_ready(self.ctx, worker,
                                                    timestamp)

        self.assertIn(action.name, ('A02', 'A04'))
        self.assertEqual('worker2', action.owner)
        self.assertEqual(consts.ACTION_RUNNING, action.status)
        self.assertEqual(timestamp, action.start_time)

    def test_action_get_all_by_owner(self):
        specs = [
            {'name': 'A01', 'owner': 'work1'},
            {'name': 'A02', 'owner': 'work2'},
            {'name': 'A03', 'owner': 'work1'},
            {'name': 'A04', 'owner': 'work3'}
        ]

        for spec in specs:
            _create_action(self.ctx, **spec)

        actions = db_api.action_get_all_by_owner(self.ctx, 'work1')
        self.assertEqual(2, len(actions))
        names = [p.name for p in actions]
        for spec in ['A01', 'A03']:
            self.assertIn(spec, names)

        action_fake_owner = db_api.action_get_all_by_owner(self.ctx,
                                                           'fake-owner')
        self.assertEqual(0, len(action_fake_owner))

    def test_action_get_all(self):
        specs = [
            {'name': 'A01', 'target': 'cluster_001'},
            {'name': 'A02', 'target': 'node_001'},
        ]

        for spec in specs:
            _create_action(self.ctx, **spec)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(2, len(actions))
        names = [p.name for p in actions]
        for spec in specs:
            self.assertIn(spec['name'], names)

    def test_action_get_all_project_safe(self):
        parser.simple_parse(shared.sample_action)
        _create_action(self.ctx)
        new_ctx = utils.dummy_context(project='another-project')
        actions = db_api.action_get_all(new_ctx, project_safe=True)
        self.assertEqual(0, len(actions))
        actions = db_api.action_get_all(new_ctx, project_safe=False)
        self.assertEqual(1, len(actions))

    def test_action_check_status(self):
        specs = [
            {'name': 'A01', 'target': 'cluster_001'},
            {'name': 'A02', 'target': 'node_001'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx, **spec)
            id_of[spec['name']] = action.id

        db_api.dependency_add(self.ctx, id_of['A02'], id_of['A01'])
        action1 = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(consts.ACTION_WAITING, action1.status)

        timestamp = time.time()
        status = db_api.action_check_status(self.ctx, id_of['A01'], timestamp)
        self.assertEqual(consts.ACTION_WAITING, status)

        status = db_api.action_check_status(self.ctx, id_of['A01'], timestamp)
        self.assertEqual(consts.ACTION_WAITING, status)
        timestamp = time.time()
        db_api.action_mark_succeeded(self.ctx, id_of['A02'], timestamp)

        status = db_api.action_check_status(self.ctx, id_of['A01'], timestamp)
        self.assertEqual(consts.ACTION_READY, status)

        action1 = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual('All depended actions completed.',
                         action1.status_reason)
        self.assertEqual(timestamp, action1.end_time)

    def _check_dependency_add_dependent_list(self):
        specs = [
            {'name': 'A01', 'target': 'cluster_001'},
            {'name': 'A02', 'target': 'node_001'},
            {'name': 'A03', 'target': 'node_002'},
            {'name': 'A04', 'target': 'node_003'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx, **spec)
            id_of[spec['name']] = action.id

        db_api.dependency_add(self.ctx,
                              id_of['A01'],
                              [id_of['A02'], id_of['A03'], id_of['A04']])

        res = db_api.dependency_get_dependents(self.ctx, id_of['A01'])
        self.assertEqual(3, len(res))
        self.assertIn(id_of['A02'], res)
        self.assertIn(id_of['A03'], res)
        self.assertIn(id_of['A04'], res)
        res = db_api.dependency_get_depended(self.ctx, id_of['A01'])
        self.assertEqual(0, len(res))

        for aid in [id_of['A02'], id_of['A03'], id_of['A04']]:
            res = db_api.dependency_get_depended(self.ctx, aid)
            self.assertEqual(1, len(res))
            self.assertIn(id_of['A01'], res)
            res = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(0, len(res))
            action = db_api.action_get(self.ctx, aid)
            self.assertEqual(action.status, consts.ACTION_WAITING)

        return id_of

    def _check_dependency_add_depended_list(self):
        specs = [
            {'name': 'A01', 'target': 'cluster_001'},
            {'name': 'A02', 'target': 'node_001'},
            {'name': 'A03', 'target': 'node_002'},
            {'name': 'A04', 'target': 'node_003'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx, **spec)
            id_of[spec['name']] = action.id

        db_api.dependency_add(self.ctx,
                              [id_of['A02'], id_of['A03'], id_of['A04']],
                              id_of['A01'])

        res = db_api.dependency_get_depended(self.ctx, id_of['A01'])
        self.assertEqual(3, len(res))
        self.assertIn(id_of['A02'], res)
        self.assertIn(id_of['A03'], res)
        self.assertIn(id_of['A04'], res)

        res = db_api.dependency_get_dependents(self.ctx, id_of['A01'])
        self.assertEqual(0, len(res))

        action = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(action.status, consts.ACTION_WAITING)

        for aid in [id_of['A02'], id_of['A03'], id_of['A04']]:
            res = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(1, len(res))
            self.assertIn(id_of['A01'], res)
            res = db_api.dependency_get_depended(self.ctx, aid)
            self.assertEqual(0, len(res))

        return id_of

    def test_dependency_add_depended_list(self):
        self._check_dependency_add_depended_list()

    def test_dependency_add_dependent_list(self):
        self._check_dependency_add_dependent_list()

    def test_action_mark_succeeded(self):
        timestamp = time.time()
        id_of = self._check_dependency_add_dependent_list()

        db_api.action_mark_succeeded(self.ctx, id_of['A01'], timestamp)

        res = db_api.dependency_get_depended(self.ctx, id_of['A01'])
        self.assertEqual(0, len(res))

        action = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(consts.ACTION_SUCCEEDED, action.status)
        self.assertEqual(timestamp, action.end_time)

        for aid in [id_of['A02'], id_of['A03'], id_of['A04']]:
            res = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(0, len(res))

    def _prepare_action_mark_failed_cancel(self):
        specs = [
            {'name': 'A01', 'status': 'INIT', 'target': 'cluster_001'},
            {'name': 'A02', 'status': 'INIT', 'target': 'node_001'},
            {'name': 'A03', 'status': 'INIT', 'target': 'node_002'},
            {'name': 'A04', 'status': 'INIT', 'target': 'node_003'},
            {'name': 'A05', 'status': 'INIT', 'target': 'cluster_002'},
            {'name': 'A06', 'status': 'INIT', 'target': 'cluster_003'},
            {'name': 'A07', 'status': 'INIT', 'target': 'cluster_004'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx, **spec)
            id_of[spec['name']] = action.id

        db_api.dependency_add(self.ctx,
                              [id_of['A02'], id_of['A03'], id_of['A04']],
                              id_of['A01'])

        db_api.dependency_add(self.ctx,
                              id_of['A01'],
                              [id_of['A05'], id_of['A06'], id_of['A07']])

        res = db_api.dependency_get_depended(self.ctx, id_of['A01'])
        self.assertEqual(3, len(res))
        self.assertIn(id_of['A02'], res)
        self.assertIn(id_of['A03'], res)
        self.assertIn(id_of['A04'], res)

        action = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(consts.ACTION_WAITING, action.status)

        for aid in [id_of['A02'], id_of['A03'], id_of['A04']]:
            res = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(1, len(res))
            self.assertIn(id_of['A01'], res)
            res = db_api.dependency_get_depended(self.ctx, aid)
            self.assertEqual(0, len(res))

        res = db_api.dependency_get_dependents(self.ctx, id_of['A01'])
        self.assertEqual(3, len(res))
        self.assertIn(id_of['A05'], res)
        self.assertIn(id_of['A06'], res)
        self.assertIn(id_of['A07'], res)

        for aid in [id_of['A05'], id_of['A06'], id_of['A07']]:
            res = db_api.dependency_get_depended(self.ctx, aid)
            self.assertEqual(1, len(res))
            self.assertIn(id_of['A01'], res)

            res = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(0, len(res))

            action = db_api.action_get(self.ctx, aid)
            self.assertEqual(consts.ACTION_WAITING, action.status)

        return id_of

    def test_engine_mark_failed_with_depended(self):
        timestamp = time.time()
        id_of = self._prepare_action_mark_failed_cancel()
        with db_api.session_for_write() as session:
            db_api._mark_engine_failed(session, id_of['A01'],
                                       timestamp, 'BOOM')
        for aid in [id_of['A02'], id_of['A03'], id_of['A04']]:
            action = db_api.action_get(self.ctx, aid)
            self.assertEqual(consts.ACTION_FAILED, action.status)
            self.assertEqual('BOOM', action.status_reason)
            self.assertEqual(timestamp, action.end_time)

        action = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(consts.ACTION_FAILED, action.status)
        self.assertEqual('BOOM', action.status_reason)
        self.assertEqual(timestamp, action.end_time)

        for aid in [id_of['A02'], id_of['A03'], id_of['A04']]:
            result = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(0, len(result))

    def test_engine_mark_failed_without_depended(self):
        timestamp = time.time()
        id_of = self._prepare_action_mark_failed_cancel()
        with db_api.session_for_write() as session:
            db_api._mark_engine_failed(session, id_of['A02'],
                                       timestamp, 'BOOM')

        for aid in [id_of['A03'], id_of['A04']]:
            action = db_api.action_get(self.ctx, aid)
            self.assertEqual(consts.ACTION_INIT, action.status)
            self.assertNotEqual('BOOM', action.status_reason)
            self.assertNotEqual(timestamp, action.end_time)

        action = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(consts.ACTION_WAITING, action.status)
        self.assertNotEqual('BOOM', action.status_reason)
        self.assertNotEqual(timestamp, action.end_time)

        action_d = db_api.action_get(self.ctx, id_of['A02'])
        self.assertEqual(consts.ACTION_FAILED, action_d.status)
        self.assertEqual('BOOM', action_d.status_reason)
        self.assertEqual(timestamp, action_d.end_time)

        for aid in [id_of['A03'], id_of['A04']]:
            result = db_api.dependency_get_dependents(self.ctx, aid)
            self.assertEqual(1, len(result))
        result = db_api.dependency_get_dependents(self.ctx, id_of['A02'])
        self.assertEqual(0, len(result))

    def test_action_mark_failed(self):
        timestamp = time.time()
        id_of = self._prepare_action_mark_failed_cancel()
        db_api.action_mark_failed(self.ctx, id_of['A01'], timestamp)

        for aid in [id_of['A05'], id_of['A06'], id_of['A07']]:
            action = db_api.action_get(self.ctx, aid)
            self.assertEqual(consts.ACTION_FAILED, action.status)
            self.assertEqual(timestamp, action.end_time)

        result = db_api.dependency_get_dependents(self.ctx, id_of['A01'])
        self.assertEqual(0, len(result))

    def test_action_mark_cancelled(self):
        timestamp = time.time()
        id_of = self._prepare_action_mark_failed_cancel()
        db_api.action_mark_cancelled(self.ctx, id_of['A01'], timestamp)

        for aid in [id_of['A05'], id_of['A06'], id_of['A07']]:
            action = db_api.action_get(self.ctx, aid)
            self.assertEqual(consts.ACTION_CANCELLED, action.status)
            self.assertEqual(timestamp, action.end_time)

        result = db_api.dependency_get_dependents(self.ctx, id_of['A01'])
        self.assertEqual(0, len(result))

    def test_action_mark_ready(self):
        timestamp = time.time()

        specs = [
            {'name': 'A01', 'status': 'INIT', 'target': 'cluster_001'},
            {'name': 'A02', 'status': 'INIT', 'target': 'node_001'},
            {'name': 'A03', 'status': 'INIT', 'target': 'node_002'},
            {'name': 'A04', 'status': 'INIT', 'target': 'node_003'},
            {'name': 'A05', 'status': 'INIT', 'target': 'cluster_002'},
            {'name': 'A06', 'status': 'INIT', 'target': 'cluster_003'},
            {'name': 'A07', 'status': 'INIT', 'target': 'cluster_004'},
        ]

        id_of = {}
        for spec in specs:
            action = _create_action(self.ctx, **spec)
            id_of[spec['name']] = action.id

        db_api.action_mark_ready(self.ctx, id_of['A01'], timestamp)

        action = db_api.action_get(self.ctx, id_of['A01'])
        self.assertEqual(consts.ACTION_READY, action.status)
        self.assertEqual(timestamp, action.end_time)

    def test_action_acquire(self):
        action = _create_action(self.ctx)
        db_api.action_update(self.ctx, action.id, {'status': 'READY'})
        timestamp = time.time()
        action = db_api.action_acquire(self.ctx, action.id, 'worker1',
                                       timestamp)

        self.assertEqual('worker1', action.owner)
        self.assertEqual(consts.ACTION_RUNNING, action.status)
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
            ex = self.assertRaises(exception.EResourceBusy,
                                   db_api.action_delete,
                                   self.ctx, action.id)
            self.assertEqual("The action '%s' is busy now." % action.id,
                             six.text_type(ex))

    def test_action_delete_by_target(self):
        for name in ['CLUSTER_CREATE', 'CLUSTER_RESIZE', 'CLUSTER_DELETE']:
            action = _create_action(self.ctx, action=name, target='CLUSTER_ID')
            self.assertIsNotNone(action)
            action = _create_action(self.ctx, action=name,
                                    target='CLUSTER_ID_2')
            self.assertIsNotNone(action)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(6, len(actions))

        db_api.action_delete_by_target(self.ctx, 'CLUSTER_ID')
        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(3, len(actions))

    def test_action_delete_by_target_with_action(self):
        for name in ['CLUSTER_CREATE', 'CLUSTER_DELETE', 'CLUSTER_DELETE']:
            action = _create_action(self.ctx, action=name, target='CLUSTER_ID')
            self.assertIsNotNone(action)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(3, len(actions))

        db_api.action_delete_by_target(self.ctx, 'CLUSTER_ID',
                                       action=['CLUSTER_DELETE'])
        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(1, len(actions))
        self.assertEqual('CLUSTER_CREATE', actions[0].action)

    def test_action_delete_by_target_with_action_excluded(self):
        for name in ['CLUSTER_CREATE', 'CLUSTER_RESIZE', 'CLUSTER_DELETE']:
            action = _create_action(self.ctx, action=name, target='CLUSTER_ID')
            self.assertIsNotNone(action)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(3, len(actions))

        db_api.action_delete_by_target(self.ctx, 'CLUSTER_ID',
                                       action_excluded=['CLUSTER_DELETE'])
        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(1, len(actions))
        self.assertEqual('CLUSTER_DELETE', actions[0].action)

    def test_action_delete_by_target_with_status(self):
        action1 = _create_action(self.ctx, action='CLUSTER_CREATE',
                                 target='CLUSTER_ID', status='SUCCEEDED')
        action2 = _create_action(self.ctx, action='CLUSTER_DELETE',
                                 target='CLUSTER_ID', status='INIT')
        self.assertIsNotNone(action1)
        self.assertIsNotNone(action2)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(2, len(actions))

        db_api.action_delete_by_target(self.ctx, 'CLUSTER_ID',
                                       status=['SUCCEEDED'])
        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(1, len(actions))
        self.assertEqual('CLUSTER_DELETE', actions[0].action)

    def test_action_delete_by_target_both_specified(self):
        for name in ['CLUSTER_CREATE', 'CLUSTER_RESIZE', 'CLUSTER_DELETE']:
            action = _create_action(self.ctx, action=name, target='CLUSTER_ID')
            self.assertIsNotNone(action)

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(3, len(actions))

        db_api.action_delete_by_target(self.ctx, 'CLUSTER_ID',
                                       action=['CLUSTER_CREATE'],
                                       action_excluded=['CLUSTER_DELETE'])

        actions = db_api.action_get_all(self.ctx)
        self.assertEqual(3, len(actions))

    def test_action_abandon(self):
        spec = {
            "owner": "test_owner",
            "start_time": 14506893904.0
        }
        action = _create_action(self.ctx, **spec)

        before_abandon = db_api.action_get(self.ctx, action.id)
        self.assertEqual(spec['owner'], before_abandon.owner)
        self.assertEqual(spec['start_time'], before_abandon.start_time)
        self.assertIsNone(before_abandon.data)

        db_api.action_abandon(self.ctx, action.id, {})
        after_abandon = db_api.action_get(self.ctx, action.id)

        self.assertIsNone(after_abandon.owner)
        self.assertIsNone(after_abandon.start_time)
        self.assertEqual('The action was abandoned.',
                         after_abandon.status_reason)
        self.assertEqual(consts.ACTION_READY, after_abandon.status)
        self.assertIsNone(after_abandon.data)

    def test_action_abandon_with_params(self):
        spec = {
            "owner": "test_owner",
            "start_time": 14506893904.0
        }
        action = _create_action(self.ctx, **spec)

        before_abandon = db_api.action_get(self.ctx, action.id)
        self.assertEqual(spec['owner'], before_abandon.owner)
        self.assertEqual(spec['start_time'], before_abandon.start_time)
        self.assertIsNone(before_abandon.data)

        db_api.action_abandon(self.ctx, action.id,
                              {'data': {'retries': 1}})
        after_abandon = db_api.action_get(self.ctx, action.id)

        self.assertIsNone(after_abandon.owner)
        self.assertIsNone(after_abandon.start_time)
        self.assertEqual('The action was abandoned.',
                         after_abandon.status_reason)
        self.assertEqual(consts.ACTION_READY, after_abandon.status)
        self.assertEqual({'retries': 1}, after_abandon.data)
