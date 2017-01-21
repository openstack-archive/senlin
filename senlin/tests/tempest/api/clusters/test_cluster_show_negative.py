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
from tempest import test

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestClusterShowNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterShowNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id1 = utils.create_a_cluster(self, profile_id,
                                                  name='c-01')
        self.cluster_id2 = utils.create_a_cluster(self, profile_id,
                                                  name='c-01')
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('3365dca5-8895-4dc3-befe-fd15b17c824c')
    def test_cluster_show_multiple_choice(self):
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.get_obj,
                               'clusters', 'c-01')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Multiple results found matching the query criteria "
            "'c-01'. Please be more specific.", str(message))


class TestClusterShowNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('4706516e-002d-42b2-9805-69058178cd9c')
    def test_cluster_show_cluster_not_found(self):
        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.get_obj,
                               'clusters', 'c-01')

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster 'c-01' could "
            "not be found.", str(message))
