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
from senlin.tests.tempest.common import utils


class TestClusterCreateNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterCreateNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.profile_id = profile_id

    @test.attr(type=['negative'])
    @decorators.idempotent_id('498a06eb-8c5f-4d9e-852f-87ac295f1a96')
    def test_cluster_create_cluster_data_not_specified(self):
        # cluster key is missing in request data
        params = {
            'bad': {
                'profile_id': self.profile_id,
                'name': 'test-cluster'
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'clusters', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Request body missing 'cluster' key.",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('3aced30b-ccb2-4e40-90c2-7b6aa205e3d6')
    def test_cluster_create_profile_invalid(self):
        # Invalid profile_id is provided
        params = {
            'cluster': {
                'profile_id': '3aced30b-ccb2-4e40-90c2-7b6aa205e3d6',
                'name': 'test-cluster'
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'clusters', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified profile '3aced30b-ccb2-4e40-90c2-7b6aa205e3d6' "
            "could not be found.", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('61b190bb-ef5a-47b3-acbe-6467fbb44439')
    def test_cluster_create_miss_profile(self):
        # Invalid profile_id is provided
        params = {
            'cluster': {
                'name': 'test-cluster'
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'clusters', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("'profile_id' is a required property",
                         str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('7eaf60c3-f33d-403b-a4ee-0276ae90928c')
    def test_cluster_create_size_constraint_illegal(self):
        # Invalid size limitation is defined: min_size > max_size
        desired_capacity = 2
        min_size = 5
        max_size = 3
        params = {
            'cluster': {
                'profile_id': self.profile_id,
                'desired_capacity': desired_capacity,
                'min_size': min_size,
                'max_size': max_size,
                'name': 'test-cluster'
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'clusters', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("The target capacity (2) is less than the "
                         "specified min_size (5).", str(message))
