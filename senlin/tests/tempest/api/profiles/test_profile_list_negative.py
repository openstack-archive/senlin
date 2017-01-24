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


class TestProfileListNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b936b936-f891-4389-bbeb-f81b7dc3c688')
    def test_profile_list_invalid_params(self):
        self.assertRaises(exceptions.BadRequest,
                          self.client.list_objs,
                          'profiles', {'bogus': 'foo'})

    @test.attr(type=['negative'])
    @decorators.idempotent_id('04ce3766-acf9-4549-91c8-e6ffdf7bafbd')
    def test_profile_list_limit_not_int(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'profiles', {'limit': 'not-int'})

        message = ex.resp_body['error']['message']
        self.assertEqual("The value for limit must be an integer: 'not-int'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('cfd50d13-5ed8-48d9-b03f-95480ba06fad')
    def test_profile_list_global_project_false(self):
        ex = self.assertRaises(exceptions.Forbidden,
                               self.client.list_objs,
                               'profiles', {'global_project': 'True'})

        message = ex.resp_body['error']['message']
        self.assertEqual("You are not authorized to complete this operation.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('ab477cf8-6c37-4762-bd85-d55b46444d8f')
    def test_profile_list_global_project_not_bool(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'profiles', {'global_project': 'not-bool'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Invalid value 'not-bool' specified for "
                         "'global_project'", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f5bd7807-2b3e-43b2-8ed6-7bdb5e9af46b')
    def test_profile_list_invalid_sort(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'profiles', {'sort': 'bad-sort'})

        message = ex.resp_body['error']['message']
        self.assertEqual("Unsupported sort key 'bad-sort' for 'sort'.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('077f39f0-bb2a-4de8-9568-2ed49e99b720')
    def test_profile_list_invalid_marker(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.list_objs,
                               'profiles', {'marker': 'bad-marker'})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The value for marker is not a valid UUID: 'bad-marker'.",
            str(message))
