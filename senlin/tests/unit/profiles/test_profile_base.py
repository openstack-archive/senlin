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
from senlin.profiles.os.nova import server as nova_server
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
    OPERATIONS = {
        'op1': schema.Operation(
            'Operation 1',
            schema={
                'param1': schema.StringParam(
                    'description of param1',
                )
            }
        )
    }

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
                             user=self.ctx.user_id,
                             project=self.ctx.project_id,
                             domain=self.ctx.domain_id,
                             context=context)
        if pid:
            profile.id = pid
            profile.context = context

        return profile

    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test_init(self, mock_creds):
        mock_creds.return_value = {'foo': 'bar'}
        profile = self._create_profile('test-profile')

        self.assertIsNone(profile.id)
        self.assertEqual('test-profile', profile.name)
        self.assertEqual(self.spec, profile.spec)
        self.assertEqual('os.dummy', profile.type_name)
        self.assertEqual('1.0', profile.version)
        self.assertEqual('os.dummy-1.0', profile.type)
        self.assertEqual(self.ctx.user_id, profile.user)
        self.assertEqual(self.ctx.project_id, profile.project)
        self.assertEqual(self.ctx.domain_id, profile.domain)
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

        self.assertIsNone(profile._computeclient)
        self.assertIsNone(profile._networkclient)
        self.assertIsNone(profile._orchestrationclient)
        self.assertIsNone(profile._block_storageclient)

    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test_init_with_context(self, mock_creds):
        mock_creds.return_value = {'foo': 'bar'}
        profile = self._create_profile('test-profile',
                                       pid='FAKE_ID', context={'bar': 'foo'})
        self.assertEqual({'bar': 'foo'}, profile.context)

    def test_init_bad_type(self):
        bad_spec = {
            'type': 'bad-type',
            'version': '1.0',
            'properties': '',
        }

        self.assertRaises(exception.ResourceNotFound,
                          pb.Profile,
                          'test-profile', bad_spec)

    def test_init_validation_error(self):
        bad_spec = copy.deepcopy(self.spec)
        del bad_spec['version']

        ex = self.assertRaises(exception.ESchema,
                               pb.Profile, 'test-profile', bad_spec)
        self.assertEqual("The 'version' key is missing from the provided "
                         "spec map.", six.text_type(ex))

    def test_from_object(self):
        obj = self._create_profile('test_profile_for_record')
        obj.store(self.ctx)
        profile = po.Profile.get(self.ctx, obj.id)

        result = pb.Profile._from_object(profile)

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
        self.assertRaises(exception.ResourceNotFound,
                          pb.Profile.load,
                          self.ctx, profile_id='FAKE_ID')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_ID',
                                         project_safe=True)

    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test_create(self, mock_creds):
        mock_creds.return_value = {}
        res = pb.Profile.create(self.ctx, 'my_profile', self.spec)

        self.assertIsInstance(res, pb.Profile)

        obj = po.Profile.get(self.ctx, res.id)
        self.assertEqual('my_profile', obj.name)

    def test_create_profile_type_not_found(self):
        spec = copy.deepcopy(self.spec)
        spec['type'] = "bogus"
        ex = self.assertRaises(exception.InvalidSpec,
                               pb.Profile.create,
                               self.ctx, 'my_profile', spec)

        self.assertEqual("Failed in creating profile my_profile: The "
                         "profile_type 'bogus-1.0' could not be found.",
                         six.text_type(ex))

    @mock.patch.object(pb.Profile, 'validate')
    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test_create_failed_validation(self, mock_creds, mock_validate):
        mock_creds.return_value = {}
        mock_validate.side_effect = exception.ESchema(message="Boom")

        ex = self.assertRaises(exception.InvalidSpec,
                               pb.Profile.create,
                               self.ctx, 'my_profile', self.spec)

        self.assertEqual("Failed in creating profile my_profile: "
                         "Boom", six.text_type(ex))

    @mock.patch.object(po.Profile, 'delete')
    def test_delete(self, mock_delete):
        res = pb.Profile.delete(self.ctx, 'FAKE_ID')
        self.assertIsNone(res)
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(po.Profile, 'delete')
    def test_delete_busy(self, mock_delete):
        err = exception.EResourceBusy(type='profile', id='FAKE_ID')
        mock_delete.side_effect = err
        self.assertRaises(exception.EResourceBusy,
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
    def test_check_object_exception_return_value(self, mock_load):
        profile = pb.Profile
        profile.load(self.ctx).do_check = mock.Mock(
            side_effect=exception.InternalError(code=400, message='BAD'))
        obj = mock_load

        res = profile.check_object(self.ctx, obj)

        profile.load(self.ctx).do_check.assert_called_once_with(obj)
        self.assertFalse(res)

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

    def test_get_ops(self):
        expected = {
            'op1': {
                'description': 'Operation 1',
                'parameters': {
                    'param1': {
                        'type': 'String',
                        'required': False,
                        'description': 'description of param1',
                    }
                }
            },
        }

        actual = DummyProfile.get_ops()
        self.assertEqual(expected, actual)

    @mock.patch.object(nova_server.ServerProfile, 'do_adopt')
    def test_adopt_node(self, mock_adopt):
        obj = mock.Mock()

        res = pb.Profile.adopt_node(self.ctx, obj, "os.nova.server-1.0",
                                    overrides=None, snapshot=False)

        mock_adopt.assert_called_once_with(obj, overrides=None, snapshot=False)
        res_obj = mock_adopt.return_value
        self.assertEqual(res_obj, res)

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

    def test_validate_without_properties(self):
        profile = self._create_profile('test_profile')

        profile.do_validate = mock.Mock()

        profile.validate()

        profile.do_validate.assert_not_called()

    def test_validate_with_properties(self):
        profile = self._create_profile('test_profile')

        profile.do_validate = mock.Mock()

        profile.validate(validate_props=True)

        profile.do_validate.assert_called_once_with(obj=profile)

    def test_validate_bad_context(self):
        spec = {
            "type": "os.dummy",
            "version": "1.0",
            "properties": {
                "context": {
                    "foo": "bar"
                },
                "key1": "value1",
                "key2": 2,
            }
        }
        profile = DummyProfile("p-bad-ctx", spec, user=self.ctx.user_id,
                               project=self.ctx.project_id,
                               domain=self.ctx.domain_id)

        self.assertRaises(exception.ESchema, profile.validate)

    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test__init_context(self, mock_creds):
        fake_ctx = mock.Mock()
        mock_creds.return_value = fake_ctx

        # _init_context() is called from __init__
        self._create_profile('test-profile')

        # cannot determin the result in this case, we only test none or not
        fake_ctx.pop.assert_has_calls([
            mock.call('project_name', None),
            mock.call('project_domain_name', None),
        ])
        mock_creds.assert_called_once_with()

    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test__init_context_for_real(self, mock_creds):
        fake_ctx = {
            'project_name': 'this project',
            'project_domain_name': 'this domain',
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        mock_creds.return_value = fake_ctx

        # _init_context() is called from __init__
        profile = self._create_profile('test-profile')

        mock_creds.assert_called_once_with()
        expected = {
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        self.assertEqual(expected, profile.context)

    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    def test__init_context_for_real_with_data(self, mock_creds):
        fake_ctx = {
            'project_name': 'this project',
            'project_domain_name': 'this domain',
            'auth_url': 'some url',
            'user_id': 'fake_user',
            'foo': 'bar',
        }
        mock_creds.return_value = fake_ctx
        self.spec['properties']['context'] = {
            'region_name': 'region_dist'
        }

        # _init_context() is called from __init__
        profile = self._create_profile('test-profile')

        mock_creds.assert_called_once_with(region_name='region_dist')
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

    @mock.patch.object(pb.Profile, '_build_conn_params')
    @mock.patch("senlin.drivers.base.SenlinDriver")
    def test_compute(self, mock_senlindriver, mock_params):
        obj = mock.Mock()
        sd = mock.Mock()
        cc = mock.Mock()
        sd.compute.return_value = cc
        mock_senlindriver.return_value = sd
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        profile = self._create_profile('test-profile')

        res = profile.compute(obj)

        self.assertEqual(cc, res)
        self.assertEqual(cc, profile._computeclient)
        mock_params.assert_called_once_with(obj.user, obj.project)
        sd.compute.assert_called_once_with(fake_params)

    def test_compute_with_cache(self):
        cc = mock.Mock()
        profile = self._create_profile('test-profile')
        profile._computeclient = cc

        res = profile.compute(mock.Mock())

        self.assertEqual(cc, res)

    @mock.patch.object(pb.Profile, '_build_conn_params')
    @mock.patch("senlin.drivers.base.SenlinDriver")
    def test_neutron_client(self, mock_senlindriver, mock_params):
        obj = mock.Mock()
        sd = mock.Mock()
        nc = mock.Mock()
        sd.network.return_value = nc
        mock_senlindriver.return_value = sd
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        profile = self._create_profile('test-profile')

        res = profile.network(obj)

        self.assertEqual(nc, res)
        self.assertEqual(nc, profile._networkclient)
        mock_params.assert_called_once_with(obj.user, obj.project)
        sd.network.assert_called_once_with(fake_params)

    @mock.patch.object(pb.Profile, '_build_conn_params')
    @mock.patch("senlin.drivers.base.SenlinDriver")
    def test_cinder_client(self, mock_senlindriver, mock_params):
        obj = mock.Mock()
        sd = mock.Mock()
        nc = mock.Mock()
        sd.block_storage.return_value = nc
        mock_senlindriver.return_value = sd
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        profile = self._create_profile('test-profile')

        res = profile.block_storage(obj)

        self.assertEqual(nc, res)
        self.assertEqual(nc, profile._block_storageclient)
        mock_params.assert_called_once_with(obj.user, obj.project)
        sd.block_storage.assert_called_once_with(fake_params)

    def test_interface_methods(self):
        profile = self._create_profile('test-profile')

        self.assertRaises(NotImplementedError, profile.do_create, mock.Mock())
        self.assertRaises(NotImplementedError, profile.do_delete, mock.Mock())
        self.assertTrue(profile.do_update(mock.Mock(), mock.Mock()))
        self.assertTrue(profile.do_check(mock.Mock()))
        self.assertEqual({}, profile.do_get_details(mock.Mock()))
        self.assertTrue(profile.do_join(mock.Mock(), mock.Mock()))
        self.assertTrue(profile.do_leave(mock.Mock()))
        self.assertTrue(profile.do_validate(mock.Mock()))

    def test_do_recover_default(self):
        profile = self._create_profile('test-profile')
        self.patchobject(profile, 'do_create', return_value=True)
        self.patchobject(profile, 'do_delete', return_value=True)

        res = profile.do_recover(mock.Mock())
        self.assertTrue(res)

        res = profile.do_recover(mock.Mock(), operation=[{'name': 'bar'}])
        self.assertFalse(res)

    def test_do_recover_with_fencing(self):
        profile = self._create_profile('test-profile')
        self.patchobject(profile, 'do_create', return_value=True)
        self.patchobject(profile, 'do_delete', return_value=True)
        obj = mock.Mock()

        res = profile.do_recover(obj, ignore_missing=True,
                                 params={"fence_compute": True})

        self.assertTrue(res)
        profile.do_delete.assert_called_once_with(obj, force=True)
        profile.do_create.assert_called_once_with(obj)

    def test_do_recover_with_recreate_succeeded(self):
        profile = self._create_profile('test-profile')
        self.patchobject(profile, 'do_delete', return_value=True)
        self.patchobject(profile, 'do_create', return_value=True)
        operation = [{"name": "RECREATE"}]
        res = profile.do_recover(mock.Mock(), operation=operation)

        self.assertTrue(res)

    def test_do_recover_with_recreate_failed_delete(self):
        profile = self._create_profile('test-profile')
        err = exception.EResourceDeletion(type='STACK', id='ID',
                                          message='BANG')
        self.patchobject(profile, 'do_delete', side_effect=err)
        operation = [{"name": "RECREATE"}]

        ex = self.assertRaises(exception.EResourceOperation,
                               profile.do_recover,
                               mock.Mock(id='NODE_ID'), operation=operation)
        self.assertEqual("Failed in recovering node 'NODE_ID': "
                         "Failed in deleting STACK 'ID': BANG.",
                         six.text_type(ex))

    def test_do_recover_with_recreate_failed_create(self):
        profile = self._create_profile('test-profile')
        self.patchobject(profile, 'do_delete', return_value=True)
        err = exception.EResourceCreation(type='STACK', message='BANNG')
        self.patchobject(profile, 'do_create', side_effect=err)
        operation = [{"name": "RECREATE"}]

        ex = self.assertRaises(exception.EResourceOperation,
                               profile.do_recover,
                               mock.Mock(id='NODE_ID'), operation=operation)

        msg = ("Failed in recovering node 'NODE_ID': Failed in creating "
               "STACK: BANNG.")
        self.assertEqual(msg, six.text_type(ex))

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
                                 user=self.ctx.user_id,
                                 project=self.ctx.project_id,
                                 domain=self.ctx.domain_id,
                                 context=None)
        res = profile.validate_for_update(new_profile)
        self.assertTrue(res)

    def test_validate_for_update_failed(self):
        profile = self._create_profile('test-profile')

        # Property is not updatable
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['key3'] = 'new_v3'
        new_profile = pb.Profile('new-profile', new_spec,
                                 user=self.ctx.user_id,
                                 project=self.ctx.project_id,
                                 domain=self.ctx.domain_id,
                                 context=None)

        res = profile.validate_for_update(new_profile)
        self.assertFalse(res)
