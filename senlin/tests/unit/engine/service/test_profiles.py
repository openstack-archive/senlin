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


class ProfileTest(base.SenlinTestCase):

    def setUp(self):
        super(ProfileTest, self).setUp()
        self.ctx = utils.dummy_context(project='profile_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        environment.global_env().register_profile('TestProfile-1.0',
                                                  fakes.TestProfile)

        self.spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {
                'INT': 1,
                'STR': 'str',
                'LIST': ['v1', 'v2'],
                'MAP': {'KEY1': 1, 'KEY2': 'v2'},
            }
        }

    def test_profile_create_default(self):
        result = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        self.assertIsInstance(result, dict)
        self.assertEqual('p-1', result['name'])
        self.assertEqual('TestProfile-1.0', result['type'])
        self.assertEqual(self.spec, result['spec'])
        self.assertIsNone(result['updated_at'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['id'])

    def test_profile_create_already_exists(self):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        result = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        self.assertIsNotNone(result)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'p-1', self.spec)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: The profile (p-1) "
                           "already exists."),
                         six.text_type(ex.exc_info[1]))

    def test_profile_create_with_metadata(self):
        metadata = {'group': 'mars'}
        result = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                         metadata=metadata)
        self.assertEqual(metadata, result['metadata'])

    def test_profile_create_type_not_found(self):
        self.spec['type'] = 'Bogus'
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'p', self.spec)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified profile "
                         "type (Bogus-1.0) is not supported.",
                         six.text_type(ex.exc_info[1]))

    def test_profile_create_invalid_spec(self):
        self.spec['properties'] = {'KEY3': 'value3'}
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'p', self.spec)
        self.assertEqual(exception.SpecValidationFailed, ex.exc_info[0])

    def test_profile_create_failed_validation(self):
        self.spec['properties'] = {'INT': 1}
        self.patchobject(fakes.TestProfile, 'validate',
                         side_effect=exception.InvalidSpec(message='BOOM'))
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create, self.ctx,
                               'p', self.spec)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])

    def test_profile_get(self):
        p = self.eng.profile_create(self.ctx, 'p-1', self.spec)

        for identity in [p['id'], p['id'][:6], 'p-1']:
            result = self.eng.profile_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(p['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_get, self.ctx, 'Bogus')
        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    def test_profile_list(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        p2 = self.eng.profile_create(self.ctx, 'p-2', self.spec)
        result = self.eng.profile_list(self.ctx)
        self.assertIsInstance(result, list)
        names = [p['name'] for p in result]
        ids = [p['id'] for p in result]
        self.assertIn(p1['name'], names)
        self.assertIn(p2['name'], names)
        self.assertIn(p1['id'], ids)
        self.assertIn(p2['id'], ids)

    def test_profile_list_with_limit_marker(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        p2 = self.eng.profile_create(self.ctx, 'p-2', self.spec)

        result = self.eng.profile_list(self.ctx, limit=0)

        self.assertEqual(0, len(result))
        result = self.eng.profile_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.profile_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.profile_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.profile_list(self.ctx, marker=p1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.profile_list(self.ctx, marker=p2['id'])
        self.assertEqual(0, len(result))

        self.eng.profile_create(self.ctx, 'p-3', self.spec)
        result = self.eng.profile_list(self.ctx, limit=1, marker=p1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.profile_list(self.ctx, limit=2, marker=p1['id'])
        self.assertEqual(2, len(result))

    def test_profile_list_with_sorting(self):
        p1 = self.eng.profile_create(self.ctx, 'p-B', self.spec)
        p2 = self.eng.profile_create(self.ctx, 'p-A', self.spec)
        p3 = self.eng.profile_create(self.ctx, 'p-C', self.spec)

        # default by created_at
        result = self.eng.profile_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.profile_list(self.ctx, sort='name')
        self.assertEqual(p2['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

        # use name for sorting (descending)
        result = self.eng.profile_list(self.ctx, sort='name:desc')
        self.assertEqual(p3['id'], result[0]['id'])

        result = self.eng.profile_list(self.ctx, sort='duang')
        self.assertIsNotNone(result)

    def test_profile_list_with_filters(self):
        self.eng.profile_create(self.ctx, 'p-B', self.spec)
        self.eng.profile_create(self.ctx, 'p-A', self.spec)
        self.eng.profile_create(self.ctx, 'p-C', self.spec)

        result = self.eng.profile_list(self.ctx, filters={'name': 'p-B'})
        self.assertEqual(1, len(result))
        self.assertEqual('p-B', result[0]['name'])

        result = self.eng.profile_list(self.ctx, filters={'name': 'p-D'})
        self.assertEqual(0, len(result))

    def test_profile_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_profile_list_empty(self):
        result = self.eng.profile_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    def test_profile_find(self):
        p = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        pid = p['id']

        result = self.eng.profile_find(self.ctx, pid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.profile_find(self.ctx, pid[:5])
        self.assertIsNotNone(result)

        # name
        result = self.eng.profile_find(self.ctx, 'p-1')
        self.assertIsNotNone(result)

        # others
        self.assertRaises(exception.ProfileNotFound,
                          self.eng.profile_find, self.ctx, 'Bogus')

    def test_profile_update_fields(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     metadata={'foo': 'bar'})
        pid = p1['id']
        self.assertEqual(self.spec, p1['spec'])

        # 1. update name
        p2 = self.eng.profile_update(self.ctx, pid, name='p-2')
        self.assertEqual(pid, p2['id'])
        self.assertEqual('p-2', p2['name'])

        # check persisted into db
        p = self.eng.profile_get(self.ctx, pid)
        self.assertEqual('p-2', p['name'])

        # 2. update metadata
        p2 = self.eng.profile_update(self.ctx, pid, metadata={'bar': 'foo'})
        self.assertEqual(pid, p2['id'])
        self.assertEqual({'bar': 'foo'}, p2['metadata'])

        # check persisted into db
        p = self.eng.profile_get(self.ctx, pid)
        self.assertEqual({'bar': 'foo'}, p['metadata'])

    def test_profile_update_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_update,
                               self.ctx, 'Bogus', name='new name')

        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    def test_profile_update_using_find(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     metadata={'foo': 'bar'})
        pid = p1['id']

        p2 = self.eng.profile_update(self.ctx, pid, name='p-2')
        self.assertEqual(pid, p2['id'])
        self.assertEqual('p-2', p2['name'])

        # use short id
        p3 = self.eng.profile_update(self.ctx, pid[:6], name='p-3')
        self.assertEqual(pid, p3['id'])
        self.assertEqual('p-3', p3['name'])

        p4 = self.eng.profile_update(self.ctx, 'p-3', name='p-4')
        self.assertEqual(pid, p4['id'])
        self.assertEqual('p-4', p4['name'])

    def test_profile_delete(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     metadata={'foo': 'bar'})
        pid = p1['id']
        result = self.eng.profile_delete(self.ctx, pid)
        self.assertIsNone(result)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_get, self.ctx, pid)

        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    def test_profile_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_get, self.ctx, 'Bogus')

        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])
