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

import time

from oslo_log import log as logging

from senlin.tests.functional import api as test_api
from senlin.tests.functional import base

LOG = logging.getLogger(__name__)


class TestCluster(base.SenlinFunctionalTest):
    def setUp(self):
        super(TestCluster, self).setUp()
        # Create profile
        test_nova_spec = {
            "type": "os.nova.server",
            "version": "1.0",
            "properties": {
                # TODO(Yanyan Hu): Use flavor name rather than ID in
                # nova server spec file after sdk support is done.
                "flavor": 1,
                "name": "new-server-test",
                "image": "cirros-0.3.2-x86_64-uec",
                "networks": [
                    {"network": "private-net"}
                ]
            }
        }
        self.profile = test_api.create_profile(self.client, 'test-profile',
                                               test_nova_spec)

    def tearDown(self):
        # Delete profile
        test_api.delete_profile(self.client, self.profile['id'])
        super(TestCluster, self).tearDown()

    def test_get_clusters(self):
        # Check that listing clusters works.
        clusters = test_api.list_clusters(self.client)
        self.assertEqual([], clusters)

    def test_cluster_create_delete(self):
        # Create cluster
        desired_capacity = 2
        min_size = 1
        max_size = 3
        cluster = test_api.create_cluster(self.client, 'test-cluster',
                                          self.profile['id'], desired_capacity,
                                          min_size, max_size)

        # Wait and verify cluster creation result
        # TODO(Yanyan Hu): Put timeout option into test configure file
        timeout = 60
        ready = False
        while timeout > 0:
            cluster = test_api.get_cluster(self.client, cluster['id'])
            if cluster['status'] == 'ACTIVE':
                ready = True
                break
            time.sleep(5)
            timeout -= 5
        if not ready:
            raise Exception('Cluster creation timeout.')

        self.assertEqual('test-cluster', cluster['name'])
        self.assertEqual(desired_capacity, cluster['desired_capacity'])
        self.assertEqual(min_size, cluster['min_size'])
        self.assertEqual(max_size, cluster['max_size'])
        self.assertEqual(desired_capacity, len(cluster['nodes']))

        # Delete cluster
        test_api.delete_cluster(self.client, cluster['id'])
        timeout = 60
        ready = False
        while timeout > 0:
            res = test_api.get_cluster(self.client, cluster['id'], True)
            if res.status == 404:
                ready = True
                break
            time.sleep(5)
            timeout -= 5
        if not ready:
            raise Exception('Cluster deletion timeout.')
