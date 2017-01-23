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


class TestEventListNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('ddbc0735-869c-4da4-ae1d-ec67984cca46')
    def test_event_list_invalid_params(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'bogus': 'foo'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid parameter bogus", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('fc3a5097-d332-42e5-8fb8-682cb248d9ad')
    def test_event_list_limit_not_int(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'limit': 'not-int'})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The value for limit must be an integer: 'not-int'.",
            str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('da0871d7-9eb4-4349-b1db-0287d444ff58')
    def test_event_list_global_project_false(self):
        ex = self.assertRaises(exceptions.Forbidden,
                               self.client.list_objs,
                               'events', {'global_project': 'True'})

        message = ex.resp_body['error']['message']
        self.assertEqual("You are not authorized to complete this operation.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('bccbbec0-08e5-4594-8fa4-c874d4359033')
    def test_event_list_global_project_not_bool(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'global_project': 'not-bool'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid value 'not-bool' specified for "
                         "'global_project'", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('84d2d883-9402-4735-8be6-b726b0e0edbd')
    def test_event_list_invalid_sort(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'sort': 'bad-sort'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Unsupported sort key 'bad-sort' for 'sort'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('c53500fc-0504-4f0f-b540-1f39e524db53')
    def test_event_list_invalid_marker(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'marker': 'bad-marker'})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The value for marker is not a valid UUID: 'bad-marker'.",
            str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('72e0fd48-2dc7-47ce-abad-299e508fabd4')
    def test_event_list_unsupported_level(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'level': ['bad-level']})

        message = ex.resp_body['error']['message']
        self.assertEqual("Field value ['bad-level'] is invalid",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('72e0fd48-2dc7-47ce-abad-299e508fabd4')
    def test_event_list_unsupported_action(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'events', {'action': ['bad-action']})

        message = ex.resp_body['error']['message']
        self.assertEqual("Field value ['bad-action'] is invalid",
                         str(message))
