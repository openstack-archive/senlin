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
from oslo_config import cfg
from oslo_messaging.rpc import dispatcher as rpc
from oslo_utils import uuidutils
import six

from senlin.common import exception as exc
from senlin.engine import environment
from senlin.engine import service
from senlin.objects import profile as po
from senlin.profiles import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class ProfileTest(base.SenlinTestCase):

    def setUp(self):
        super(ProfileTest, self).setUp()
        self.ctx = utils.dummy_context(project='profile_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    def _setup_fakes(self):
        """Set up fake proflie for the purpose of testing.

        This method is provided in a standalone function because not all
        test cases need such a set up.
        """
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

    @mock.patch.object(po.Profile, 'get')
    def test_profile_find_by_uuid(self, mock_get):
        x_profile = mock.Mock()
        mock_get.return_value = x_profile

        aid = uuidutils.generate_uuid()
        result = self.eng.profile_find(self.ctx, aid)

        self.assertEqual(x_profile, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(po.Profile, 'get_by_name')
    @mock.patch.object(po.Profile, 'get')
    def test_profile_find_by_uuid_as_name(self, mock_get, mock_get_name):
        x_profile = mock.Mock()
        mock_get_name.return_value = x_profile
        mock_get.return_value = None

        aid = uuidutils.generate_uuid()
        result = self.eng.profile_find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_profile, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)

    @mock.patch.object(po.Profile, 'get_by_name')
    def test_profile_find_by_name(self, mock_get_name):
        x_profile = mock.Mock()
        mock_get_name.return_value = x_profile

        aid = 'this-is-not-uuid'
        result = self.eng.profile_find(self.ctx, aid)

        self.assertEqual(x_profile, result)
        mock_get_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(po.Profile, 'get_by_short_id')
    @mock.patch.object(po.Profile, 'get_by_name')
    def test_profile_find_by_shortid(self, mock_get_name, mock_get_shortid):
        x_profile = mock.Mock()
        mock_get_shortid.return_value = x_profile
        mock_get_name.return_value = None

        aid = 'abcd-1234-abcd'
        result = self.eng.profile_find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_profile, result)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, aid,
                                                 project_safe=False)

    @mock.patch.object(po.Profile, 'get_by_name')
    def test_profile_find_not_found(self, mock_get_name):
        mock_get_name.return_value = None

        ex = self.assertRaises(exc.ProfileNotFound,
                               self.eng.profile_find,
                               self.ctx, 'Bogus')

        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex))
        mock_get_name.assert_called_once_with(self.ctx, 'Bogus',
                                              project_safe=True)

    @mock.patch.object(pb.Profile, 'load_all')
    def test_profile_list(self, mock_load):
        x_obj_1 = mock.Mock()
        x_obj_1.to_dict.return_value = {'k': 'v1'}
        x_obj_2 = mock.Mock()
        x_obj_2.to_dict.return_value = {'k': 'v2'}
        mock_load.return_value = [x_obj_1, x_obj_2]

        result = self.eng.profile_list(self.ctx)

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=None, marker=None,
                                          filters=None, sort=None,
                                          project_safe=True)

    @mock.patch.object(pb.Profile, 'load_all')
    def test_profile_list_with_params(self, mock_load):
        mock_load.return_value = []

        result = self.eng.profile_list(self.ctx, limit=10, marker='KEY',
                                       filters={'foo': 'bar'}, sort='name:asc',
                                       project_safe=True)

        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, limit=10, marker='KEY',
                                          filters={'foo': 'bar'},
                                          sort='name:asc',
                                          project_safe=True)

    def test_profile_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list,
                               self.ctx, limit='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list,
                               self.ctx, sort='crazykey')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list,
                               self.ctx, project_safe='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(pb.Profile, 'load_all')
    def test_profile_list_with_project_safe(self, mock_load):
        mock_load.return_value = []

        result = self.eng.profile_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_list,
                               self.ctx, project_safe=False)
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.profile_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.profile_list(self.ctx, project_safe=True)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.profile_list(self.ctx, project_safe=False)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=False)

    def test_profile_create_default(self):
        self._setup_fakes()

        result = self.eng.profile_create(self.ctx, 'p-1', self.spec)

        self.assertEqual('p-1', result['name'])
        self.assertEqual('TestProfile-1.0', result['type'])
        self.assertEqual(self.spec, result['spec'])
        self.assertIsNone(result['updated_at'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['id'])

    @mock.patch.object(po.Profile, 'get_by_name')
    def test_profile_create_name_conflict(self, mock_get):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        mock_get.return_value = mock.Mock()

        spec = {
            'type': 'FakeProfile',
            'version': '1.0',
            'properties': {
                'LIST': ['A', 'B'],
                'MAP': {'KEY1': 11, 'KEY2': 12},
            }
        }

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'FAKE_NAME', spec)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: A profile named "
                         "'FAKE_NAME' already exists.",
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'FAKE_NAME')

    def test_profile_create_type_not_found(self):
        # We skip the fakes setup, so we won't get the proper profile type
        spec = {
            'type': 'FakeProfile',
            'version': '1.0',
            'properties': {
                'LIST': ['A', 'B'],
                'MAP': {'KEY1': 11, 'KEY2': 12},
            }
        }

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'p-2', spec)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified profile "
                         "type (FakeProfile-1.0) is not found.",
                         six.text_type(ex.exc_info[1]))

    def test_profile_create_invalid_spec(self):
        # This test is for the profile object constructor which may throw
        # exceptions if the spec is invalid
        self._setup_fakes()
        self.spec['properties'] = {'KEY3': 'value3'}

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'FAKE_PROFILE', self.spec)

        self.assertEqual(exc.SpecValidationFailed, ex.exc_info[0])
        self.assertEqual('Unrecognizable spec item "KEY3"',
                         six.text_type(ex.exc_info[1]))

    def test_profile_create_failed_validation(self):
        self._setup_fakes()

        mock_validate = self.patchobject(fakes.TestProfile, 'validate')
        mock_validate.side_effect = exc.InvalidSpec(message='BOOM')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create,
                               self.ctx, 'p-2', self.spec)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: BOOM',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(pb.Profile, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_get(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_profile = mock.Mock()
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_profile

        result = self.eng.profile_get(self.ctx, 'FAKE_PROFILE')

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_load.assert_called_once_with(self.ctx, profile=x_obj)

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ProfileNotFound(profile='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_get, self.ctx, 'Bogus')

        self.assertEqual(exc.ProfileNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Profile, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_update(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_profile = mock.Mock()
        x_profile.name = 'OLD_NAME'
        x_profile.metadata = {'V': 'K'}
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_profile

        result = self.eng.profile_update(self.ctx, 'FAKE_PROFILE',
                                         name='NEW_NAME',
                                         metadata={'K': 'V'})
        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_load.assert_called_once_with(self.ctx, profile=x_obj)
        self.assertEqual('NEW_NAME', x_profile.name)
        self.assertEqual({'K': 'V'}, x_profile.metadata)
        x_profile.store.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_update_not_found(self, mock_find):

        mock_find.side_effect = exc.ProfileNotFound(profile='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_update,
                               self.ctx, 'Bogus', name='NEW_NAME')

        self.assertEqual(exc.ProfileNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Profile, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_update_no_change(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_profile = mock.Mock()
        x_profile.name = 'OLD_NAME'
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_profile

        result = self.eng.profile_update(self.ctx, 'FAKE_PROFILE',
                                         name='OLD_NAME')

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_load.assert_called_once_with(self.ctx, profile=x_obj)
        self.assertEqual(0, x_profile.store.call_count)
        self.assertEqual('OLD_NAME', x_profile.name)

    @mock.patch.object(pb.Profile, 'delete')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_delete(self, mock_find, mock_delete):
        x_obj = mock.Mock(id='PROFILE_ID')
        mock_find.return_value = x_obj
        mock_delete.return_value = None

        result = self.eng.profile_delete(self.ctx, 'FAKE_PROFILE')

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_delete.assert_called_once_with(self.ctx, 'PROFILE_ID')

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ProfileNotFound(profile='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_delete, self.ctx, 'Bogus')

        self.assertEqual(exc.ProfileNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Profile, 'delete')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_delete_profile_in_use(self, mock_find, mock_delete):
        x_obj = mock.Mock(id='PROFILE_ID')
        mock_find.return_value = x_obj
        err = exc.ResourceBusyError(resource_type='profile',
                                    resource_id='PROFILE_ID')
        mock_delete.side_effect = err

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_delete,
                               self.ctx, 'FAKE_PROFILE')

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertEqual('The profile (PROFILE_ID) is still in use.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_delete.assert_called_once_with(self.ctx, 'PROFILE_ID')
