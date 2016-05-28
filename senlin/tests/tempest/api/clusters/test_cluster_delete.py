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


class TestClusterDelete(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterDelete, cls).resource_setup()
        cls.profile = utils.create_a_profile(cls)
        cls.cluster = utils.create_a_cluster(cls, cls.profile['id'])

    @classmethod
    def resource_cleanup(cls):
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestClusterDelete, cls).resource_cleanup()

    @decorators.idempotent_id('33d7426e-0138-42c9-9ab4-ba796a7d1fdc')
    def test_cluster_delete_in_active_status(self):
        # Delete test cluster
        res = self.client.delete_obj('clusters', self.cluster['id'])

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIsNone(res['body'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.wait_for_status('actions', action_id, 'SUCCEEDED')
