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


class TestWebhookTrigger(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestWebhookTrigger, cls).resource_setup()
        cls.profile_id = utils.create_a_profile(cls)
        cls.cluster_id = utils.create_a_cluster(cls, cls.profile_id)['id']
        params = {'max_size': 2}
        receiver = cls.create_receiver(cls.cluster_id, 'CLUSTER_RESIZE',
                                       'webhook', params=params)
        cls.receiver_id = receiver['id']
        cls.webhook_url = receiver['channel']['alarm_url']

    @classmethod
    def resource_cleanup(cls):
        cls.delete_receiver(cls.receiver_id)
        utils.delete_a_cluster(cls, cls.cluster_id)
        utils.delete_a_profile(cls, cls.profile_id)
        super(TestWebhookTrigger, cls).resource_cleanup()

    @decorators.idempotent_id('afd671af-330a-46d6-bdb5-9c50966ab8b5')
    def test_trigger_webhook(self):
        res = self.client.trigger_webhook(self.webhook_url)

        # Verify resp of webhook API
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        # Trigger webhook action
        action_id = res['location'].split('/actions/')[1]
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify cluster status
        cluster = self.get_test_cluster(self.cluster_id)
        self.assertEqual(2, cluster['max_size'])
