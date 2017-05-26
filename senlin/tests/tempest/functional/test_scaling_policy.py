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
from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestScalingPolicy(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestScalingPolicy, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.attr(type=['functional'])
    @decorators.idempotent_id('6b513a5d-75b6-447a-b95d-e17b84ac9ee8')
    def test_scaling_policy(self):
        # Create a scaling policy targets on CLUSTER_SCALE_OUT action
        spec = constants.spec_scaling_policy
        spec['properties'] = {
            'event': 'CLUSTER_SCALE_OUT',
            'adjustment': {
                'type': 'CHANGE_IN_CAPACITY',
                'number': 2,
                'min_step': 1,
                'best_effort': True
            }
        }
        policy_id = utils.create_a_policy(self, spec)
        scaleout_policy = utils.get_a_policy(self, policy_id)
        self.addCleanup(utils.delete_a_policy, self, scaleout_policy['id'])

        # Create a scaling policy targets on CLUSTER_SCALE_IN action
        spec['properties'] = {
            'event': 'CLUSTER_SCALE_IN',
            'adjustment': {
                'type': 'CHANGE_IN_PERCENTAGE',
                'number': 50,
                'min_step': 2,
                'best_effort': False
            }
        }
        policy_id = utils.create_a_policy(self, spec)
        scalein_policy = utils.get_a_policy(self, policy_id)
        self.addCleanup(utils.delete_a_policy, self, scalein_policy['id'])

        # Attach scale in/out policies to cluster
        for policy in [scaleout_policy, scalein_policy]:
            utils.cluster_attach_policy(self, self.cluster_id, policy['id'])
            self.addCleanup(utils.cluster_detach_policy, self,
                            self.cluster_id, policy['id'])

        # Scale out cluster without count specified
        utils.cluster_scale_out(self, self.cluster_id)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, cluster['desired_capacity'])
        self.assertEqual(3, len(cluster['nodes']))

        # Scale out cluster with count set to 1
        utils.cluster_scale_out(self, self.cluster_id, count=1)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(4, cluster['desired_capacity'])
        self.assertEqual(4, len(cluster['nodes']))

        # Keep scaling out cluster with count set to 2 to
        # verify best_effort parameter
        utils.cluster_scale_out(self, self.cluster_id, count=2)

        # Verify scale out result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(5, cluster['desired_capacity'])
        self.assertEqual(5, len(cluster['nodes']))

        # Scale in cluster without count specified
        utils.cluster_scale_in(self, self.cluster_id)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(3, cluster['desired_capacity'])
        self.assertEqual(3, len(cluster['nodes']))

        # Scale in cluster without count specified to
        # verify min_step parameter
        utils.cluster_scale_in(self, self.cluster_id)

        # Verify scale in result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))

        # Keep scaling in cluster with count set to 2 to
        # verify best_effort parameter
        res = utils.cluster_scale_in(self, self.cluster_id, count=2,
                                     expected_status='FAILED')

        # Verify action result and action failure reason
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(1, cluster['desired_capacity'])
        self.assertEqual(1, len(cluster['nodes']))
        reason = _(
            "Policy check failure: Failed policy '%s': The target "
            "capacity (-1) is less than the cluster's "
            "min_size (0).") % scalein_policy['name']
        self.assertEqual(reason, res)
