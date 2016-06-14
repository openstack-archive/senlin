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

import copy
from types import GeneratorType

import mock
from oslo_context import context as oslo_ctx
import six

from senlin.common import context as senlin_ctx
from senlin.common import exception
from senlin.common import schema
from senlin.common import utils as common_utils
from senlin.engine import environment
from senlin.engine import parser
from senlin.objects import credential as co
from senlin.objects import profile as po
from senlin.profiles import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


sample_profile = """
  type: os.dummy
  version: 1.0
  properties:
    key1: value1
    key2: 2
"""


class DummyProfile(pb.Profile):

    VERSION = '1.0'
    CONTEXT = 'context'

    properties_schema = {
        CONTEXT: schema.Map(
            'context data'
        ),
        'key1': schema.String(
            'first key',
            default='value1',
            updatable=True,
        ),
        'key2': schema.Integer(
            'second key',
            required=True,
            updatable=True,
        ),
        'key3': schema.String(
            'third key',
        ),
    }
    OPERATIONS = {}

    def __init__(self, name, spec, **kwargs):
        super(DummyProfile, self).__init__(name, spec, **kwargs)


class TestProfileBase(base.SenlinTestCase):

    def setUp(self):
        super(TestProfileBase, self).setUp()
        self.ctx = utils.dummy_context(project='profile_test_project')
        g_env = environment.global_env()
        g_env.register_profile('os.dummy-1.0', DummyProfile)
        self.spec = parser.simple_parse(sample_profile)

    def _create_profile(self, name, pid=None, context=None):
        profile = pb.Profile(name, self.spec,
                             user=self.ctx.user,
                             project=self.ctx.project,
                             domain=self.ctx.domain,
                             context=context)
        if pid:
            profile.id = pid
            profile.context = context

        return profile

    @mock.patch.object(senlin_ctx, 'get_service_context')
    def test_init(self, mock_ctx):
        mock_ctx.return_value = {'foo': 'bar'}
        profile = self._create_profile('test-profile')

        self.assertIsNone(profile.id)
        self.assertEqual('test-profile', profile.name)
        self.assertEqual(self.spec, profile.spec)
        self.assertEqual('os.dummy-1.0', profile.type)
        self.assertEqual(self.ctx.user, profile.user)
        self.assertEqual(self.ctx.project, profile.project)
        self.assertEqual(self.ctx.domain, profile.domain)
        self.assertEqual({}, profile.metadata)
        self.assertIsNone(profile.created_at)
        self.assertIsNone(profile.updated_at)

        spec_data = profile.spec_data
        self.assertEqual('os.dummy', spec_data['type'])
        self.assertEqual('1.0', spec_data['version'])
        self.assertEqual('value1', spec_data['properties']['key1'])
        self.assertEqual(2, spec_data['properties']['key2'])
        self.assertEqual('value1', profile.properties['key1'])
        self.assertEqual(2, profile.properties['key2'])
        self.assertEqual({'foo': 'bar'}, profile.context)

    @mock.patch.object(senlin_ctx, 'get_service_context')
    def test_init_with_context(self, mock_ctx):
        mock_ctx.return_value = {'foo': 'bar'}
        profile = self._create_profile('test-profile',
                                       pid='FAKE_ID', context={'bar': 'foo'})
        self.assertEqual({'bar': 'foo'}, profile.context)

    def test_init_bad_type(self):
        bad_spec = {
            'type': 'bad-type',
            'version': '1.0',
            'properties': '',
        }

        self.assertRaises(exception.ProfileTypeNotFound,
                          pb.Profile,
                          'test-profile', bad_spec)

    def test_init_validation_error(self):
        bad_spec = copy.deepcopy(self.spec)
        del bad_spec['version']

        ex = self.assertRaises(exception.SpecValidationFailed,
                               pb.Profile, 'test-profile', bad_spec)
        self.assertEqual("The 'version' key is missing from the provided "
                         "spec map.", six.text_type(ex))

    def test_from_object(self):
        obj = self._create_profile('test_profile_for_record')
        obj.store(self.ctx)
        profile = po.Profile.get(self.ctx, obj.id)

        result = pb.Profile.from_object(profile)

        self.assertEqual(profile.id, result.id)
        self.assertEqual(profile.name, result.name)
        self.assertEqual(profile.type, result.type)
        self.assertEqual(profile.user, result.user)
        self.assertEqual(profile.project, result.project)
        self.assertEqual(profile.domain, result.domain)
        self.assertEqual(profile.spec, result.spec)
        self.assertEqual(profile.metadata, result.metadata)
        self.assertEqual('value1', result.properties['key1'])
        self.assertEqual(2, result.properties['key2'])

        self.assertEqual(profile.created_at, result.created_at)
        self.assertEqual(profile.updated_at, result.updated_at)
        self.assertEqual(profile.context, result.context)

    def test_load_with_poect(self):
        obj = self._create_profile('test-profile-bb')
        profile_id = obj.store(self.ctx)
        profile = po.Profile.get(self.ctx, profile_id)

        result = pb.Profile.load(self.ctx, profile=profile)

        self.assertEqual(profile.id, result.id)

    def test_load_with_profile_id(self):
        obj = self._create_profile('test-profile-cc')
        profile_id = obj.store(self.ctx)

        result = pb.Profile.load(self.ctx, profile_id=profile_id)

        self.assertEqual(obj.id, result.id)

    def test_load_with_both(self):
        profile = self._create_profile('test1')
        profile.store(self.ctx)
        db_profile = po.Profile.get(self.ctx, profile.id)

        res = pb.Profile.load(self.ctx, profile=db_profile,
                              profile_id=profile.id)

        self.assertEqual(profile.id, res.id)

    @mock.patch.object(po.Profile, 'get')
    def test_load_not_found(self, mock_get):
        mock_get.return_value = None
        self.assertRaises(exception.ProfileNotFound,
                          pb.Profile.load,
                          self.ctx, profile_id='FAKE_ID')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_ID',
                                         project_safe=True)

    @mock.patch.object(po.Profile, 'get_all')
    def test_load_all_empty(self, mock_get):
        mock_get.return_value = []
        res = pb.Profile.load_all(self.ctx)
        self.assertIsInstance(res, GeneratorType)
        value = [v for v in res]
        self.assertEqual([], value)
        mock_get.assert_called_once_with(self.ctx, limit=None, marker=None,
                                         sort=None, filters=None,
                                         project_safe=True)

    @mock.patch.object(po.Profile, 'get_all')
    @mock.patch.object(pb.Profile, 'from_object')
    def test_load_all_with_results(self, mock_from, mock_get):
        dbobj = mock.Mock()
        mock_get.return_value = [dbobj]
        obj = mock.Mock()
        mock_from.return_value = obj
        res = pb.Profile.load_all(self.ctx)
        self.assertIsInstance(res, GeneratorType)
        value = [v for v in res]
        self.assertEqual([obj], value)
        mock_get.assert_called_once_with(self.ctx, limit=None, marker=None,
                                         sort=None, filters=None,
                                         project_safe=True)
        mock_from.assert_called_once_with(dbobj)

    @mock.patch.object(po.Profile, 'get_all')
    @mock.patch.object(pb.Profile, 'from_object')
    def test_load_all_with_params(self, mock_from, mock_get):
        dbobj = mock.Mock()
        mock_get.return_value = [dbobj]
        obj = mock.Mock()
        mock_from.return_value = obj
        res = pb.Profile.load_all(self.ctx, limit=123, marker='MARKER',
                                  sort='FOOKEY', filters='BARDICT',
                                  project_safe=False)
        self.assertIsInstance(res, GeneratorType)
        value = [v for v in res]
        self.assertEqual([obj], value)
        mock_get.assert_called_once_with(self.ctx, limit=123, marker='MARKER',
                                         sort='FOOKEY', filters='BARDICT',
                                         project_safe=False)
        mock_from.assert_called_once_with(dbobj)

    @mock.patch.object(po.Profile, 'delete')
    def test_delete(self, mock_delete):
        res = pb.Profile.delete(self.ctx, 'FAKE_ID')
        self.assertIsNone(res)
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(po.Profile, 'delete')
    def test_delete_busy(self, mock_delete):
        err = exception.ResourceBusyError(resource_type='profile',
                                          resource_id='FAKE_ID')
        mock_delete.side_effect = err
        self.assertRaises(exception.ResourceBusyError,
                          pb.Profile.delete,
                          self.ctx, 'FAKE_ID')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(po.Profile, 'delete')
    def test_delete_not_found(self, mock_delete):
        mock_delete.return_value = None
        result = pb.Profile.delete(self.ctx, 'BOGUS')
        self.assertIsNone(result)
        mock_delete.assert_called_once_with(self.ctx, 'BOGUS')

    @mock.patch.object(po.Profile, 'create')
    def test_store_for_create(self, mock_create):
        profile = self._create_profile('test-profile')
        self.assertIsNone(profile.id)
        self.assertIsNone(profile.created_at)

        mock_create.return_value = mock.Mock(id='FAKE_ID')

        profile_id = profile.store(self.ctx)

        mock_create.assert_called_once_with(
            self.ctx,
            {
                'name': profile.name,
                'type': profile.type,
                'context': profile.context,
                'spec': profile.spec,
                'user': profile.user,
                'project': profile.project,
                'domain': profile.domain,
                'meta_data': profile.metadata,
                'created_at': mock.ANY,
            }
        )
        self.assertEqual('FAKE_ID', profile_id)
        self.assertIsNotNone(profile.created_at)

    @mock.patch.object(po.Profile, 'update')
    def test_store_for_update(self, mock_update):
        profile = self._create_profile('test-profile')
        self.assertIsNone(profile.id)
        self.assertIsNone(profile.updated_at)
        profile.id = 'FAKE_ID'

        profile_id = profile.store(self.ctx)
        self.assertEqual('FAKE_ID', profile.id)
        mock_update.assert_called_once_with(
            self.ctx,
            'FAKE_ID',
            {
                'name': profile.name,
                'type': profile.type,
                'context': profile.context,
                'spec': profile.spec,
                'user': profile.user,
                'project': profile.project,
                'domain': profile.domain,
                'meta_data': profile.metadata,
                'updated_at': mock.ANY,
            }
        )
        self.assertIsNotNone(profile.updated_at)
        self.assertEqual('FAKE_ID', profile_id)

    @mock.patch.object(pb.Profile, 'load')
    def test_create_object(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.create_object(self.ctx, obj)

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_create.assert_called_once_with(obj)
        res_obj = profile.do_create.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_check_object(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.check_object(self.ctx, obj)

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_check.assert_called_once_with(obj)
        res_obj = profile.do_check.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_delete_object(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.delete_object(self.ctx, obj)

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_delete.assert_called_once_with(obj)
        res_obj = profile.do_delete.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_update_object_with_profile(self, mock_load):
        old_profile = mock.Mock()
        new_profile = mock.Mock()

        mock_load.side_effect = [old_profile, new_profile]
        obj = mock.Mock()
        obj.profile_id = 'OLD_ID'

        res = pb.Profile.update_object(self.ctx, obj,
                                       new_profile_id='NEW_ID', foo='bar')

        mock_load.assert_has_calls([
            mock.call(self.ctx, profile_id='OLD_ID'),
            mock.call(self.ctx, profile_id='NEW_ID'),
        ])

        old_profile.do_update.assert_called_once_with(obj, new_profile,
                                                      foo='bar')
        res_obj = old_profile.do_update.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_update_object_without_profile(self, mock_load):
        profile = mock.Mock()

        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.update_object(self.ctx, obj, foo='bar', zoo='car')

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_update.assert_called_once_with(obj, None,
                                                  foo='bar', zoo='car')
        res_obj = profile.do_update.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_recover_object(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.recover_object(self.ctx, obj, foo='bar', zoo='car')

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_recover.assert_called_once_with(obj, foo='bar', zoo='car')
        res_obj = profile.do_recover.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_get_details(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.get_details(self.ctx, obj)

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_get_details.assert_called_once_with(obj)
        res_obj = profile.do_get_details.return_value
        self.assertEqual(res_obj, res)

    def test_get_schema(self):
        expected = {
            'context': {
                'description': 'context data',
                'required': False,
                'updatable': False,
                'type': 'Map'
            },
            'key1': {
                'default': 'value1',
                'description': 'first key',
                'required': False,
                'updatable': True,
                'type': 'String',
            },
            'key2': {
                'description': 'second key',
                'required': True,
                'updatable': True,
                'type': 'Integer'
            },
            'key3': {
                'description': 'third key',
                'required': False,
                'updatable': False,
                'type': 'String'
            },
        }

        actual = DummyProfile.get_schema()
        self.assertEqual(expected, actual)

    @mock.patch.object(pb.Profile, 'load')
    def test_join_cluster(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.join_cluster(self.ctx, obj, 'CLUSTER_ID')

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_join.assert_called_once_with(obj, 'CLUSTER_ID')
        res_obj = profile.do_join.return_value
        self.assertEqual(res_obj, res)

    @mock.patch.object(pb.Profile, 'load')
    def test_leave_cluster(self, mock_load):
        profile = mock.Mock()
        mock_load.return_value = profile
        obj = mock.Mock()
        obj.profile_id = 'FAKE_ID'

        res = pb.Profile.leave_cluster(self.ctx, obj)

        mock_load.assert_called_once_with(self.ctx, profile_id='FAKE_ID')
        profile.do_leave.assert_called_once_with(obj)
        res_obj = profile.do_leave.return_value
        self.assertEqual(res_obj, res)

    def test_validate(self):
        profile = self._create_profile('test_profile')

        profile.spec_data = mock.Mock()
        profile.properties = mock.Mock()

        profile.validate()

        profile.spec_data.validate.assert_called_once_with()
        profile.properties.validate.assert_called_once_with()

    @mock.patch.object(senlin_ctx, 'get_service_context')
    def test__init_context(self, mock_get):
        fake_ctx = mock.Mock()
        mock_get.return_value = fake_ctx

        # _init_context() is called from __init__
        self._create_profile('test-profile')

        # cannot determin the result in this case, we only test none or not
        fake_ctx.pop.assert_has_calls([
            mock.call('project_name', None),
            mock.call('project_domain_name', None),
        ])
        mock_get.assert_called_once_with()

    @mock.patch.object(senlin_ctx, 'get_service_context')
    def test__init_context_for_real(self, mock_get):
        fake_ctx = {
            'project_name': 'this project',
            'project_domain_name': 'this domain',
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        mock_get.return_value = fake_ctx

        # _init_context() is called from __init__
        profile = self._create_profile('test-profile')

        mock_get.assert_called_once_with()
        expected = {
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        self.assertEqual(expected, profile.context)

    @mock.patch.object(senlin_ctx, 'get_service_context')
    def test__init_context_for_real_with_data(self, mock_get):
        fake_ctx = {
            'project_name': 'this project',
            'project_domain_name': 'this domain',
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        mock_get.return_value = fake_ctx
        self.spec['properties']['context'] = {
            'region_name': 'region_dist'
        }

        # _init_context() is called from __init__
        profile = self._create_profile('test-profile')

        mock_get.assert_called_once_with(region_name='region_dist')
        expected = {
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        self.assertEqual(expected, profile.context)

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(oslo_ctx, 'get_current')
    def test__build_conn_params(self, mock_current, mock_get):
        profile = self._create_profile('test-profile')
        profile.context = {'foo': 'bar'}
        fake_cred = mock.Mock(cred={'openstack': {'trust': 'TRUST_ID'}})
        mock_get.return_value = fake_cred
        fake_ctx = mock.Mock()
        mock_current.return_value = fake_ctx

        user = 'FAKE_USER'
        project = 'FAKE_PROJECT'

        res = profile._build_conn_params(user, project)
        expected = {
            'foo': 'bar',
            'trust_id': 'TRUST_ID',
        }
        self.assertEqual(expected, res)
        mock_current.assert_called_once_with()
        mock_get.assert_called_once_with(fake_ctx, 'FAKE_USER', 'FAKE_PROJECT')

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(oslo_ctx, 'get_current')
    def test__build_conn_params_trust_not_found(self, mock_current, mock_get):
        profile = self._create_profile('test-profile')
        mock_get.return_value = None
        fake_ctx = mock.Mock()
        mock_current.return_value = fake_ctx

        self.assertRaises(exception.TrustNotFound,
                          profile._build_conn_params,
                          'FAKE_USER', 'FAKE_PROJECT')

        mock_current.assert_called_once_with()
        mock_get.assert_called_once_with(fake_ctx, 'FAKE_USER', 'FAKE_PROJECT')

    def test_interface_methods(self):
        profile = self._create_profile('test-profile')

        self.assertRaises(NotImplementedError, profile.do_create, mock.Mock())
        self.assertRaises(NotImplementedError, profile.do_delete, mock.Mock())
        self.assertEqual(True, profile.do_update(mock.Mock(), mock.Mock()))
        self.assertEqual(True, profile.do_check(mock.Mock()))
        self.assertEqual({}, profile.do_get_details(mock.Mock()))
        self.assertEqual(True, profile.do_join(mock.Mock(), mock.Mock()))
        self.assertEqual(True, profile.do_leave(mock.Mock()))
        self.assertEqual(True, profile.do_rebuild(mock.Mock()))

    def test_do_recover_default(self):
        profile = self._create_profile('test-profile')
        self.patchobject(profile, 'do_create', return_value=True)
        self.patchobject(profile, 'do_delete', return_value=True)

        self.assertEqual(True, profile.do_recover(mock.Mock()))

        self.assertEqual(True,
                         profile.do_recover(mock.Mock(), foo='bar'))
        self.assertEqual(False,
                         profile.do_recover(mock.Mock(), operation='bar'))

    def test_do_recover_with_recreate_succeeded(self):
        profile = self._create_profile('test-profile')

        self.patchobject(profile, 'do_delete', return_value=True)
        self.patchobject(profile, 'do_create', return_value=True)
        res = profile.do_recover(mock.Mock(), operation='RECREATE')
        self.assertTrue(res)

    def test_do_recover_with_recreate_failed_delete(self):
        profile = self._create_profile('test-profile')

        # Fail because do_delete not implemented
        self.assertRaises(NotImplementedError,
                          profile.do_recover,
                          mock.Mock(), operation='RECREATE')

        # Failed in do_delete
        self.patchobject(profile, 'do_delete', return_value=False)
        res = profile.do_recover(mock.Mock(), operation='RECREATE')
        self.assertFalse(res)

    def test_do_recover_with_recreate_failed_create(self):
        profile = self._create_profile('test-profile')

        # Failed because do_create is not implemented (weird case)
        self.patchobject(profile, 'do_delete', return_value=True)
        res = profile.do_recover(mock.Mock(), operation='RECREATE')
        self.assertEqual(False, res)

        # Failed in do_create
        self.patchobject(profile, 'do_delete', return_value=True)
        self.patchobject(profile, 'do_create', return_value=False)
        res = profile.do_recover(mock.Mock(), operation='RECREATE')
        self.assertFalse(res)

        # Failed in do_create with exception
        self.patchobject(profile, 'do_create', side_effect=Exception)
        res = profile.do_recover(mock.Mock(), operation='RECREATE')
        self.assertFalse(res)

    def test_to_dict(self):
        profile = self._create_profile('test-profile')
        # simulate a store()
        profile.id = 'FAKE_ID'
        expected = {
            'id': 'FAKE_ID',
            'name': profile.name,
            'type': profile.type,
            'user': profile.user,
            'project': profile.project,
            'domain': profile.domain,
            'spec': profile.spec,
            'metadata': profile.metadata,
            'created_at': common_utils.isotime(profile.created_at),
            'updated_at': None,
        }

        result = profile.to_dict()
        self.assertEqual(expected, result)

    def test_validate_for_update_succeeded(self):
        profile = self._create_profile('test-profile')

        # Properties are updatable
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['key1'] = 'new_v1'
        new_spec['properties']['key2'] = 3
        new_profile = pb.Profile('new-profile', new_spec,
                                 user=self.ctx.user,
                                 project=self.ctx.project,
                                 domain=self.ctx.domain,
                                 context=None)
        res = profile.validate_for_update(new_profile)
        self.assertTrue(res)

    def test_validate_for_update_failed(self):
        profile = self._create_profile('test-profile')

        # Property is not updatable
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['key3'] = 'new_v3'
        new_profile = pb.Profile('new-profile', new_spec,
                                 user=self.ctx.user,
                                 project=self.ctx.project,
                                 domain=self.ctx.domain,
                                 context=None)

        res = profile.validate_for_update(new_profile)
        self.assertFalse(res)
