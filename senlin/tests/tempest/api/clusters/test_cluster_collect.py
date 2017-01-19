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
from tempest.lib import exceptions

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestClusterCollect(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterCollect, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        self.node1 = utils.create_a_node(self, profile_id, name='N01',
                                         cluster_id=self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.node1)
        self.node2 = utils.create_a_node(self, profile_id, name='N02',
                                         cluster_id=self.cluster_id)
        self.addCleanup(utils.delete_a_node, self, self.node2)

    @utils.api_microversion('1.2')
    @decorators.idempotent_id('00c389f8-3e83-4171-bd72-2202f1f3954d')
    def test_cluster_collect(self):
        # Collect on a basic path
        res = self.client.cluster_collect(self.cluster_id, path='name')

        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        self.assertIn({u'id': self.node1, u'value': u'N01'}, res['body'])
        self.assertIn({u'id': self.node2, u'value': u'N02'}, res['body'])

    @utils.api_microversion('1.2')
    @decorators.idempotent_id('1ec4ca67-20db-43eb-95af-1301aa2b1948')
    def test_cluster_collect_details(self):
        # Collect on a basic path
        res = self.client.cluster_collect(self.cluster_id,
                                          path='details.status')

        self.assertEqual(200, res['status'])
        self.assertIsNotNone(res['body'])
        self.assertIn({u'id': self.node1, u'value': u'ACTIVE'}, res['body'])
        self.assertIn({u'id': self.node2, u'value': u'ACTIVE'}, res['body'])


class TestClusterCollectNegative(base.BaseSenlinAPITest):

    @utils.api_microversion('1.1')
    @decorators.idempotent_id('88fff27d-27eb-4a4d-906b-b3a9761072ba')
    def test_cluster_collect_failed_api_version(self):
        # Collect on a basic path
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_collect,
                               'FAKE_CLUSTER', path='name')

        message = ex.resp_body['error']['message']
        self.assertEqual("API version '1.1' is not supported on this method.",
                         str(message))

    @utils.api_microversion('1.2')
    @decorators.idempotent_id('a3d59666-93be-47ee-a484-c248ed2f49fe')
    def test_cluster_collect_failed_path(self):
        # Collect on a basic path
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.cluster_collect,
                               'FAKE_CLUSTER', path='None')

        message = ex.resp_body['error']['message']
        self.assertEqual("Required path attribute is missing.",
                         str(message))

    @utils.api_microversion('1.2')
    @decorators.idempotent_id('a3d59666-93be-47ee-a484-c248ed2f49fe')
    def test_cluster_collect_cluster_not_found(self):
        # Collect on a basic path
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.cluster_collect,
                               'a3d59666-93be-47ee-a484-c248ed2f49fe',
                               path='name')

        message = ex.resp_body['error']['message']
        self.assertEqual("The cluster 'a3d59666-93be-47ee-a484-c248ed2f49fe' "
                         "could not be found.", str(message))
