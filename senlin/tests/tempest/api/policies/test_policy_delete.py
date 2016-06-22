# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import decorators

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestPolicyDelete(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestPolicyDelete, self).setUp()
        self.policy_id = utils.create_a_policy(self)

    @decorators.idempotent_id('b707e4e3-3d42-4a9f-9a09-3e330959b498')
    def test_policy_delete(self):
        # Verify resp of policy delete API
        res = self.client.delete_obj('policies', self.policy_id)
        self.assertEqual(204, res['status'])
        self.assertIsNone(res['body'])
