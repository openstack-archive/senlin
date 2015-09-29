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

from oslo_log import log as logging

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils

LOG = logging.getLogger(__name__)


class TestClusterBasic(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestClusterBasic, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(self.client, 'test-profile',
                                               test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestClusterBasic, self).tearDown()

    def test_get_clusters(self):
        # Check that listing clusters works.
        clusters = test_api.list_clusters(self.client)
        self.assertEqual([], clusters)

    def test_cluster_create_delete(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster = test_api.create_cluster(self.client, 'test-cluster',
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)

        # Wait and verify cluster creation result
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')
        self.assertEqual('test-cluster', cluster['name'])
        self.assertEqual(desired_capacity, cluster['desired_capacity'])
        self.assertEqual(min_size, cluster['min_size'])
        self.assertEqual(max_size, cluster['max_size'])
        self.assertEqual(desired_capacity, len(cluster['nodes']))

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_utils.wait_for_status(test_api.get_cluster, self.client,
                                   cluster['id'], 'DELETED',
                                   ignore_missing=True)
