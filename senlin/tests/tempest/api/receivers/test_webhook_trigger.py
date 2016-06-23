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

from senlin.tests.tempest.api import base
from senlin.tests.tempest.api import utils


class TestWebhookTrigger(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestWebhookTrigger, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        params = {'max_size': 2}
        self.receiver_id = utils.create_a_receiver(self.client, cluster_id,
                                                   'CLUSTER_RESIZE',
                                                   params=params)
        self.addCleanup(self.client.delete_obj, 'receivers', self.receiver_id)

        receiver = self.client.get_obj('receivers', self.receiver_id)
        self.webhook_url = receiver['body']['channel']['alarm_url']

    @decorators.idempotent_id('afd671af-330a-46d6-bdb5-9c50966ab8b5')
    def test_webhook_trigger(self):
        res = self.client.trigger_webhook(self.webhook_url)

        # Verify resp of webhook API
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        # Trigger webhook action
        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')
