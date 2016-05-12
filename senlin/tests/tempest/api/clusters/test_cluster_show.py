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


class TestClusterShow(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestClusterShow, cls).resource_setup()
        # Create profile
        cls.profile = cls.create_profile(
            constants.spec_nova_server)
        # Create a test cluster
        cls.cluster = cls.create_test_cluster(cls.profile['id'], 0)

    @classmethod
    def resource_cleanup(cls):
        # Delete test cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.delete_profile(cls.profile['id'])
        super(TestClusterShow, cls).resource_cleanup()

    @decorators.idempotent_id('45f56c9a-4589-48dd-9256-9b368727dd6c')
    def test_cluster_show(self):
        res = self.client.get_obj('clusters', self.cluster['id'])

        # Verify resp of cluster get API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        cluster = res['body']
        for key in ['created_at', 'data', 'desired_capacity', 'domain',
                    'id', 'init_at', 'max_size', 'metadata', 'min_size',
                    'name', 'nodes', 'policies', 'profile_id', 'profile_name',
                    'project', 'status', 'status_reason', 'timeout',
                    'updated_at', 'user']:
            self.assertIn(key, cluster)
