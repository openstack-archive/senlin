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

from senlin.tests.tempest.common import utils
from senlin.tests.tempest.functional import base


class TestReceiver(base.BaseSenlinFunctionalTest):

    def setUp(self):
        super(TestReceiver, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['functional'])
    @decorators.idempotent_id('60b04757-1ee1-4955-a098-b1c42af6bb19')
    def test_webhook(self):
        # Create a webhook type of receiver
        receiver_id = utils.create_a_receiver(self, self.cluster_id,
                                              'CLUSTER_SCALE_OUT',
                                              r_type='webhook',
                                              params={'count': 2})
        self.addCleanup(utils.delete_a_receiver, self, receiver_id)
        receiver = utils.get_a_receiver(self, receiver_id)
        webhook_url = receiver['channel']['alarm_url']

        # Trigger webhook and wait for action execution
        res = self.client.trigger_webhook(webhook_url)
        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify action result
        cluster = utils.get_a_cluster(self, self.cluster_id)
        self.assertEqual(2, cluster['desired_capacity'])
        self.assertEqual(2, len(cluster['nodes']))
