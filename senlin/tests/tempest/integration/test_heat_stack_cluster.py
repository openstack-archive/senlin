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

from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils
from senlin.tests.tempest.integration import base


class TestHeatStackCluster(base.BaseSenlinIntegrationTest):

    def setUp(self):
        super(TestHeatStackCluster, self).setUp()
        self.profile_id = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)

    @decorators.attr(type=['integration'])
    @decorators.idempotent_id('c9ba5700-f384-4376-b61b-e2b108ab3a16')
    def test_cluster_create_delete(self):
        # Create a cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        metadata = {'k1': 'v1'}
        timeout = 300
        cluster_id = utils.create_a_cluster(
            self, self.profile_id, desired_capacity, min_size, max_size,
            timeout, metadata)

        # Verify creation result
        cluster = utils.get_a_cluster(self, cluster_id)
        self.assertIsNotNone(cluster)
        self.assertEqual(desired_capacity, cluster['desired_capacity'])
        self.assertEqual(desired_capacity, len(cluster['nodes']))
        for nid in cluster['nodes']:
            node = utils.get_a_node(self, nid)
            self.assertEqual('ACTIVE', node['status'])
            self.assertEqual(cluster_id, node['cluster_id'])

        # Delete cluster
        utils.delete_a_cluster(self, cluster_id)
