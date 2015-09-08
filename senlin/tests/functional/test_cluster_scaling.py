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

from senlin.common.i18n import _
from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils

LOG = logging.getLogger(__name__)


class TestCluster(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestCluster, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(self.client, 'test-profile',
                                               test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestCluster, self).tearDown()

    def test_cluster_scale_in_out(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 5
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

        # Scale out cluster without params
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, len(cluster['nodes']))

        # Scale out with count set to 2
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out', {'count': 2})
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, len(cluster['nodes']))

        # Keep scaling out and break the size constraint
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_out')

        # Wait for cluster scale out action failed
        action = test_utils.wait_for_status(test_api.get_action, self.client,
                                            action_id, 'FAILED')
        reason = _("The target capacity (6) is greater "
                   "than the cluster's max_size (5).")
        self.assertEqual(reason, action['status_reason'])

        # Verify cluster scale out result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, len(cluster['nodes']))

        # Scale in cluster without params
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in')
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale in result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, len(cluster['nodes']))

        # Scale in with count set to 3
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in', {'count': 3})
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster scale in result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Keep scaling in and break the size constraint
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'scale_in')
        action = test_utils.wait_for_status(test_api.get_action, self.client,
                                            action_id, 'FAILED')

        reason = _("The target capacity (0) is less "
                   "than the cluster's min_size (1).")
        self.assertEqual(reason, action['status_reason'])

        # Verify cluster scale in result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'DELETED',
                                             ignore_missing=True)
