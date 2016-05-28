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


class TestClusterUpdate(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterUpdate, cls).resource_setup()
        cls.profile_id = utils.create_a_profile(cls)
        cls.cluster_id = utils.create_a_cluster(cls, cls.profile_id)

    @classmethod
    def resource_cleanup(cls):
        utils.delete_a_cluster(cls, cls.cluster_id)
        utils.delete_a_profile(cls, cls.profile_id)
        super(TestClusterUpdate, cls).resource_cleanup()

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
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify cluster update result
        cluster = self.get_test_cluster(cluster['id'])
        self.assertEqual('cluster_new_name', cluster['name'])
        self.assertEqual({'k2': 'v2'}, cluster['metadata'])
        self.assertEqual(240, cluster['timeout'])

    @decorators.idempotent_id('abff7891-21af-4c37-a8df-5bc7379ce349')
    def test_cluster_update_profile(self):
        # Create a new profile
        spec_nova_server = copy.deepcopy(constants.spec_nova_server)
        spec_nova_server['properties']['flavor'] = 'new_flavor'
        spec_nova_server['properties']['image'] = 'new_image'
        new_profile_id = utils.create_a_profile(self, spec_nova_server)

        # Update cluster with new profile
        params = {
            'cluster': {
                'profile_id': new_profile_id
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
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify cluster update result
        cluster = self.get_test_cluster(cluster['id'])
        self.assertEqual(new_profile_id, cluster['profile_id'])
