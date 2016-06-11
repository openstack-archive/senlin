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
from senlin.tests.tempest.api import utils
from senlin.tests.tempest.common import constants


class TestNodeCreateNegativeBadRequest(base.BaseSenlinTest):

    def setUp(self):
        super(TestNodeCreateNegativeBadRequest, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.profile_id2 = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id2)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('cbe7827a-60ca-42c0-99d2-38167cb4f46d')
    def test_node_create_profile_invalid(self):
        # Invalid profile_id is provided
        params = {
            'node': {
                'profile_id': 'cbe7827a-60ca-42c0-99d2-38167cb4f46d',
                'cluster_id': self.cluster_id,
                'metadata': {'k1': 'v1'},
                'role': 'member',
                'name': 'test-node'
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'nodes', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('960cd427-2487-4c83-b679-1b5e1f9dd985')
    def test_node_create_cluster_invalid(self):
        # Invalid cluster_id is provided
        params = {
            'node': {
                'profile_id': self.profile_id,
                'cluster_id': '960cd427-2487-4c83-b679-1b5e1f9dd985',
                'metadata': {'k1': 'v1'},
                'role': 'member',
                'name': 'test-node'
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'nodes', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('8ddf45a5-f45f-4cc8-813d-2bff75498576')
    def test_node_create_profile_type_unmatch(self):
        # Node profile type is different from cluster profile type
        params = {
            'node': {
                'profile_id': self.profile_id2,
                'cluster_id': self.cluster_id,
                'metadata': {'k1': 'v1'},
                'role': 'member',
                'name': 'test-node'
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'nodes', params)
