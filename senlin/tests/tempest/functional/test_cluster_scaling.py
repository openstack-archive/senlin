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
from tempest import test

from senlin.common.i18n import _
from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestClusterScaleInOut(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestClusterScaleInOut, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 min_size=1, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['functional'])
    @decorators.idempotent_id('e326554b-9b42-45f8-a9ea-4ab0914fb364')
    def test_cluster_scale_in_out(self):
        # Scale out cluster without count specified
        utils.cluster_scale_out(self, self.cluster_id)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))

        # Scale out cluster with count set to 2
        utils.cluster_scale_out(self, self.cluster_id, count=2)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))

        # Keep scaling out cluster with count set to 2
        res = utils.cluster_scale_out(self, self.cluster_id, count=2,
                                      expected_status='FAILED')

        # Verify action result and action failure reason
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))
        reason = _("The target capacity (6) is greater "
                   "than the cluster's max_size (5).")
        self.assertEqual(reason, res)

        # Scale in cluster with count set to 2
        utils.cluster_scale_in(self, self.cluster_id, count=2)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))

        # Scale in cluster without count specified
        utils.cluster_scale_in(self, self.cluster_id)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))

        # Keep scaling in cluster
        res = utils.cluster_scale_in(self, self.cluster_id,
                                     expected_status='FAILED')

        # Verify action result and action failure reason
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))
        reason = _("The target capacity (0) is less "
                   "than the cluster's min_size (1).")
        self.assertEqual(reason, res)
