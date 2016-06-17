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
from tempest.lib import exceptions
from tempest import test

from senlin.tests.tempest.api import base


class TestPolicyListNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b936b936-f891-4389-bbeb-f81b7dc3c688')
    def test_policy_list_invalid_params(self):
        self.assertRaises(exceptions.BadRequest,
                          self.client.list_objs,
                          'policies', {'bogus': 'foo'})
