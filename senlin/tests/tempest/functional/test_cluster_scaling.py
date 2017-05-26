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

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('e326554b-9b42-45f8-a9ea-4ab0914fb364')
    def test_cluster_scale_in_out(self):
        # Scale out cluster without count specified
        utils.cluster_scale_out(self, self.cluster_id)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))

        # Scale out cluster with count set to 2
        utils.cluster_scale_out(self, self.cluster_id, count=2)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))

        # Keep scaling out cluster with count set to 2
        res = utils.cluster_scale_out(self, self.cluster_id, count=2,
                                      expected_status='FAILED')

        # Verify action result and action failure reason
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))
        reason = _("The target capacity (6) is greater "
                   "than the cluster's max_size (5).")
        self.assertEqual(reason, res)

        # Scale in cluster with count set to 2
        utils.cluster_scale_in(self, self.cluster_id, count=2)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))

        # Scale in cluster without count specified
        utils.cluster_scale_in(self, self.cluster_id)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))

        # Keep scaling in cluster
        res = utils.cluster_scale_in(self, self.cluster_id,
                                     expected_status='FAILED')

        # Verify action result and action failure reason
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))
        reason = _("The target capacity (0) is less "
                   "than the cluster's min_size (1).")
        self.assertEqual(reason, res)


class TestClusterResize(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestClusterResize, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 min_size=2, max_size=5,
                                                 desired_capacity=3)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('02b570ef-9101-489b-9ee7-8c1f35d2b105')
    def test_cluster_resize_basic(self):
        # Increase cluster size by specifying adjustment count
        kwargs = {
            'adj_type': 'CHANGE_IN_CAPACITY',
            'number': 2
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, cluster['desired_capacity'])
        self.assertEqual(5, len(cluster['nodes']))

        # Decrease cluster size by specifying adjustment percentage
        kwargs = {
            'adj_type': 'CHANGE_IN_PERCENTAGE',
            'number': -50
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, cluster['desired_capacity'])
        self.assertEqual(3, len(cluster['nodes']))

        # Decrease cluster size by specifying exact capacity
        kwargs = {
            'adj_type': 'EXACT_CAPACITY',
            'number': 2
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('72aac2f7-8cb3-4d95-a0b8-4aeeadf4b319')
    def test_cluster_resize_constraint_breaking(self):
        # Do best-effort resizing when size upper limit is broken
        kwargs = {
            'adj_type': 'CHANGE_IN_CAPACITY',
            'number': 1,
            'strict': False
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))

        # Do best-effort resizing when size lower limit is broken
        kwargs = {
            'adj_type': 'CHANGE_IN_CAPACITY',
            'number': -5,
            'strict': False
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('9bde1918-7821-4024-a382-44e6b4950a7e')
    def test_cluster_resize_constraint_adjusting(self):
        # Increase cluster size with upper limit increased
        kwargs = {
            'adj_type': 'CHANGE_IN_CAPACITY',
            'number': 3,
            'max_size': 7
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(6, cluster['desired_capacity'])
        self.assertEqual(6, len(cluster['nodes']))
        self.assertEqual(7, cluster['max_size'])

        # Decrease cluster size upper limit with strict set to False
        kwargs = {
            'max_size': 4,
            'strict': False
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))
        self.assertEqual(4, cluster['max_size'])

        # Decrease cluster size with lower limit decreased
        kwargs = {
            'adj_type': 'CHANGE_IN_CAPACITY',
            'number': -4,
            'min_size': 0
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(0, cluster['desired_capacity'])
        self.assertEqual(0, len(cluster['nodes']))
        self.assertEqual(0, cluster['min_size'])

        # Increase cluster size lower limit with strict set to False
        kwargs = {
            'min_size': 2,
            'strict': False
        }
        utils.cluster_resize(self, self.cluster_id, **kwargs)

        # Verify resizing result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))
        self.assertEqual(2, cluster['min_size'])
