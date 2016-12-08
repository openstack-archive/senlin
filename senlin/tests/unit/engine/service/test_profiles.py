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
from oslo_config import cfg
from oslo_messaging.rpc import dispatcher as rpc
from oslo_utils import uuidutils
import six

from senlin.common import exception as exc
from senlin.engine import environment
from senlin.engine import service
from senlin.objects import profile as po
from senlin.objects.requests import profiles as vorp
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

        ex = self.assertRaises(exc.ResourceNotFound,
                               self.eng.profile_find,
                               self.ctx, 'Bogus')

        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex))
        mock_get_name.assert_called_once_with(self.ctx, 'Bogus',
                                              project_safe=True)

    @mock.patch.object(pb.Profile, 'load_all')
    def test_profile_list2(self, mock_load):
        x_obj_1 = mock.Mock()
        x_obj_1.to_dict.return_value = {'k': 'v1'}
        x_obj_2 = mock.Mock()
        x_obj_2.to_dict.return_value = {'k': 'v2'}
        mock_load.return_value = [x_obj_1, x_obj_2]
        req = vorp.ProfileListRequest(project_safe=True)

        result = self.eng.profile_list2(self.ctx, req.obj_to_primitive())

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(pb.Profile, 'load_all')
    def test_profile_list2_with_params(self, mock_load):
        mock_load.return_value = []
        marker = uuidutils.generate_uuid()
        params = {
            'limit': 10,
            'marker': marker,
            'name': ['foo'],
            'type': ['os.nova.server'],
            'sort': 'name:asc',
            'project_safe': True
        }
        req = vorp.ProfileListRequest(**params)

        result = self.eng.profile_list2(self.ctx, req.obj_to_primitive())

        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, limit=10, marker=marker,
                                          filters={'name': ['foo'],
                                                   'type': ['os.nova.server']},
                                          sort='name:asc',
                                          project_safe=True)

    @mock.patch.object(pb.Profile, 'create')
    def test_profile_create2_default(self, mock_create):
        x_profile = mock.Mock()
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_create.return_value = x_profile
        self._setup_fakes()
        body = vorp.ProfileCreateRequestBody(name='p-1', spec=self.spec,
                                             metadata={'foo': 'bar'})
        req = vorp.ProfileCreateRequest(profile=body)

        result = self.eng.profile_create2(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)

    @mock.patch.object(po.Profile, 'get_by_name')
    def test_profile_create2_name_conflict(self, mock_get):
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

        body = vorp.ProfileCreateRequestBody(name='FAKE_NAME', spec=spec)
        req = vorp.ProfileCreateRequest(profile=body)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create2,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: A profile named "
                         "'FAKE_NAME' already exists.",
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'FAKE_NAME')

    @mock.patch.object(pb.Profile, 'create')
    def test_profile_create2_type_not_found(self, mock_create):
        self._setup_fakes()
        spec = copy.deepcopy(self.spec)
        spec['type'] = 'Bogus'
        body = vorp.ProfileCreateRequestBody(name='foo', spec=spec)
        req = vorp.ProfileCreateRequest(profile=body)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create2,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The profile_type (Bogus-1.0) could not be found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(pb.Profile, 'create')
    def test_profile_create2_invalid_spec(self, mock_create):
        self._setup_fakes()
        mock_create.side_effect = exc.InvalidSpec(message="badbad")
        body = vorp.ProfileCreateRequestBody(name='foo', spec=self.spec)
        req = vorp.ProfileCreateRequest(profile=body)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_create2,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.InvalidSpec, ex.exc_info[0])
        self.assertEqual("badbad", six.text_type(ex.exc_info[1]))

    def test_profile_validate2(self):
        self._setup_fakes()

        expected_resp = {
            'created_at': None,
            'domain': '',
            'id': None,
            'metadata': None,
            'name': 'validated_profile',
            'project': 'profile_test_project',
            'type': 'TestProfile-1.0',
            'updated_at': None,
            'user': 'test_user_id',
            'spec': {
                'type': 'TestProfile',
                'version': '1.0',
                'properties': {
                    'INT': 1,
                    'STR': 'str',
                    'LIST': ['v1', 'v2'],
                    'MAP': {'KEY1': 1, 'KEY2': 'v2'},
                }
            }
        }

        body = vorp.ProfileValidateRequestBody(spec=self.spec)
        request = vorp.ProfileValidateRequest(profile=body)
        resp = self.eng.profile_validate2(self.ctx, request.obj_to_primitive())
        self.assertEqual(expected_resp, resp)

    def test_profile_validate2_failed(self):
        self._setup_fakes()

        mock_do_validate = self.patchobject(fakes.TestProfile, 'do_validate')
        mock_do_validate.side_effect = exc.ESchema(message='BOOM')

        body = vorp.ProfileValidateRequestBody(spec=self.spec)
        request = vorp.ProfileValidateRequest(profile=body)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_validate2,
                               self.ctx, request.obj_to_primitive())
        self.assertEqual(exc.InvalidSpec, ex.exc_info[0])
        self.assertEqual('BOOM',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(pb.Profile, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_get2(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_profile = mock.Mock()
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_profile
        req = vorp.ProfileGetRequest(identity='FAKE_PROFILE')

        result = self.eng.profile_get2(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_load.assert_called_once_with(self.ctx, profile=x_obj)

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_get2_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='profile',
                                                     id='Bogus')
        req = vorp.ProfileGetRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_get2, self.ctx,
                               req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Profile, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_update2(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_profile = mock.Mock()
        x_profile.name = 'OLD_NAME'
        x_profile.metadata = {'V': 'K'}
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_profile

        params = {'name': 'NEW_NAME', 'metadata': {'K': 'V'}}
        req_body = vorp.ProfileUpdateRequestBody(**params)
        req = vorp.ProfileUpdateRequest(identity='PID', profile=req_body)

        result = self.eng.profile_update2(self.ctx, req.obj_to_primitive())
        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'PID')
        mock_load.assert_called_once_with(self.ctx, profile=x_obj)
        self.assertEqual('NEW_NAME', x_profile.name)
        self.assertEqual({'K': 'V'}, x_profile.metadata)
        x_profile.store.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_update2_not_found(self, mock_find):

        mock_find.side_effect = exc.ResourceNotFound(type='profile',
                                                     id='Bogus')

        req_body = vorp.ProfileUpdateRequestBody(name='NEW_NAME')
        req = vorp.ProfileUpdateRequest(identity='Bogus', profile=req_body)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_update2,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Profile, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_update2_no_change(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_profile = mock.Mock()
        x_profile.name = 'OLD_NAME'
        x_profile.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_profile

        req_body = vorp.ProfileUpdateRequestBody(name='OLD_NAME')
        req = vorp.ProfileUpdateRequest(identity='PID', profile=req_body)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_update2,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual(
            'The request is malformed: No property needs an update.',
            six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PID')
        mock_load.assert_called_once_with(self.ctx, profile=x_obj)
        self.assertEqual(0, x_profile.store.call_count)
        self.assertEqual('OLD_NAME', x_profile.name)

    @mock.patch.object(fakes.TestProfile, 'delete')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_delete2(self, mock_find, mock_delete):
        self._setup_fakes()
        x_obj = mock.Mock(id='PROFILE_ID', type='TestProfile-1.0')
        mock_find.return_value = x_obj
        mock_delete.return_value = None

        req = vorp.ProfileDeleteRequest(identity='PROFILE_ID')
        result = self.eng.profile_delete2(self.ctx, req.obj_to_primitive())

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'PROFILE_ID')
        mock_delete.assert_called_once_with(self.ctx, 'PROFILE_ID')

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_delete2_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='profile',
                                                     id='Bogus')

        req = vorp.ProfileDeleteRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_delete2, self.ctx,
                               req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Profile, 'delete')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_profile_delete2_profile_in_use(self, mock_find, mock_delete):
        self._setup_fakes()
        x_obj = mock.Mock(id='PROFILE_ID', type='TestProfile-1.0')
        mock_find.return_value = x_obj
        err = exc.EResourceBusy(type='profile', id='PROFILE_ID')
        mock_delete.side_effect = err

        req = vorp.ProfileDeleteRequest(identity='PROFILE_ID')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.profile_delete2,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertEqual("The profile PROFILE_ID cannot be deleted: still "
                         "referenced by some clusters and/or nodes.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE_ID')
        mock_delete.assert_called_once_with(self.ctx, 'PROFILE_ID')
