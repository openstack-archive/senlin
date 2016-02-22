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

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestClusterHealth(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestClusterHealth, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestClusterHealth, self).tearDown()

    def test_cluster_check_recover(self):
        # Create cluster
        desired_capacity = 3
        min_size = 2
        max_size = 5
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Check cluster health status
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'check')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])

        # Perform cluster recovering operation
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'recover')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'recover',
                                            {'operation': 'REBUILD'})
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])
