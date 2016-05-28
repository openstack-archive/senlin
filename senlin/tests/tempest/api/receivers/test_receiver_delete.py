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


class TestReceiverDelete(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestReceiverDelete, cls).resource_setup()
        cls.profile = utils.create_a_profile(cls)
        cls.cluster = utils.create_a_cluster(cls, cls.profile['id'])
        cls.receiver = cls.create_receiver(cls.cluster['id'],
                                           'CLUSTER_RESIZE', 'webhook')

    @classmethod
    def resource_cleanup(cls):
        # Delete test cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestReceiverDelete, cls).resource_cleanup()

    @decorators.idempotent_id('c67cf6c3-2339-4f10-9631-fb7e9f47170f')
    def test_delete_receiver(self):
        # Verify resp of receiver delete API
        res = self.client.delete_obj('receivers', self.receiver['id'])
        self.assertEqual(204, res['status'])
        self.assertIsNone(res['body'])
