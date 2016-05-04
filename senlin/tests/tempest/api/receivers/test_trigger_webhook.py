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
from senlin.tests.tempest.common import constants


class TestWebhookTrigger(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestWebhookTrigger, cls).resource_setup()
        # Create profile
        cls.profile = cls.create_profile(constants.spec_nova_server)
        # Create a test cluster
        cls.cluster = cls.create_test_cluster(cls.profile['id'],
                                              0, min_size=0, max_size=-1)
        # Create a webhook receiver
        params = {
            'max_size': 2
        }
        cls.receiver = cls.create_receiver(
            cls.cluster['id'], 'CLUSTER_RESIZE', 'webhook', params=params)

    @classmethod
    def resource_cleanup(cls):
        # Delete receiver
        cls.delete_receiver(cls.receiver['id'])
        # Delete test cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestWebhookTrigger, cls).resource_cleanup()

    @decorators.idempotent_id('afd671af-330a-46d6-bdb5-9c50966ab8b5')
    def test_trigger_webhook(self):
        webhook_url = self.receiver['channel']['alarm_url']
        res = self.client.trigger_webhook(webhook_url)

        # Verify resp of webhook API
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        # Trigger webhook action
        action_id = res['location'].split('/actions/')[1]
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify cluster status
        cluster = self.get_test_cluster(self.cluster['id'])
        self.assertEqual(2, cluster['max_size'])
