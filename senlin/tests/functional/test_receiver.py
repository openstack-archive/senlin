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

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils


class TestReceiver(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestReceiver, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(
            self.client, test_utils.random_name('profile'),
            test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestReceiver, self).tearDown()


class TestWebhook(TestReceiver):
    def test_webhook(self):
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

        # Create a webhook receiver targets on cluster resize action
        # with params
        params = {
            'adjustment_type': 'EXACT_CAPACITY',
            'number': 2,
        }
        webhook_name = test_utils.random_name('webhook')
        res = test_api.create_receiver(self.client, webhook_name,
                                       cluster['id'], 'CLUSTER_RESIZE',
                                       'webhook', params=params)

        r_webhook = test_api.get_receiver(self.client, res['id'])
        # Verify webhook params
        self.assertEqual(webhook_name, r_webhook['name'])
        self.assertEqual(cluster['id'], r_webhook['cluster_id'])
        self.assertEqual('CLUSTER_RESIZE', r_webhook['action'])
        self.assertEqual(params, r_webhook['params'])
        webhook_url = r_webhook['channel']['alarm_url']

        # Trigger webhook and wait for action complete
        action_id = test_api.trigger_webhook(webhook_url)
        test_utils.wait_for_status(test_api.get_action, self.client,
                                   action_id, 'SUCCEEDED')

        # Verify action is as expected
        action = test_api.get_action(self.client, action_id)
        self.assertEqual('CLUSTER_RESIZE', action['action'])
        self.assertEqual(cluster['id'], action['target'])
        self.assertEqual(params, action['inputs'])

        # Verify cluster resize result
        cluster = test_api.get_cluster(self.client, cluster['id'])
        self.assertEqual('ACTIVE', cluster['status'])
        self.assertEqual(2, len(cluster['nodes']))

        # Delete webhook receiver
        test_api.delete_receiver(self.client, r_webhook['id'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_utils.wait_for_status(test_api.get_cluster, self.client,
                                   cluster['id'], 'DELETED',
                                   ignore_missing=True)
