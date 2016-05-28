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


class TestClusterAction(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterAction, cls).resource_setup()
        cls.profile = utils.create_a_profile(cls)
        cls.cluster = utils.create_a_cluster(cls, cls.profile['id'])

    @classmethod
    def resource_cleanup(cls):
        # Delete cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestClusterAction, cls).resource_cleanup()

    @decorators.idempotent_id('f5f75882-df3d-481f-bd05-019e4d08af65')
    def test_cluster_action_trigger(self):
        params = {
            'resize': {
                'max_size': 3
            }
        }
        # Trigger cluster action
        res = self.client.trigger_action('clusters', self.cluster['id'],
                                         params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.wait_for_status('actions', action_id, 'SUCCEEDED')

        # Verify action result
        cluster = self.get_test_cluster(self.cluster['id'])
        self.assertEqual(3, cluster['max_size'])
