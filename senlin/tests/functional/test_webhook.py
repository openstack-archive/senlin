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

from oslo_log import log as logging

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base
from senlin.tests.functional.utils import test_utils

LOG = logging.getLogger(__name__)


class TestWebhook(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestWebhook, self).setUp()
        # Create profile
        self.profile = test_api.create_profile(self.client, 'test-profile',
                                               test_utils.spec_nova_server)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestWebhook, self).tearDown()

    def test_webhook(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 5
        cluster = test_api.create_cluster(self.client, 'test-cluster',
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)
        cluster = test_utils.wait_for_status(test_api.get_cluster, self.client,
                                             cluster['id'], 'ACTIVE')

        # Create a webhook targets on cluster resize action with params
        params = {
            'adjustment_type': 'EXACT_CAPACITY',
            'number': 2,
        }
        webhook = test_api.create_webhook(self.client, 'webhook-c-resize',
                                          'cluster', cluster['id'],
                                          'CLUSTER_RESIZE',
                                          params=params)
        webhook_url = webhook['url']

        # Verify webhook params
        self.assertEqual('webhook-c-resize', webhook['name'])
        self.assertEqual('cluster', webhook['obj_type'])
        self.assertEqual(cluster['id'], webhook['obj_id'])
        self.assertEqual('CLUSTER_RESIZE', webhook['action'])
        self.assertEqual(params, webhook['params'])

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

        # Delete webhook
        test_api.delete_webhook(self.client, webhook['id'])

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        test_utils.wait_for_status(test_api.get_cluster, self.client,
                                   cluster['id'], 'DELETED',
                                   ignore_missing=True)
