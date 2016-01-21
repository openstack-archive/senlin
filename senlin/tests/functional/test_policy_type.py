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

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base


class TestPolicyType(base.SenlinFunctionalTest):

    def test_get_policy_types(self):
        # Check that listing policy types works.
        policy_types = test_api.list_policy_types(self.client)
        policy_names = [p['name'] for p in policy_types]
        self.assertIn('senlin.policy.deletion-1.0', policy_names)
        self.assertIn('senlin.policy.scaling-1.0', policy_names)
