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
from senlin.tests.tempest.common import constants


class TestNodeCreate(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestNodeCreate, cls).resource_setup()
        cls.profile = cls.create_profile(constants.spec_nova_server)
        cls.cluster = utils.create_a_cluster(cls, cls.profile['id'])

    @classmethod
    def resource_cleanup(cls):
        # Delete test cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestNodeCreate, cls).resource_cleanup()

    @decorators.idempotent_id('14d06753-7f0a-4ad2-84be-37fce7114a8f')
    def test_node_create_all_attrs_defined(self):
        params = {
            'node': {
                'profile_id': self.profile['id'],
                'cluster_id': self.cluster['id'],
                'metadata': {'k1': 'v1'},
                'role': 'member',
                'name': 'test-node'
            }
        }
        res = self.client.create_obj('nodes', params)

        # Verify resp of node create API
        self.assertEqual(202, res['status'])
        self.assertIsNotNone(res['body'])
        self.assertIn('actions', res['location'])
        node = res['body']
        for key in ['cluster_id', 'created_at', 'data', 'domain', 'id',
                    'index', 'init_at', 'metadata', 'name', 'physical_id',
                    'profile_id', 'profile_name', 'project', 'role',
                    'status', 'status_reason', 'updated_at', 'user']:
            self.assertIn(key, node)
        self.assertIn('test-node', node['name'])
        self.assertEqual(self.profile['id'], node['profile_id'])
        self.assertEqual(self.cluster['id'], node['cluster_id'])
        self.assertEqual({'k1': 'v1'}, node['metadata'])
        self.assertEqual('member', node['role'])
        self.assertEqual('test-node', node['name'])

        # Wait node to be active before moving on
        action_id = res['location'].split('/actions/')[1]
        self.wait_for_status('actions', action_id, 'SUCCEEDED')
