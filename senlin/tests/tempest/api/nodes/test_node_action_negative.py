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

from senlin.tests.tempest.api import base


class TestNodeActionNegativeBadRequest(base.BaseSenlinTest):

    @decorators.idempotent_id('9ab462e2-ea3a-49f8-bd78-5a056ae80a48')
    def test_node_action_no_action_specified(self):
        # No action is specified
        params = {}

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'nodes', 'node_id', params)

    @decorators.idempotent_id('9e696e4f-1ec8-45d7-8461-81d275aae81d')
    def test_node_action_multiple_action_specified(self):
        # Multiple actions are specified
        params = {
            'check': {},
            'recover': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'nodes', 'node_id', params)

    @decorators.idempotent_id('4bd97c71-fbfc-421d-95ff-b3f4a212cc38')
    def test_node_action_unrecognized_action(self):
        # Unrecoginized action is specified
        params = {
            'bogus': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'nodes', 'node_id', params)

    @decorators.idempotent_id('723ea351-1bcb-4d45-bfe7-35c656d29761')
    def test_node_action_check_param_is_not_map(self):
        # Check action parameter is not a map
        params = {
            'check': []
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'nodes', 'node_id', params)

    @decorators.idempotent_id('60790d8a-fd9e-47d8-b9e2-c06aa7701c33')
    def test_node_action_recover_param_is_not_map(self):
        # Recover action parameter is not a map
        params = {
            'recover': []
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'nodes', 'node_id', params)


class TestNodeActionNegativeNotFound(base.BaseSenlinTest):

    @decorators.idempotent_id('90c46123-f992-4833-859a-46f6d2ccd8e9')
    def test_node_action_node_not_found(self):
        params = {
            'check': {}
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action,
                          'nodes', '90c46123-f992-4833-859a-46f6d2ccd8e9',
                          params)
