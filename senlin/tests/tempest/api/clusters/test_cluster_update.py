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


class TestClusterUpdate(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterUpdate, self).setUp()

        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('ba8514b2-b3c4-47a4-9176-7fe9bb2781ae')
    def test_cluster_update_basic_properties(self):
        # Update basic properties of cluster
        params = {
            'cluster': {
                'timeout': 240,
                'metadata': {'k2': 'v2'},
                'name': 'cluster_new_name'
            }
        }
        res = self.client.update_obj('clusters', self.cluster_id, params)

        # Verify resp of cluster update API
        self.assertEqual(202, res['status'])
        self.assertIsNotNone(res['body'])
        self.assertIn('actions', res['location'])
        cluster = res['body']
        for key in ['created_at', 'data', 'domain', 'id', 'init_at',
                    'metadata', 'name', 'nodes', 'policies', 'profile_id',
                    'profile_name', 'project', 'status', 'status_reason',
                    'timeout', 'updated_at', 'user']:
            self.assertIn(key, cluster)

        # Wait for cluster update to be done before moving on
        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')
