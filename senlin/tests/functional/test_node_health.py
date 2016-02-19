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

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestNodeHealth(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestNodeHealth, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestNodeHealth, self).tearDown()

    def test_node_check_recover(self):
        # Create a node
        node1 = test_api.create_node(self.client,
                                     test_utils.random_name('node1'),
                                     self.profile['id'],
                                     role='master')
        node1 = test_utils.wait_for_status(test_api.get_node, self.client,
                                           node1['id'], 'ACTIVE')

        # Check node health status
        action_id = test_api.action_node(self.client, node1['id'], 'check')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')
        node1 = test_api.get_node(self.client, node1['id'])
        self.assertEqual('ACTIVE', node1['status'])

        # Perform node recovering operation
        action_id = test_api.action_node(self.client, node1['id'], 'recover')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')
        action_id = test_api.action_node(self.client, node1['id'], 'recover',
                                         {'operation': 'REBUILD'})
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Delete node
        test_api.delete_node(self.client, node1['id'])
        test_utils.wait_for_delete(test_api.get_node, self.client, node1['id'])
