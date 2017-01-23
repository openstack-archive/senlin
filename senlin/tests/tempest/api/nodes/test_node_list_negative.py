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


class TestNodeListNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d27172ca-00ad-465d-b854-4fac7f1edc13')
    def test_node_list_invalid_params(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'bogus': 'foo'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid parameter bogus", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('bb668501-b48e-4355-8bf0-eb9b2e2a89fd')
    def test_node_list_cluster_not_found(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'cluster_id': 'fake'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Cannot find the given cluster: fake.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('2e6677ad-8f0d-410e-bd30-baea7882c6fd')
    def test_node_list_limit_negative(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'limit': '-5'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Value must be >= 0 for field 'limit'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('57e4fd0c-35ae-4270-a9a2-01e9f89fdaf3')
    def test_node_list_limit_not_int(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'limit': 'not-int'})

        message = ex.resp_body['error']['message']
        self.assertEqual("The value for limit must be an integer: 'not-int'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('733b1812-0ce6-4b21-ab07-3e4dfda10273')
    def test_node_list_global_project_false(self):
        ex = self.assertRaises(exceptions.Forbidden,
                               self.client.list_objs,
                               'nodes', {'global_project': 'True'})

        message = ex.resp_body['error']['message']
        self.assertEqual("You are not authorized to complete this operation.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('a9936950-0127-475f-bee6-700a553a7465')
    def test_node_list_global_project_not_bool(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'global_project': 'not-bool'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid value 'not-bool' specified for "
                         "'global_project'", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('688270f0-9f08-43fe-8ff3-4598aa637493')
    def test_node_list_invalid_sort(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'sort': 'bad-sort'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Unsupported sort key 'bad-sort' for 'sort'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0ae75360-4445-4c20-8d26-55a86770ad21')
    def test_node_list_invalid_marker(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'marker': 'bad-marker'})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The value for marker is not a valid UUID: 'bad-marker'.",
            str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d8d7dd1e-afd8-4921-83b2-c4ce73b1cb22')
    def test_node_list_unsupported_status(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'nodes', {'status': ['bad-status']})

        message = ex.resp_body['error']['message']
        self.assertEqual("Field value ['bad-status'] is invalid",
                         str(message))
