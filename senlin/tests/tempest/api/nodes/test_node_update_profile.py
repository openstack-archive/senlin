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

from senlin.tests.tempest.api import base
from senlin.tests.tempest.api import utils
from senlin.tests.tempest.common import constants


class TestNodeUpdateProfile(base.BaseSenlinTest):

    def setUp(self):
        super(TestNodeUpdateProfile, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        new_spec = copy.deepcopy(constants.spec_nova_server)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_spec['properties']['image'] = 'new_image'
        self.new_profile_id = utils.create_a_profile(self, new_spec)
        self.addCleanup(utils.delete_a_profile, self, self.new_profile_id)

        self.node_id = self.create_test_node(profile_id, name='node1',
                                             metadata={'k1': 'v1'},
                                             role='member')['id']
        self.addCleanup(self.delete_test_node, self.node_id)

    @decorators.idempotent_id('de9465f2-95b4-41ce-81f5-b092967cb2b8')
    def test_node_update_profile(self):
        # Update node with new profile
        params = {
            'node': {
                'profile_id': self.new_profile_id
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
