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


class TestNodeList(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestNodeList, cls).resource_setup()
        cls.profile = utils.create_a_profile(cls)
        cls.node = cls.create_test_node(cls.profile['id'])

    @classmethod
    def resource_cleanup(cls):
        # Delete test node
        cls.delete_test_node(cls.node['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestNodeList, cls).resource_cleanup()

    @decorators.idempotent_id('cd086dcb-7509-4125-adfc-6beb63b10d0a')
    def test_node_list(self):
        res = self.client.list_objs('nodes')

        # Verify resp of node list API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        nodes = res['body']
        node_ids = []
        for node in nodes:
            for key in ['cluster_id', 'created_at', 'data', 'domain',
                        'id', 'index', 'init_at', 'metadata', 'name',
                        'physical_id', 'profile_id', 'profile_name',
                        'project', 'role', 'status', 'status_reason',
                        'updated_at', 'user']:
                self.assertIn(key, node)
            node_ids.append(node['id'])
        self.assertIn(self.node['id'], node_ids)
