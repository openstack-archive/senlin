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


class TestNodeDeleteNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('86bd7425-cddd-457e-a467-78e290aceab9')
    def test_node_delete_not_found(self):
        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.delete_obj, 'nodes',
                               '86bd7425-cddd-457e-a467-78e290aceab9')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The node '86bd7425-cddd-457e-a467-78e290aceab9' could "
            "not be found.", str(message))


class TestNodeDeleteNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeDeleteNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id1 = utils.create_a_node(self, profile_id, name='n-01')
        self.addCleanup(utils.delete_a_node, self, self.node_id1)
        self.node_id2 = utils.create_a_node(self, profile_id, name='n-01')
        self.addCleanup(utils.delete_a_node, self, self.node_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('669203c5-6abd-4e0e-bc66-0bdd588c7b63')
    def test_node_delete_multiple_choice(self):
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.delete_obj,
                               'nodes', 'n-01')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Multiple results found matching the query criteria 'n-01'. "
            "Please be more specific.", str(message))
