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


class TestNodeDelete(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestNodeDelete, cls).resource_setup()
        cls.profile = utils.create_a_profile(cls)
        cls.node = cls.create_test_node(cls.profile['id'], name='node1',
                                        metadata={'k1': 'v1'}, role='member')

    @classmethod
    def resource_cleanup(cls):
        # Delete test node
        cls.delete_test_node(cls.node['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestNodeDelete, cls).resource_cleanup()

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
        res = self.client.update_obj('nodes', self.node['id'], params)

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

        # Verify node update result
        node = self.get_test_node(node['id'])
        self.assertEqual('node_new_name', node['name'])
        self.assertEqual({'k2': 'v2'}, node['metadata'])
        self.assertEqual('admin', node['role'])

    @decorators.idempotent_id('de9465f2-95b4-41ce-81f5-b092967cb2b8')
    def test_node_update_profile(self):
        # Create a new profile
        spec_nova_server = copy.deepcopy(constants.spec_nova_server)
        spec_nova_server['properties']['flavor'] = 'new_flavor'
        spec_nova_server['properties']['image'] = 'new_image'
        new_profile = utils.create_a_profile(self, spec_nova_server)

        # Update node with new profile
        params = {
            'node': {
                'profile_id': new_profile['id']
            }
        }
        res = self.client.update_obj('nodes', self.node['id'], params)

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

        # Verify node update result
        node = self.get_test_node(node['id'])
        self.assertEqual(new_profile['id'], node['profile_id'])
