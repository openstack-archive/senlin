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

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestNodeActionCheck(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeActionCheck, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('ae124bfe-9fcf-4e87-91b7-319102efbdcc')
    def test_node_action_check(self):
        params = {
            'check': {
            }
        }
        # Trigger node action
        res = self.client.trigger_action('nodes', self.node_id, params=params)

        # Verfiy resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestNodeActionRecover(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeActionRecover, self).setUp()
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
