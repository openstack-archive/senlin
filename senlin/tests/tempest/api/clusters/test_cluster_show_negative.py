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


class TestClusterShowNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('bbc593ff-8556-416e-83c3-384e5c14d363')
    def test_cluster_show_not_found(self):
        self.assertRaises(exceptions.NotFound,
                          self.client.get_obj,
                          'clusters', 'bbc593ff-8556-416e-83c3-384e5c14d363')


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
        self.assertRaises(exceptions.BadRequest,
                          self.client.get_obj,
                          'clusters', 'c-01')
