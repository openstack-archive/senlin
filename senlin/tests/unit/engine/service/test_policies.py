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
from senlin.engine import service
from senlin.policies import base as policy_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class PolicyLevelNameTest(base.SenlinTestCase):

    def test_level_name(self):
        names = []
        for level in policy_base.POLICY_LEVELS:
            name = policy_base.getLevelName(level)
            names.append(name)

        for name in names:
            level = policy_base.getLevelName(name)
            self.assertIn(level, policy_base.POLICY_LEVELS)


class PolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(PolicyTest, self).setUp()
        self.ctx = utils.dummy_context(project='policy_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        environment.global_env().register_policy('TestPolicy',
                                                 fakes.TestPolicy)
        self.spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {
                'KEY1': 'value1',
                'KEY2': 2,
            }
        }

    def test_policy_create_default(self):
        self.spec['properties'] = {'KEY2': 5}
        result = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        self.assertIsInstance(result, dict)
        self.assertEqual('p-1', result['name'])
        self.assertEqual('TestPolicy-1.0', result['type'])
        self.assertEqual(self.spec, result['spec'])
        self.assertEqual(policy_base.SHOULD, result['level'])
        self.assertIsNone(result['cooldown'])
        self.assertIsNone(result['updated_time'])
        self.assertIsNone(result['deleted_time'])
        self.assertIsNotNone(result['created_time'])
        self.assertIsNotNone(result['id'])

    def test_policy_create_with_cooldown_and_level(self):
        result = self.eng.policy_create(self.ctx, 'p-1', self.spec,
                                        cooldown=60, level=20)
        self.assertEqual(self.spec, result['spec'])
        self.assertEqual(60, result['cooldown'])
        self.assertEqual(20, result['level'])

    def test_policy_create_type_not_found(self):
        self.spec['type'] = 'Bogus'
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-2', self.spec)
        self.assertEqual(exception.PolicyTypeNotFound, ex.exc_info[0])

    def test_policy_create_invalid_spec(self):
        self.spec['properties'] = {'KEY3': 'value3'}
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-2', self.spec)
        self.assertEqual(exception.SpecValidationFailed, ex.exc_info[0])

    def test_policy_create_failed_validation(self):
        self.spec['properties'] = {'KEY2': 1}
        self.patchobject(fakes.TestPolicy, 'validate',
                         side_effect=exception.InvalidSpec(message='BOOM'))
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-2', self.spec)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])

    def test_policy_get(self):
        p = self.eng.policy_create(self.ctx, 'p-1', self.spec)

        for identity in [p['id'], p['id'][:6], 'p-1']:
            result = self.eng.policy_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(p['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_get, self.ctx, 'Bogus')
        self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])

    def test_policy_list(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        p2 = self.eng.policy_create(self.ctx, 'p-2', self.spec)
        result = self.eng.policy_list(self.ctx)
        self.assertIsInstance(result, list)
        names = [p['name'] for p in result]
        ids = [p['id'] for p in result]
        self.assertIn(p1['name'], names)
        self.assertIn(p2['name'], names)
        self.assertIn(p1['id'], ids)
        self.assertIn(p2['id'], ids)

    def test_policy_list_with_limit_marker(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        p2 = self.eng.policy_create(self.ctx, 'p-2', self.spec)

        result = self.eng.policy_list(self.ctx, limit=0)

        self.assertEqual(0, len(result))
        result = self.eng.policy_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.policy_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.policy_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.policy_list(self.ctx, marker=p1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.policy_list(self.ctx, marker=p2['id'])
        self.assertEqual(0, len(result))

        self.eng.policy_create(self.ctx, 'p-3', self.spec)
        result = self.eng.policy_list(self.ctx, limit=1, marker=p1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.policy_list(self.ctx, limit=2, marker=p1['id'])
        self.assertEqual(2, len(result))

    def test_policy_list_with_sort_keys(self):
        p1 = self.eng.policy_create(self.ctx, 'p-B', self.spec, cooldown=60)
        p2 = self.eng.policy_create(self.ctx, 'p-A', self.spec, cooldown=60)
        p3 = self.eng.policy_create(self.ctx, 'p-C', self.spec, cooldown=120)

        # default by created_time
        result = self.eng.policy_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.policy_list(self.ctx, sort_keys=['name'])
        self.assertEqual(p2['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

        # use permission for sorting
        result = self.eng.policy_list(self.ctx, sort_keys=['cooldown'])
        self.assertEqual(p3['id'], result[2]['id'])

        # use name and permission for sorting
        result = self.eng.policy_list(self.ctx,
                                      sort_keys=['cooldown', 'name'])
        self.assertEqual(p2['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])
        self.assertEqual(p3['id'], result[2]['id'])

        # unknown keys will be ignored
        result = self.eng.policy_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    def test_policy_list_with_sort_dir(self):
        p1 = self.eng.policy_create(self.ctx, 'p-B', self.spec)
        p2 = self.eng.policy_create(self.ctx, 'p-A', self.spec)
        p3 = self.eng.policy_create(self.ctx, 'p-C', self.spec)

        # default by created_time, ascending
        result = self.eng.policy_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # sort by created_time, descending
        result = self.eng.policy_list(self.ctx, sort_dir='desc')
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.policy_list(self.ctx, sort_keys=['name'],
                                      sort_dir='desc')
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

        # use permission for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.policy_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    def test_policy_list_show_deleted(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        result = self.eng.policy_list(self.ctx)
        self.assertEqual(1, len(result))
        self.assertEqual(p1['id'], result[0]['id'])

        self.eng.policy_delete(self.ctx, p1['id'])

        result = self.eng.policy_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.policy_list(self.ctx, show_deleted=True)
        self.assertEqual(1, len(result))
        self.assertEqual(p1['id'], result[0]['id'])

    def test_policy_list_with_filters(self):
        self.eng.policy_create(self.ctx, 'p-B', self.spec, cooldown=60)
        self.eng.policy_create(self.ctx, 'p-A', self.spec, cooldown=60)
        self.eng.policy_create(self.ctx, 'p-C', self.spec, cooldown=0)

        result = self.eng.policy_list(self.ctx, filters={'name': 'p-B'})
        self.assertEqual(1, len(result))
        self.assertEqual('p-B', result[0]['name'])

        result = self.eng.policy_list(self.ctx, filters={'name': 'p-D'})
        self.assertEqual(0, len(result))

        filters = {'cooldown': 60}
        result = self.eng.policy_list(self.ctx, filters=filters)
        self.assertEqual(2, len(result))

    def test_policy_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list, self.ctx,
                               show_deleted='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_policy_list_empty(self):
        result = self.eng.policy_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    def test_policy_find(self):
        p = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        pid = p['id']

        result = self.eng.policy_find(self.ctx, pid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.policy_find(self.ctx, pid[:5])
        self.assertIsNotNone(result)

        # name
        result = self.eng.policy_find(self.ctx, 'p-1')
        self.assertIsNotNone(result)

        # others
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_find, self.ctx, 'Bogus')
        self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])

    def test_policy_find_show_deleted(self):
        p = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        pid = p['id']
        self.eng.policy_delete(self.ctx, pid)

        for identity in [pid, pid[:6], 'p-1']:
            self.assertRaises(rpc.ExpectedException,
                              self.eng.policy_find, self.ctx, identity)

        # short id and name based finding does not support show_deleted
        for identity in [pid[:6], 'p-1']:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.policy_find, self.ctx, identity)
            self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])

        # ID based finding is okay with show_deleted
        result = self.eng.policy_find(self.ctx, pid, show_deleted=True)
        self.assertIsNotNone(result)

    def test_policy_update_fields(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec, cooldown=60,
                                    level=20)
        pid = p1['id']
        self.assertEqual(self.spec, p1['spec'])

        # 1. update name
        p2 = self.eng.policy_update(self.ctx, pid, name='p-2')
        self.assertEqual(pid, p2['id'])
        self.assertEqual('p-2', p2['name'])

        # check persisted into db
        p = self.eng.policy_get(self.ctx, pid)
        self.assertEqual('p-2', p['name'])

        # 2. update cooldown
        p2 = self.eng.policy_update(self.ctx, pid, cooldown=120)
        self.assertEqual(pid, p2['id'])
        self.assertEqual(120, p2['cooldown'])

        # check persisted into db
        p = self.eng.policy_get(self.ctx, pid)
        self.assertEqual(120, p['cooldown'])

        # invalid cooldown value
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update, self.ctx, pid,
                               cooldown=-1)
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        # 3. update level
        p2 = self.eng.policy_update(self.ctx, pid, level=50)
        self.assertEqual(pid, p2['id'])
        self.assertEqual(50, p2['level'])

        # check persisted into db
        p = self.eng.policy_get(self.ctx, pid)
        self.assertEqual(50, p['level'])

        # invalid enforcement level
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update, self.ctx, pid,
                               level=150)
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_policy_update_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, 'Bogus', name='new name')

        self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])

    def test_policy_update_using_find(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        pid = p1['id']

        p2 = self.eng.policy_update(self.ctx, pid, name='p-2')
        self.assertEqual(pid, p2['id'])
        self.assertEqual('p-2', p2['name'])

        # use short id
        p3 = self.eng.policy_update(self.ctx, pid[:6], name='p-3')
        self.assertEqual(pid, p3['id'])
        self.assertEqual('p-3', p3['name'])

        p4 = self.eng.policy_update(self.ctx, 'p-3', name='p-4')
        self.assertEqual(pid, p4['id'])
        self.assertEqual('p-4', p4['name'])

    def test_policy_update_err_validate(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        pid = p1['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, pid, cooldown='yes')

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, pid, level='high')

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_policy_delete(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        pid = p1['id']
        result = self.eng.policy_delete(self.ctx, pid)
        self.assertIsNone(result)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_get, self.ctx, pid)

        self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])

    def test_policy_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_delete, self.ctx, 'Bogus')

        self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])
