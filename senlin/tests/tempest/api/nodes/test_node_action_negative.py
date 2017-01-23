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


class TestNodeActionNegativeBadRequest(base.BaseSenlinAPITest):

    @decorators.idempotent_id('9ab462e2-ea3a-49f8-bd78-5a056ae80a48')
    def test_no_action_specified(self):
        # No action is specified
        params = {}

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'nodes', 'node_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("No action specified.",
                         str(message))

    @decorators.idempotent_id('9e696e4f-1ec8-45d7-8461-81d275aae81d')
    def test_multiple_action_specified(self):
        # Multiple actions are specified
        params = {
            'check': {},
            'recover': {}
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'nodes', 'node_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Multiple actions specified.",
                         str(message))

    @decorators.idempotent_id('4bd97c71-fbfc-421d-95ff-b3f4a212cc38')
    def test_unrecognized_action(self):
        # Unrecoginized action is specified
        params = {
            'bogus': {}
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'nodes', 'node_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Unrecognized action 'bogus' specified",
                         str(message))
