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
from senlin.tests.tempest.api import utils


class TestNodeUpdate(base.BaseSenlinTest):

    def setUp(self):
        super(TestNodeUpdate, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id = utils.create_a_node(self, profile_id, name='node1',
                                           metadata={'k1': 'v1'},
                                           role='member')
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @decorators.idempotent_id('bd8a39bf-eee0-4056-aec0-0d8f8706efea')
    def test_node_update_basic_properties(self):
        # Update basic properties of node
        params = {
            'node': {
                'name': 'node_new_name',
                'role': 'admin',
                'metadata': {'k2': 'v2'}
            }
        }
        res = self.client.update_obj('nodes', self.node_id, params)

        # Verify resp of node update API
        self.assertEqual(202, res['status'])
        self.assertIsNotNone(res['body'])
        self.assertIn('actions', res['location'])
        node = res['body']
        for key in ['cluster_id', 'created_at', 'data', 'domain', 'id',
                    'index', 'init_at', 'metadata', 'name', 'physical_id',
                    'profile_id', 'profile_name', 'project', 'role', 'status',
                    'status_reason', 'updated_at', 'user']:
            self.assertIn(key, node)

        # Wait for node update to be done before moving on
        action_id = res['location'].split('/actions/')[1]
        self.wait_for_status('actions', action_id, 'SUCCEEDED')
