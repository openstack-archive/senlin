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
from senlin.common.i18n import _
from senlin.engine import environment
from senlin.engine import service
from senlin.objects import policy as po
from senlin.objects.requests import policies as orpo
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

    @mock.patch.object(po.Policy, 'get_all')
    def test_policy_list(self, mock_get):
        x_obj_1 = mock.Mock()
        x_obj_1.to_dict.return_value = {'k': 'v1'}
        x_obj_2 = mock.Mock()
        x_obj_2.to_dict.return_value = {'k': 'v2'}
        mock_get.return_value = [x_obj_1, x_obj_2]
        req = orpo.PolicyListRequest(project_safe=True)

        result = self.eng.policy_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(po.Policy, 'get_all')
    def test_policy_list_with_params(self, mock_get):
        mock_get.return_value = []
        marker = uuidutils.generate_uuid()
        params = {
            'limit': 10,
            'marker': marker,
            'name': ['test-policy'],
            'type': ['senlin.policy.scaling-1.0'],
            'sort': 'name:asc',
            'project_safe': True
        }
        req = orpo.PolicyListRequest(**params)

        result = self.eng.policy_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([], result)
        mock_get.assert_called_once_with(
            self.ctx, limit=10, marker=marker, sort='name:asc',
            filters={'name': ['test-policy'],
                     'type': ['senlin.policy.scaling-1.0']},
            project_safe=True)

    def test_policy_create_default(self):
        self._setup_fakes()
        req = orpo.PolicyCreateRequestBody(name='Fake', spec=self.spec)

        result = self.eng.policy_create(self.ctx, req.obj_to_primitive())

        self.assertEqual('Fake', result['name'])
        self.assertEqual('TestPolicy-1.0', result['type'])
        self.assertIsNone(result['updated_at'])
        self.assertIsNotNone(result['created_at'])
        self.assertIsNotNone(result['id'])

    @mock.patch.object(po.Policy, 'get_by_name')
    def test_policy_create_name_conflict(self, mock_get):
        cfg.CONF.set_override('name_unique', True)
        mock_get.return_value = mock.Mock()

        spec = {
            'type': 'FakePolicy',
            'version': '1.0',
            'properties': {
                'KEY2': 6
            }
        }

        req = orpo.PolicyCreateRequestBody(name='FAKE_NAME', spec=spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("A policy named 'FAKE_NAME' already exists.",
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

        req = orpo.PolicyCreateRequestBody(name='Fake', spec=spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The policy_type 'FakePolicy-1.0' could "
                         "not be found.",
                         six.text_type(ex.exc_info[1]))

    def test_policy_create_invalid_spec(self):
        # This test is for the policy object constructor which may throw
        # exceptions if the spec is invalid
        self._setup_fakes()
        spec = copy.deepcopy(self.spec)
        spec['properties'] = {'KEY3': 'value3'}

        req = orpo.PolicyCreateRequestBody(name='Fake', spec=spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.ESchema, ex.exc_info[0])
        self.assertEqual("Required spec item 'KEY2' not provided",
                         six.text_type(ex.exc_info[1]))

    def test_policy_create_invalid_value(self):
        self._setup_fakes()
        spec = copy.deepcopy(self.spec)
        spec['properties']['KEY2'] = 'value3'

        mock_validate = self.patchobject(fakes.TestPolicy, 'validate')
        mock_validate.side_effect = exc.InvalidSpec(
            message="The specified KEY2 'value3' could not be found.")

        req = orpo.PolicyCreateRequestBody(name='Fake', spec=spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.InvalidSpec, ex.exc_info[0])
        self.assertEqual("The specified KEY2 'value3' could not be "
                         "found.", six.text_type(ex.exc_info[1]))

    def test_policy_create_failed_validation(self):
        self._setup_fakes()

        mock_validate = self.patchobject(fakes.TestPolicy, 'validate')
        mock_validate.side_effect = exc.InvalidSpec(message='BOOM')

        req = orpo.PolicyCreateRequestBody(name='Fake', spec=self.spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_create,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.InvalidSpec, ex.exc_info[0])
        self.assertEqual('BOOM', six.text_type(ex.exc_info[1]))

    def test_policy_validate_pass(self):
        self._setup_fakes()

        expected_resp = {
            'created_at': None,
            'domain': '',
            'id': None,
            'data': {},
            'name': 'validated_policy',
            'project': 'policy_test_project',
            'type': 'TestPolicy-1.0',
            'updated_at': None,
            'user': 'test_user_id',
            'spec': {
                'type': 'TestPolicy',
                'version': '1.0',
                'properties': {
                    'KEY2': 6
                }
            }
        }

        body = orpo.PolicyValidateRequestBody(spec=self.spec)

        resp = self.eng.policy_validate(self.ctx, body.obj_to_primitive())
        self.assertEqual(expected_resp, resp)

    def test_policy_validate_failed(self):
        self._setup_fakes()
        mock_validate = self.patchobject(fakes.TestPolicy, 'validate')
        mock_validate.side_effect = exc.InvalidSpec(message='BOOM')

        body = orpo.PolicyValidateRequestBody(spec=self.spec)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_validate,
                               self.ctx, body.obj_to_primitive())
        self.assertEqual(exc.InvalidSpec, ex.exc_info[0])
        self.assertEqual('BOOM',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(po.Policy, 'find')
    def test_policy_get(self, mock_find):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_obj.to_dict.return_value = {'foo': 'bar'}
        req = orpo.PolicyGetRequest(identity='FAKE_POLICY')

        result = self.eng.policy_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_POLICY')

    @mock.patch.object(po.Policy, 'find')
    def test_policy_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='policy',
                                                     id='Fake')
        req = orpo.PolicyGetRequest(identity='POLICY')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_get,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(pb.Policy, 'load')
    @mock.patch.object(po.Policy, 'find')
    def test_policy_update(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_policy = mock.Mock()
        x_policy.name = 'OLD_NAME'
        x_policy.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_policy
        p_req = orpo.PolicyUpdateRequestBody(name='NEW_NAME')
        request = {
            'identity': 'FAKE',
            'policy': p_req
        }

        req = orpo.PolicyUpdateRequest(**request)

        result = self.eng.policy_update(self.ctx, req.obj_to_primitive())
        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE')
        mock_load.assert_called_once_with(self.ctx, db_policy=x_obj)

    @mock.patch.object(po.Policy, 'find')
    def test_policy_update_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='policy',
                                                     id='Fake')
        p_req = orpo.PolicyUpdateRequestBody(name='NEW_NAME')
        request = {
            'identity': 'Fake',
            'policy': p_req
        }

        req = orpo.PolicyUpdateRequest(**request)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(pb.Policy, 'load')
    @mock.patch.object(po.Policy, 'find')
    def test_policy_update_no_change(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_policy = mock.Mock()
        x_policy.name = 'OLD_NAME'
        x_policy.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_policy
        body = {
            'name': 'OLD_NAME',
        }
        p_req = orpo.PolicyUpdateRequestBody(**body)
        request = {
            'identity': 'FAKE',
            'policy': p_req
        }

        req = orpo.PolicyUpdateRequest(**request)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('No property needs an update.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE')
        mock_load.assert_called_once_with(self.ctx, db_policy=x_obj)
        self.assertEqual(0, x_policy.store.call_count)
        self.assertEqual('OLD_NAME', x_policy.name)

    @mock.patch.object(pb.Policy, 'delete')
    @mock.patch.object(po.Policy, 'find')
    def test_policy_delete(self, mock_find, mock_delete):
        x_obj = mock.Mock(id='POLICY_ID')
        mock_find.return_value = x_obj
        mock_delete.return_value = None

        req = orpo.PolicyDeleteRequest(identity='POLICY_ID')
        result = self.eng.policy_delete(self.ctx, req.obj_to_primitive())

        self.assertIsNone(result)
        self.assertEqual('POLICY_ID', req.identity)
        mock_find.assert_called_once_with(self.ctx, 'POLICY_ID')
        mock_delete.assert_called_once_with(self.ctx, 'POLICY_ID')

    @mock.patch.object(po.Policy, 'find')
    def test_policy_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='policy', id='Bogus')

        req = orpo.PolicyDeleteRequest(identity='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_delete, self.ctx,
                               req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The policy 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(pb.Policy, 'delete')
    @mock.patch.object(po.Policy, 'find')
    def test_policy_delete_policy_in_use(self, mock_find, mock_delete):
        x_obj = mock.Mock(id='POLICY_ID')
        mock_find.return_value = x_obj
        err = exc.EResourceBusy(type='policy', id='POLICY_ID')
        mock_delete.side_effect = err

        req = orpo.PolicyDeleteRequest(identity='POLICY_ID')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_delete, self.ctx,
                               req.obj_to_primitive())

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertEqual(_("The policy 'POLICY_ID' cannot be deleted: "
                         "still attached to some clusters."),
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'POLICY_ID')
        mock_delete.assert_called_once_with(self.ctx, 'POLICY_ID')
