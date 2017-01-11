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
from oslo_messaging.rpc import dispatcher as rpc
import six

from senlin.common import exception as exc
from senlin.engine import environment
from senlin.engine import service
from senlin.objects.requests import policy_type as orpt
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class PolicyTypeTest(base.SenlinTestCase):

    def setUp(self):
        super(PolicyTypeTest, self).setUp()
        self.ctx = utils.dummy_context(project='policy_type_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(environment, 'global_env')
    def test_policy_type_list(self, mock_env):
        x_env = mock.Mock()
        x_env.get_policy_types.return_value = [{'foo': 'bar'}]
        mock_env.return_value = x_env

        req = orpt.PolicyTypeListRequest()
        types = self.eng.policy_type_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([{'foo': 'bar'}], types)
        mock_env.assert_called_once_with()
        x_env.get_policy_types.assert_called_once_with()

    @mock.patch.object(environment, 'global_env')
    def test_policy_type_get(self, mock_env):
        x_env = mock.Mock()
        x_policy_type = mock.Mock()
        x_policy_type.get_schema.return_value = {'foo': 'bar'}
        x_policy_type.VERSIONS = {'1.0': [{'status': 'supported',
                                           'since': '2016.04'}]}
        x_env.get_policy.return_value = x_policy_type
        mock_env.return_value = x_env

        req = orpt.PolicyTypeGetRequest(type_name='FAKE_TYPE')
        result = self.eng.policy_type_get(self.ctx, req.obj_to_primitive())

        self.assertEqual(
            {
                'name': 'FAKE_TYPE',
                'schema': {'foo': 'bar'},
                'support_status': {'1.0': [{'status': 'supported',
                                            'since': '2016.04'}]}
            },
            result)
        mock_env.assert_called_once_with()
        x_env.get_policy.assert_called_once_with('FAKE_TYPE')
        x_policy_type.get_schema.assert_called_once_with()

    @mock.patch.object(environment, 'global_env')
    def test_policy_type_get_nonexist(self, mock_env):
        x_env = mock.Mock()
        err = exc.ResourceNotFound(type='policy_type', id='FAKE_TYPE')
        x_env.get_policy.side_effect = err
        mock_env.return_value = x_env

        req = orpt.PolicyTypeGetRequest(type_name='FAKE_TYPE')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_type_get,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The policy_type 'FAKE_TYPE' could not be "
                         "found.", six.text_type(ex.exc_info[1]))
        mock_env.assert_called_once_with()
        x_env.get_policy.assert_called_once_with('FAKE_TYPE')
