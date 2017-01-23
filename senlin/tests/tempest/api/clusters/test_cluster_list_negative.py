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


class TestClusterListNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b18c2b98-0dcf-489f-8245-080db10298d8')
    def test_cluster_list_invalid_params(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'clusters', {'bogus': 'foo'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid parameter 'bogus'", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f6687ce2-288c-42fa-8132-e0faec813129')
    def test_cluster_list_limit_not_int(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'clusters', {'limit': 'not-int'})

        message = ex.resp_body['error']['message']
        self.assertEqual("The value for limit must be an integer: 'not-int'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('32a9f3ad-0284-4fe7-b6e8-d98915637c7f')
    def test_cluster_list_global_project_false(self):
        ex = self.assertRaises(exceptions.Forbidden,
                               self.client.list_objs,
                               'clusters', {'global_project': 'True'})

        message = ex.resp_body['error']['message']
        self.assertEqual("You are not authorized to complete this operation.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('2944d7dd-72d5-4dd0-9f3e-6f5c6ead8b30')
    def test_cluster_list_global_project_not_bool(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'clusters', {'global_project': 'not-bool'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid value 'not-bool' specified for "
                         "'global_project'", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('dc4194f1-6487-47c4-8ad7-da6ca0e88ca2')
    def test_cluster_list_invalid_sort(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'clusters', {'sort': 'bad-sort'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Unsupported sort key 'bad-sort' for 'sort'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('91489f49-686d-470d-9b74-c5e8f46eaae5')
    def test_cluster_list_invalid_marker(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'clusters', {'marker': 'bad-marker'})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The value for marker is not a valid UUID: 'bad-marker'.",
            str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('d13ff32f-aa8a-4704-824a-54d52a160874')
    def test_cluster_list_unsupported_status(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'clusters', {'status': ['bad-status']})

        message = ex.resp_body['error']['message']
        self.assertEqual("Field value ['bad-status'] is invalid",
                         str(message))
