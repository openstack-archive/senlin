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
from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils


class TestNodeCreateNegativeBadRequest(base.BaseSenlinAPITest):

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
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified profile 'cbe7827a-60ca-42c0-99d2-38167cb4f46d' "
            "could not be found.", str(message))

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
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified cluster '960cd427-2487-4c83-b679-1b5e1f9dd985' "
            "could not be found.", str(message))

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
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Node and cluster have different profile type, "
            "operation aborted.", str(message))


class TestNodeCreateNegativeInvalidRequest(base.BaseSenlinAPITest):

    @decorators.idempotent_id('b109aa66-2a54-493e-8a07-1ea6f20e17ce')
    def test_node_create_empty_param(self):
        params = {}

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Request body missing 'node' key.",
                         str(message))

    @decorators.idempotent_id('080946ef-a9e0-46b4-add7-da70d05391d6')
    def test_node_create_unsupported_param(self):
        params = {
            'node': {
                'profile_id': 'fake_profile',
                'name': 'fake_name',
                'boo': 'foo'
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Additional properties are not allowed (u'boo' "
            "was unexpected)", str(message))

    @decorators.idempotent_id('0ac2a77e-082c-47d2-8156-92e7fb43689c')
    def test_node_create_miss_name(self):
        params = {
            'node': {
                'profile_id': 'fake_profile',
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("'name' is a required property",
                         str(message))

    @decorators.idempotent_id('39eb68ed-7808-4a73-85b1-83faca124546')
    def test_node_create_miss_profile(self):
        params = {
            'node': {
                'name': 'fake',
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.create_obj,
                               'nodes', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("'profile_id' is a required property",
                         str(message))
