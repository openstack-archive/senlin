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


class TestReceiverList(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestReceiverList, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        self.receiver_id = utils.create_a_receiver(self.client, cluster_id,
                                                   'CLUSTER_RESIZE')
        self.addCleanup(self.client.delete_obj, 'receivers', self.receiver_id)

    @decorators.idempotent_id('e5cedce0-9240-45ea-90d7-692be5058aac')
    def test_receiver_list(self):
        res = self.client.list_objs('receivers')

        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        receivers = res['body']
        ids = []
        for receiver in receivers:
            for key in ['action', 'actor', 'channel', 'cluster_id',
                        'created_at', 'domain', 'id', 'name', 'params',
                        'project', 'type', 'updated_at', 'user']:
                self.assertIn(key, receiver)
            ids.append(receiver['id'])
        self.assertIn(self.receiver_id, ids)
