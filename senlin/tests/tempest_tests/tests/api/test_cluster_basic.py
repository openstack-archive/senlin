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

from senlin.tests.tempest_tests.tests.api import base
from senlin.tests.tempest_tests.tests.common import constants


class TestClusterBasic(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterBasic, cls).resource_setup()
        # Create profile
        cls.profile = cls.client.create_profile(
            constants.spec_nova_server)

    @classmethod
    def resource_cleanup(cls):
        # Delete profile
        cls.client.delete_profile(cls.profile['id'])
        super(TestClusterBasic, cls).resource_cleanup()

    @decorators.idempotent_id('61cbe340-937a-40d5-9d2f-067f2c7cafcc')
    def test_cluster_create_delete(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster = self._create_cluster(self.profile['id'], desired_capacity,
                                       min_size=min_size, max_size=max_size)

        # Create cluster without nodes
        desired_capacity = 0
        cluster2 = self._create_cluster(self.profile['id'], desired_capacity)

        # List clusters
        clusters = self.client.list_cluster()
        clusters_id = [c['id'] for c in clusters]
        self.assertIn(cluster['id'], clusters_id)
        self.assertIn(cluster2['id'], clusters_id)

        # Delete cluster
        self._delete_cluster(cluster['id'])
        self._delete_cluster(cluster2['id'])


class TestClusterUpdate(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterUpdate, cls).resource_setup()
        # Create profile
        cls.profile = cls.client.create_profile(
            constants.spec_nova_server)

    @classmethod
    def resource_cleanup(cls):
        # Delete profile
        cls.client.delete_profile(cls.profile['id'])
        super(TestClusterUpdate, cls).resource_cleanup()

    @decorators.idempotent_id('ba8514b2-b3c4-47a4-9176-7fe9bb2781ae')
    def test_cluster_update_basic_properties(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster = self._create_cluster(
            self.profile['id'], desired_capacity,
            min_size=min_size, max_size=max_size, metadata={'k1': 'v1'},
            timeout=120)

        # Update basic properties of cluster
        action_id = self.client.update_cluster(
            cluster['id'], name='cluster_new_name', metadata={'k2': 'v2'},
            timeout=240)
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify update result
        cluster = self.client.show_cluster(cluster['id'])
        self.assertEqual('cluster_new_name', cluster['name'])
        self.assertEqual({'k2': 'v2'}, cluster['metadata'])
        self.assertEqual(240, cluster['timeout'])

        # Delete cluster
        self._delete_cluster(cluster['id'])

    @decorators.idempotent_id('abff7891-21af-4c37-a8df-5bc7379ce349')
    def test_cluster_update_profile(self):
        spec_nova_server = copy.deepcopy(constants.spec_nova_server)
        spec_nova_server['properties']['flavor'] = 'new_flavor'
        spec_nova_server['properties']['image'] = 'new_image'
        new_profile = self.client.create_profile(spec_nova_server)

        # Create cluster with original profile
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster = self._create_cluster(
            self.profile['id'], desired_capacity,
            min_size=min_size, max_size=max_size)

        # Update cluster with new profile
        action_id = self.client.update_cluster(cluster['id'],
                                               profile_id=new_profile['id'])
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify update result
        cluster = self.client.show_cluster(cluster['id'])
        self.assertEqual(new_profile['id'], cluster['profile_id'])
        nodes = cluster['nodes']
        for n in nodes:
            node = self.client.show_node(n)
            self.assertEqual(new_profile['id'], node['profile_id'])

        # Delete cluster
        self._delete_cluster(cluster['id'])
        # Delete new profile
        self.client.delete_profile(new_profile['id'])
