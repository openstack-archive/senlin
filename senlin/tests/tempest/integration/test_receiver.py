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

import time

from oslo_utils import timeutils
from tempest.lib import decorators

from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils
from senlin.tests.tempest.integration import base


class TestReceiver(base.BaseSenlinIntegrationTest):

    def setUp(self):
        super(TestReceiver, self).setUp()
        self.profile_id = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.attr(type=['integration'])
    @decorators.idempotent_id('16902c7a-1057-49bb-aa9e-227297864a92')
    def test_message_receiver(self):
        # Create a message type of receiver
        receiver_id = utils.create_a_receiver(self, None, None,
                                              r_type='message')
        self.addCleanup(utils.delete_a_receiver, self, receiver_id)
        receiver = utils.get_a_receiver(self, receiver_id)
        queue_name = receiver['channel']['queue_name']
        self.assertTrue(queue_name.startswith('senlin-receiver-'))

        # Trigger cluster_scale_out action
        message1 = {
            'body': {
                'cluster': self.cluster_id,
                'action': 'CLUSTER_SCALE_OUT'
            },
            'ttl': 3600
        }
        utils.post_messages(self, queue_name, [message1])

        # Wait and verify result
        timeout = 120
        with timeutils.StopWatch(timeout) as timeout_watch:
            while timeout > 0:
                time.sleep(5)
                cluster = utils.get_a_cluster(self, self.cluster_id)
                if (len(cluster['nodes']) == 2 and
                        cluster['status'] == 'ACTIVE'):
                    break
                timeout = timeout_watch.leftover(True)

        if timeout <= 0:
            raise Exception('Failed in triggering cluster action.')

        # TODO(Anyone): uncomment the following code when DB
        # concurrency issue is fixed.
#        # Trigger multiple actions at the same time
#        message2 = {
#            'body': {
#                'cluster': self.cluster_id,
#                'action': 'CLUSTER_SCALE_IN'
#            },
#            'ttl': 3600
#        }
#        utils.post_messages(self, queue_name, [message1, message1, message2])
#
#        # Wait and verify result
#        timeout = 360
#        while timeout > 0:
#            time.sleep(5)
#            cluster = utils.get_a_cluster(self, self.cluster_id)
#            if len(cluster['nodes']) == 3 and cluster['status'] == 'ACTIVE':
#                break
#            timeout -= 5
#        if timeout <= 0:
#            raise Exception('Failed in triggering cluster action.')
