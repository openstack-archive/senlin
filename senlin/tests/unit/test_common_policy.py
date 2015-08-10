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

from senlin.common import exception
from senlin.common import policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class PolicyEnforcerTest(base.SenlinTestCase):

    def setUp(self):
        super(PolicyEnforcerTest, self).setUp()

        self.ctx = utils.dummy_context()

    @mock.patch.object(policy, '_get_enforcer')
    def test_enforce(self, enforce):
        mock_enforcer = mock.Mock()
        mock_res = mock.Mock()
        mock_enforcer.enforce.return_value = mock_res
        enforce.return_value = mock_enforcer
        target = mock.Mock()

        res = policy.enforce(self.ctx, 'RULE1', target, do_raise=True)

        self.assertEqual(res, mock_res)
        enforce.assert_called_once_with()
        mock_enforcer.enforce.assert_called_once_with(
            'RULE1', target, self.ctx.to_dict(), True,
            exc=exception.Forbidden)
