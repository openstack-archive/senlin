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
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class ProfileTest(base.SenlinTestCase):

    def setUp(self):
        super(ProfileTest, self).setUp()
        self.ctx = utils.dummy_context(project='profile_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        environment.global_env().register_profile('TestProfile',
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
        self.assertIsNone(result['permission'])
        self.assertIsNone(result['updated_time'])
        self.assertIsNone(result['deleted_time'])
        self.assertIsNotNone(result['created_time'])
        self.assertIsNotNone(result['id'])

    def test_profile_create_with_perm_and_metadata(self):
        permission = 'fake permission'
        metadata = {'group': 'mars'}
        result = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                         permission=permission,
                                         metadata=metadata)
        self.assertEqual(permission, result['permission'])
        self.assertEqual(metadata, result['metadata'])

    def test_profile_create_type_not_found(self):
        self.spec['type'] = 'Bogus'
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'p', self.spec)
        self.assertEqual(exception.ProfileTypeNotFound, ex.exc_info[0])

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

    def test_profile_list_with_sort_keys(self):
        p1 = self.eng.profile_create(self.ctx, 'p-B', self.spec,
                                     permission='1111')
        p2 = self.eng.profile_create(self.ctx, 'p-A', self.spec,
                                     permission='1111')
        p3 = self.eng.profile_create(self.ctx, 'p-C', self.spec,
                                     permission='0000')

        # default by created_time
        result = self.eng.profile_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.profile_list(self.ctx, sort_keys=['name'])
        self.assertEqual(p2['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

        # use permission for sorting
        result = self.eng.profile_list(self.ctx, sort_keys=['permission'])
        self.assertEqual(p3['id'], result[0]['id'])

        # use name and permission for sorting
        result = self.eng.profile_list(self.ctx,
                                       sort_keys=['permission', 'name'])
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])
        self.assertEqual(p1['id'], result[2]['id'])

        # unknown keys will be ignored
        result = self.eng.profile_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    def test_profile_list_with_sort_dir(self):
        p1 = self.eng.profile_create(self.ctx, 'p-B', self.spec,
                                     permission='1111')
        p2 = self.eng.profile_create(self.ctx, 'p-A', self.spec,
                                     permission='1111')
        p3 = self.eng.profile_create(self.ctx, 'p-C', self.spec,
                                     permission='0000')

        # default by created_time, ascending
        result = self.eng.profile_list(self.ctx)
        self.assertEqual(p1['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # sort by created_time, descending
        result = self.eng.profile_list(self.ctx, sort_dir='desc')
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.profile_list(self.ctx, sort_keys=['name'],
                                       sort_dir='desc')
        self.assertEqual(p3['id'], result[0]['id'])
        self.assertEqual(p1['id'], result[1]['id'])

        # use permission for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.profile_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    def test_profile_list_show_deleted(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        result = self.eng.profile_list(self.ctx)
        self.assertEqual(1, len(result))
        self.assertEqual(p1['id'], result[0]['id'])

        self.eng.profile_delete(self.ctx, p1['id'])

        result = self.eng.profile_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.profile_list(self.ctx, show_deleted=True)
        self.assertEqual(1, len(result))
        self.assertEqual(p1['id'], result[0]['id'])

    def test_profile_list_with_filters(self):
        self.eng.profile_create(self.ctx, 'p-B', self.spec,
                                permission='1111')
        self.eng.profile_create(self.ctx, 'p-A', self.spec,
                                permission='1111')
        self.eng.profile_create(self.ctx, 'p-C', self.spec,
                                permission='0000')

        result = self.eng.profile_list(self.ctx, filters={'name': 'p-B'})
        self.assertEqual(1, len(result))
        self.assertEqual('p-B', result[0]['name'])

        result = self.eng.profile_list(self.ctx, filters={'name': 'p-D'})
        self.assertEqual(0, len(result))

        filters = {'permission': '1111'}
        result = self.eng.profile_list(self.ctx, filters=filters)
        self.assertEqual(2, len(result))

    def test_profile_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list, self.ctx,
                               show_deleted='no')
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
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_find, self.ctx, 'Bogus')
        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    def test_profile_find_show_deleted(self):
        p = self.eng.profile_create(self.ctx, 'p-1', self.spec)
        pid = p['id']
        self.eng.profile_delete(self.ctx, pid)

        for identity in [pid, pid[:6], 'p-1']:
            self.assertRaises(rpc.ExpectedException,
                              self.eng.profile_find, self.ctx, identity)

        # short id and name based finding does not support show_deleted
        for identity in [pid[:6], 'p-1']:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.profile_find, self.ctx, identity)
            self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

        # ID based finding is okay with show_deleted
        result = self.eng.profile_find(self.ctx, pid, show_deleted=True)
        self.assertIsNotNone(result)

    def test_profile_update_fields(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     permission='1111',
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

        # 2. update permission
        p2 = self.eng.profile_update(self.ctx, pid, permission='1100')
        self.assertEqual(pid, p2['id'])
        self.assertEqual('1100', p2['permission'])

        # check persisted into db
        p = self.eng.profile_get(self.ctx, pid)
        self.assertEqual('1100', p['permission'])

        # 3. update metadata
        p2 = self.eng.profile_update(self.ctx, pid, metadata={'bar': 'foo'})
        self.assertEqual(pid, p2['id'])
        self.assertEqual({'bar': 'foo'}, p2['metadata'])

        # check persisted into db
        p = self.eng.profile_get(self.ctx, pid)
        self.assertEqual({'bar': 'foo'}, p['metadata'])

    def test_profile_update_new_spec(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     permission='1111',
                                     metadata={'foo': 'bar'})
        pid = p1['id']

        # update spec only
        new_spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'INT': 2}
        }
        p2 = self.eng.profile_update(self.ctx, pid, spec=new_spec)
        self.assertNotEqual(pid, p2['id'])
        # spec changed but other fields not changed
        self.assertEqual(new_spec, p2['spec'])
        self.assertEqual('p-1', p2['name'])
        self.assertEqual('1111', p2['permission'])
        self.assertEqual({'foo': 'bar'}, p2['metadata'])

        p = self.eng.profile_get(self.ctx, p2['id'])
        self.assertEqual(new_spec, p['spec'])
        self.assertEqual('p-1', p['name'])
        self.assertEqual('1111', p['permission'])
        self.assertEqual({'foo': 'bar'}, p['metadata'])

        # update spec with other fields
        p2 = self.eng.profile_update(self.ctx, pid, name='p-2',
                                     permission='1100', spec=new_spec)

        self.assertNotEqual(pid, p2['id'])
        # spec changed with other fields changed properly
        self.assertEqual(new_spec, p2['spec'])
        self.assertEqual('p-2', p2['name'])
        self.assertEqual('1100', p2['permission'])
        self.assertEqual({'foo': 'bar'}, p2['metadata'])

    def test_profile_update_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_update,
                               self.ctx, 'Bogus', name='new name')

        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    def test_profile_update_using_find(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     permission='1111',
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

    def test_profile_update_err_validate(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     permission='1111',
                                     metadata={'foo': 'bar'})
        pid = p1['id']

        new_spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {
                'bad': 'yes',
            }
        }
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_update,
                               self.ctx, pid, spec=new_spec)

        self.assertEqual(exception.SpecValidationFailed, ex.exc_info[0])

    def test_profile_delete(self):
        p1 = self.eng.profile_create(self.ctx, 'p-1', self.spec,
                                     permission='1111',
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
