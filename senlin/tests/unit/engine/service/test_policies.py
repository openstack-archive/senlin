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

from oslo_config import cfg
from oslo_messaging.rpc import dispatcher as rpc
import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.engine import environment
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class PolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(PolicyTest, self).setUp()
        self.ctx = utils.dummy_context(project='policy_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        environment.global_env().register_policy('TestPolicy-1.0',
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
        self.assertIsNone(result['updated_at'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['id'])

    def test_policy_create_already_exists(self):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        result = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        self.assertIsNotNone(result)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-1', self.spec)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: The policy (p-1) "
                           "already exists."),
                         six.text_type(ex.exc_info[1]))

    def test_policy_create_type_not_found(self):
        self.spec['type'] = 'Bogus'
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-2', self.spec)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified policy "
                         "type (Bogus-1.0) is not supported.",
                         six.text_type(ex.exc_info[1]))

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

    def test_policy_list_with_sorting(self):
        p1 = self.eng.policy_create(self.ctx, 'p-B', self.spec)
        p2 = self.eng.policy_create(self.ctx, 'p-A', self.spec)

        # default by created_at
        result = self.eng.policy_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.policy_list(self.ctx, sort='name')
        self.assertEqual(p2['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

        # unknown keys will be ignored
        result = self.eng.policy_list(self.ctx, sort='duang')
        self.assertIsNotNone(result)

    def test_policy_list_with_sorting_dir(self):
        p1 = self.eng.policy_create(self.ctx, 'p-B', self.spec)
        p2 = self.eng.policy_create(self.ctx, 'p-A', self.spec)
        p3 = self.eng.policy_create(self.ctx, 'p-C', self.spec)

        # default by created_at, ascending
        result = self.eng.policy_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # sort by created_at, descending
        result = self.eng.policy_list(self.ctx, sort='created_at:desc')
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.policy_list(self.ctx, sort='name:desc')
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

    def test_policy_list_with_filters(self):
        self.eng.policy_create(self.ctx, 'p-B', self.spec)
        self.eng.policy_create(self.ctx, 'p-A', self.spec)
        self.eng.policy_create(self.ctx, 'p-C', self.spec)

        result = self.eng.policy_list(self.ctx, filters={'name': 'p-B'})
        self.assertEqual(1, len(result))
        self.assertEqual('p-B', result[0]['name'])

        result = self.eng.policy_list(self.ctx, filters={'name': 'p-D'})
        self.assertEqual(0, len(result))

    def test_policy_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list, self.ctx, limit='no')
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
        self.assertRaises(exception.PolicyNotFound,
                          self.eng.policy_find, self.ctx, 'Bogus')

    def test_policy_update(self):
        p1 = self.eng.policy_create(self.ctx, 'p-1', self.spec)
        pid = p1['id']
        self.assertEqual(self.spec, p1['spec'])

        # 1. update name
        p2 = self.eng.policy_update(self.ctx, pid, name='p-2')
        self.assertEqual(pid, p2['id'])
        self.assertEqual('p-2', p2['name'])

        # check persisted into db
        p = self.eng.policy_get(self.ctx, pid)
        self.assertEqual('p-2', p['name'])

    def test_policy_update_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, 'Bogus', name='new name')

        self.assertEqual(exception.PolicyNotFound, ex.exc_info[0])

    def test_policy_update_name_not_specified(self):
        self.eng.policy_create(self.ctx, 'p-1', self.spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, 'p-1', None)

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])

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
