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


class TestNodeCheck(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeCheck, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('ae124bfe-9fcf-4e87-91b7-319102efbdcc')
    def test_check(self):
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


class TestNodeCheckNegative(base.BaseSenlinAPITest):

    @decorators.idempotent_id('723ea351-1bcb-4d45-bfe7-35c656d29761')
    def test_param_is_not_map(self):
        # Check action parameter is not a map
        params = {
            'check': []
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'nodes', 'node_id', params)

    @decorators.idempotent_id('90c46123-f992-4833-859a-46f6d2ccd8e9')
    def test_node_not_found(self):
        params = {
            'check': {}
        }

        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action,
                          'nodes', '90c46123-f992-4833-859a-46f6d2ccd8e9',
                          params)
