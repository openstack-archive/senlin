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


class TestNodeShowNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f7a2ed7e-bf92-452b-bc76-37a8bbde2169')
    def test_node_show_not_found(self):
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.get_obj, 'nodes',
                               'f7a2ed7e-bf92-452b-bc76-37a8bbde2169')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The node 'f7a2ed7e-bf92-452b-bc76-37a8bbde2169' could "
            "not be found.", str(message))


class TestNodeShowNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeShowNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.node_id1 = utils.create_a_node(self, profile_id, name='n-01')
        self.node_id2 = utils.create_a_node(self, profile_id, name='n-01')
        self.addCleanup(utils.delete_a_node, self, self.node_id1)
        self.addCleanup(utils.delete_a_node, self, self.node_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('49db9d49-76f1-47a7-9bd2-5e67311c453c')
    def test_node_show_multiple_choice(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.get_obj,
                               'nodes', 'n-01')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Multiple results found matching the query criteria 'n-01'. "
            "Please be more specific.", str(message))
