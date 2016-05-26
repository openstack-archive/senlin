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
from senlin.objects import policy as po
from senlin.policies import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class PolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(PolicyTest, self).setUp()
        self.ctx = utils.dummy_context(project='policy_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    def _setup_fakes(self):
        """Set up fake policy for the purpose of testing.

        This method is provided in a standalone function because not all
        test cases need such a set up.
        """
        environment.global_env().register_policy('TestPolicy-1.0',
                                                 fakes.TestPolicy)
        self.spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {
                'KEY2': 6
            }
        }

    @mock.patch.object(po.Policy, 'get')
    def test_policy_find_by_uuid(self, mock_get):
        x_policy = mock.Mock()
        mock_get.return_value = x_policy

        aid = uuidutils.generate_uuid()
        result = self.eng.policy_find(self.ctx, aid)

        self.assertEqual(x_policy, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(po.Policy, 'get_by_name')
    @mock.patch.object(po.Policy, 'get')
    def test_policy_find_by_uuid_as_name(self, mock_get, mock_get_name):
        x_policy = mock.Mock()
        mock_get_name.return_value = x_policy
        mock_get.return_value = None

        aid = uuidutils.generate_uuid()
        result = self.eng.policy_find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_policy, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)

    @mock.patch.object(po.Policy, 'get_by_name')
    def test_policy_find_by_name(self, mock_get_name):
        x_policy = mock.Mock()
        mock_get_name.return_value = x_policy

        aid = 'this-is-not-uuid'
        result = self.eng.policy_find(self.ctx, aid)

        self.assertEqual(x_policy, result)
        mock_get_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(po.Policy, 'get_by_short_id')
    @mock.patch.object(po.Policy, 'get_by_name')
    def test_policy_find_by_shortid(self, mock_get_name, mock_get_shortid):
        x_policy = mock.Mock()
        mock_get_shortid.return_value = x_policy
        mock_get_name.return_value = None

        aid = 'abcd-1234-abcd'
        result = self.eng.policy_find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_policy, result)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, aid,
                                                 project_safe=False)

    @mock.patch.object(po.Policy, 'get_by_name')
    def test_policy_find_not_found(self, mock_get_name):
        mock_get_name.return_value = None

        ex = self.assertRaises(exc.PolicyNotFound,
                               self.eng.policy_find,
                               self.ctx, 'Bogus')

        self.assertEqual('The policy (Bogus) could not be found.',
                         six.text_type(ex))
        mock_get_name.assert_called_once_with(self.ctx, 'Bogus',
                                              project_safe=True)

    @mock.patch.object(pb.Policy, 'load_all')
    def test_policy_list(self, mock_load):
        x_obj_1 = mock.Mock()
        x_obj_1.to_dict.return_value = {'k': 'v1'}
        x_obj_2 = mock.Mock()
        x_obj_2.to_dict.return_value = {'k': 'v2'}
        mock_load.return_value = [x_obj_1, x_obj_2]

        result = self.eng.policy_list(self.ctx)

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=None, marker=None,
                                          filters=None, sort=None,
                                          project_safe=True)

    @mock.patch.object(pb.Policy, 'load_all')
    def test_policy_list_with_params(self, mock_load):
        mock_load.return_value = []

        result = self.eng.policy_list(self.ctx, limit=10, marker='KEY',
                                      filters={'foo': 'bar'}, sort='name:asc',
                                      project_safe=True)

        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, limit=10, marker='KEY',
                                          filters={'foo': 'bar'},
                                          sort='name:asc',
                                          project_safe=True)

    def test_policy_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list,
                               self.ctx, limit='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list,
                               self.ctx, sort='invalidkey')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list,
                               self.ctx, project_safe='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(pb.Policy, 'load_all')
    def test_policy_list_with_project_safe(self, mock_load):
        mock_load.return_value = []

        result = self.eng.policy_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_list,
                               self.ctx, project_safe=False)
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.policy_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.policy_list(self.ctx, project_safe=True)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.policy_list(self.ctx, project_safe=False)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=False)

    def test_policy_create_default(self):
        self._setup_fakes()
        self.spec['properties'] = {'KEY2': 5}

        result = self.eng.policy_create(self.ctx, 'p-1', self.spec)

        self.assertEqual('p-1', result['name'])
        self.assertEqual('TestPolicy-1.0', result['type'])
        self.assertEqual(self.spec, result['spec'])
        self.assertIsNone(result['updated_at'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['id'])

    @mock.patch.object(po.Policy, 'get_by_name')
    def test_policy_create_name_conflict(self, mock_get):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        mock_get.return_value = mock.Mock()

        spec = {
            'type': 'FakePolicy',
            'version': '1.0',
            'properties': {
                'KEY2': 6
            }
        }

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'FAKE_NAME', spec)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: A policy named "
                         "'FAKE_NAME' already exists.",
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'FAKE_NAME')

    def test_policy_create_type_not_found(self):
        # We skip the fakes setup, so we won't get the proper policy type
        spec = {
            'type': 'FakePolicy',
            'version': '1.0',
            'properties': {
                'KEY2': 6
            }
        }

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-2', spec)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified policy "
                         "type (FakePolicy-1.0) is not found.",
                         six.text_type(ex.exc_info[1]))

    def test_policy_create_invalid_spec(self):
        # This test is for the policy object constructor which may throw
        # exceptions if the spec is invalid
        self._setup_fakes()
        self.spec['properties'] = {'KEY3': 'value3'}

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'FAKE_POLICY', self.spec)
        self.assertEqual(exc.SpecValidationFailed, ex.exc_info[0])
        self.assertEqual('Spec validation error (KEY2): Required spec item '
                         '"KEY2" not assigned',
                         six.text_type(ex.exc_info[1]))

    def test_policy_create_failed_validation(self):
        self._setup_fakes()

        mock_validate = self.patchobject(fakes.TestPolicy, 'validate')
        mock_validate.side_effect = exc.InvalidSpec(message='BOOM')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, 'p-2', self.spec)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: BOOM',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(pb.Policy, 'load')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_get(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_policy = mock.Mock()
        x_policy.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_policy

        result = self.eng.policy_get(self.ctx, 'FAKE_POLICY')

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_POLICY')
        mock_load.assert_called_once_with(self.ctx, db_policy=x_obj)

    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_get_not_found(self, mock_find):
        mock_find.side_effect = exc.PolicyNotFound(policy='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_get, self.ctx, 'Bogus')

        self.assertEqual(exc.PolicyNotFound, ex.exc_info[0])
        self.assertEqual('The policy (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Policy, 'load')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_update(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_policy = mock.Mock()
        x_policy.name = 'OLD_NAME'
        x_policy.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_policy

        result = self.eng.policy_update(self.ctx, 'FAKE_POLICY',
                                        name='NEW_NAME')
        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_POLICY')
        mock_load.assert_called_once_with(self.ctx, db_policy=x_obj)
        self.assertEqual('NEW_NAME', x_policy.name)
        x_policy.store.assert_called_once_with(self.ctx)

    def test_policy_update_name_not_specified(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, 'FAKE_POLICY', None)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: Policy name not '
                         'specified.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_update_not_found(self, mock_find):

        mock_find.side_effect = exc.PolicyNotFound(policy='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, 'Bogus', name='NEW_NAME')

        self.assertEqual(exc.PolicyNotFound, ex.exc_info[0])
        self.assertEqual('The policy (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Policy, 'load')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_update_no_change(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_policy = mock.Mock()
        x_policy.name = 'OLD_NAME'
        x_policy.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_policy

        result = self.eng.policy_update(self.ctx, 'FAKE_POLICY',
                                        name='OLD_NAME')

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_POLICY')
        mock_load.assert_called_once_with(self.ctx, db_policy=x_obj)
        self.assertEqual(0, x_policy.store.call_count)
        self.assertEqual('OLD_NAME', x_policy.name)

    @mock.patch.object(pb.Policy, 'delete')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_delete(self, mock_find, mock_delete):
        x_obj = mock.Mock(id='POLICY_ID')
        mock_find.return_value = x_obj
        mock_delete.return_value = None

        result = self.eng.policy_delete(self.ctx, 'FAKE_POLICY')

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_POLICY')
        mock_delete.assert_called_once_with(self.ctx, 'POLICY_ID')

    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.PolicyNotFound(policy='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_delete, self.ctx, 'Bogus')

        self.assertEqual(exc.PolicyNotFound, ex.exc_info[0])
        self.assertEqual('The policy (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Policy, 'delete')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_policy_delete_policy_in_use(self, mock_find, mock_delete):
        x_obj = mock.Mock(id='POLICY_ID')
        mock_find.return_value = x_obj
        err = exc.ResourceBusyError(resource_type='policy',
                                    resource_id='POLICY_ID')
        mock_delete.side_effect = err

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_delete,
                               self.ctx, 'FAKE_POLICY')

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertEqual('The policy (POLICY_ID) is still in use.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_POLICY')
        mock_delete.assert_called_once_with(self.ctx, 'POLICY_ID')
