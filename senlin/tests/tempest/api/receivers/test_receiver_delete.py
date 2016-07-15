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
from senlin.tests.tempest.common import utils


class TestReceiverDelete(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestReceiverDelete, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        self.receiver_id = utils.create_a_receiver(self, cluster_id,
                                                   'CLUSTER_RESIZE')

    @decorators.idempotent_id('c67cf6c3-2339-4f10-9631-fb7e9f47170f')
    def test_receiver_delete(self):
        # Verify resp of receiver delete API
        res = self.client.delete_obj('receivers', self.receiver_id)
        self.assertEqual(204, res['status'])
        self.assertIsNone(res['body'])
        self.assertEqual('0', res['content-length'])
