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


class TestNodeShow(base.BaseSenlinTest):

    def setUp(self):
        super(TestNodeShow, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.node_id = self.create_test_node(profile_id)['id']
        self.addCleanup(self.delete_test_node, self.node_id)

    @decorators.idempotent_id('302372e8-efa2-4348-88dd-8a1829e5e26c')
    def test_node_show(self):
        res = self.client.get_obj('nodes', self.node_id)

        # Verify resp of node get API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        node = res['body']
        for key in ['cluster_id', 'created_at', 'data', 'domain',
                    'id', 'index', 'init_at', 'metadata', 'name',
                    'physical_id', 'profile_id', 'profile_name',
                    'project', 'role', 'status', 'status_reason',
                    'updated_at', 'user']:
            self.assertIn(key, node)
