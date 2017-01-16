# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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


class TestClusterPolicyListNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('7f23de64-60c4-456e-9e24-db86ac89480c')
    def test_cluster_policy_list_invalid_params(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_cluster_policies,
                               '7f23de64-60c4-456e-9e24-db86ac89480c',
                               {'bogus': 'foo'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid parameter bogus", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0259cbac-0fb3-480b-8f23-1ec59616f3af')
    def test_cluster_policy_list_cluster_not_found(self):
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.list_cluster_policies,
                               '0259cbac-0fb3-480b-8f23-1ec59616f3af')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster (0259cbac-0fb3-480b-8f23-1ec59616f3af) "
            "could not be found.", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('958c6fd2-a647-4b5a-8133-8b4232267b40')
    def test_cluster_policy_list_invalid_sort(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_cluster_policies,
                               '958c6fd2-a647-4b5a-8133-8b4232267b40',
                               {'sort': 'bad-sort'})

        message = ex.resp_body['error']['message']
        self.assertEqual("unsupported sort key 'bad-sort' for 'sort'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0e59c1c7-7477-45ee-8f12-7e5b87373bf7')
    def test_cluster_policy_list_enabled_not_bool(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_cluster_policies,
                               '0e59c1c7-7477-45ee-8f12-7e5b87373bf7',
                               {'enabled': 'bad-enabled'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid value 'bad-enabled' specified for 'enabled'",
                         str(message))
