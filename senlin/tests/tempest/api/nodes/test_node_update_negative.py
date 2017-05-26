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

import copy
from tempest.lib import decorators
from tempest.lib import exceptions

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils


class TestNodeUpdateNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('608addc9-cbbe-45cd-a00a-495cae7db400')
    def test_node_update_node_not_found(self):
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.update_obj, 'nodes',
                               '608addc9-cbbe-45cd-a00a-495cae7db400',
                               {'node': {'name': 'new-name'}})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The node '608addc9-cbbe-45cd-a00a-495cae7db400' could "
            "not be found.", str(message))


class TestNodeUpdateNegativeProfileNotFound(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeUpdateNegativeProfileNotFound, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a node
        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('3243dd63-1008-4181-849a-0058af975800')
    def test_node_update_profile_not_found(self):
        # Provided profile can not be found
        params = {
            'node': {
                'profile_id': '3243dd63-1008-4181-849a-0058af975800',
            }
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'nodes', self.node_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified profile '3243dd63-1008-4181-849a-0058af975800' "
            "could not be found.", str(message))


class TestNodeUpdateNegativeProfileMultichoices(base.BaseSenlinAPITest):
    def setUp(self):
        super(TestNodeUpdateNegativeProfileMultichoices, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a node
        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)
        # Create two new profiles of the same type with the same name
        new_spec = copy.deepcopy(constants.spec_nova_server)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile_id1 = utils.create_a_profile(self, new_spec, name='p-nova')
        new_profile_id2 = utils.create_a_profile(self, new_spec, name='p-nova')
        self.addCleanup(utils.delete_a_profile, self, new_profile_id1)
        self.addCleanup(utils.delete_a_profile, self, new_profile_id2)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('0d73eff6-1916-43e1-9518-31820fcfe01f')
    def test_node_update_profile_multichoices(self):
        # Multiple profiles are found for given name
        params = {
            'node': {
                'profile_id': 'p-nova',
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'nodes', self.node_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Multiple results found matching the query criteria 'p-nova'. "
            "Please be more specific.", str(message))


class TestNodeUpdateNegativeProfileTypeUnmatch(base.BaseSenlinAPITest):
    def setUp(self):
        super(TestNodeUpdateNegativeProfileTypeUnmatch, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a node
        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)
        # Create a new profile of different type
        self.new_profile_id = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.new_profile_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ec5821d8-142e-4fff-a998-81428ecc239c')
    def test_node_update_profile_type_unmatch(self):
        # New profile type is different from original cone
        params = {
            'node': {
                'profile_id': self.new_profile_id,
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'nodes', self.node_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Cannot update a node to a different profile type, "
            "operation aborted.", str(message))


class TestNodeUpdateNegativeNoPropertyUpdated(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeUpdateNegativeNoPropertyUpdated, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a node
        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ed6f385d-780b-4562-928d-3e00f27550d2')
    def test_node_update_no_property_updated(self):
        # Provided profile can not be found
        params = {
            'node': {}
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'nodes', self.node_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual("No property needs an update.",
                         str(message))
