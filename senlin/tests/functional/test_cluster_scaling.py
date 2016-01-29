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

from senlin.common.i18n import _
from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestClusterScaling(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestClusterScaling, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestClusterScaling, self).tearDown()

    def test_cluster_scale_in_out(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 5
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

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
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])

    def test_cluster_resize_basic(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 5
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Increase cluster size by specifying adjustment count
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': 3,
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, len(cluster['nodes']))

        # Decrease cluster size by specifying adjustment percentage.
        params = {
            'adjustment_type': 'CHANGE_IN_PERCENTAGE',
            'number': -50,
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, len(cluster['nodes']))

        # Decrease cluster size by specifying exact capacity
        params = {
            'adjustment_type': 'EXACT_CAPACITY',
            'number': 2,
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, len(cluster['nodes']))

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])

    def test_cluster_resize_with_constraint_breaking(self):
        # Create cluster
        desired_capacity = 3
        min_size = 1
        max_size = 5
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Increase cluster size and break the size constraint
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': 3,
            'strict': True
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'resize',
                                      params)
        reason = _("The target capacity (6) is greater than the cluster's "
                   "max_size (5).")
        self.assertIn(reason, res)

        # Do best-effort resizing
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': 3,
            'strict': False
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)

        # Wait for cluster resize action succeeded
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, len(cluster['nodes']))

        # Decrease cluster size and break the size constraint
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': -5,
            'strict': True
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'resize',
                                      params)
        reason = _("The target capacity (0) is less than the cluster's "
                   "min_size (1).")
        self.assertIn(reason, res)

        # Do best-effort resizing
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': -5,
            'strict': False
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)

        # Wait for cluster resize action succeeded
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])

    def test_cluster_resize_with_constraint_adjusting(self):
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

        # Increase cluster size with upper limit increasing
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': 3,
            'max_size': 6
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(6, len(cluster['nodes']))

        # Decrease cluster size upper limit with strict set to False
        params = {
            'max_size': 4,
            'strict': False
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, len(cluster['nodes']))

        # Reduce cluster size with lower limit change
        params = {
            'adjustment_type': 'CHANGE_IN_CAPACITY',
            'number': -3,
            'min_size': 1
        }
        action_id = test_api.action_cluster(self.client, cluster['id'],
                                            'resize', params)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Increase cluster size lower limit with strict set to True
        params = {
            'min_size': 2,
            'strict': True
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'resize',
                                      params)
        reason = _("The specified min_size (2) is greater than the current "
                   "desired_capacity (1) of the cluster.")
        self.assertIn(reason, res)

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, len(cluster['nodes']))

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])

    def test_cluster_resize_with_invalid_constraint_provided(self):
        # Create cluster
        desired_capacity = 3
        min_size = 1
        max_size = 4
        cluster = test_api.create_cluster(self.client,
                                          test_utils.random_name('cluster'),
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # New min_size is larger than current cluster
        # max_size with strict set to False
        params = {
            'min_size': 5,
            'strict': False
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'resize',
                                      params)
        reason = _("The specified min_size (5) is greater than the current "
                   "max_size (4) of the cluster.")
        self.assertIn(reason, res)

        # New max_size is less than current cluster
        # min_size with strict set to True
        params = {
            'max_size': 0,
            'strict': True
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'resize',
                                      params)
        reason = _("The specified max_size (0) is less than the current "
                   "min_size (1) of the cluster.")
        self.assertIn(reason, res)

        # New min_size > new max_size
        params = {
            'min_size': 5,
            'max_size': 3
        }
        res = test_api.action_cluster(self.client, cluster['id'], 'resize',
                                      params)
        reason = _("The specified min_size (5) is greater than the "
                   "specified max_size (3).")
        self.assertIn(reason, res)

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        cluster = test_utils.wait_for_delete(test_api.get_cluster, self.client,
                                             cluster['id'])
