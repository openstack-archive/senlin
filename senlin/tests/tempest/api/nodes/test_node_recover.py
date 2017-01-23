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
from senlin.tests.tempest.common import utils


class TestNodeRecover(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeRecover, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('217af65a-4029-40ce-a833-74faeac8c1f5')
    def test_node_action_recover(self):
        params = {
            "recover": {
                "operation": "REBUILD"
            }
        }
        # Trigger node action
        res = self.client.trigger_action('nodes', self.node_id, params=params)

        # Verfiy resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestNodeRecoverNegative(base.BaseSenlinAPITest):

    @decorators.idempotent_id('60790d8a-fd9e-47d8-b9e2-c06aa7701c33')
    def test_param_is_not_map(self):
        # Recover action parameter is not a map
        params = {
            'recover': []
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'nodes', 'node_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("The params provided is not a map.",
                         str(message))

    @decorators.idempotent_id('694e59ce-551e-4e77-a684-e77781583e12')
    def test_node_not_found(self):
        params = {
            'recover': {}
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action,
                               'nodes', '694e59ce-551e-4e77-a684-e77781583e12',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The node '694e59ce-551e-4e77-a684-e77781583e12' could "
            "not be found.", str(message))
