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
from tempest import test

from senlin.tests.tempest.common import utils
from senlin.tests.tempest.integration import base


class TestNovaServerCluster(base.BaseSenlinIntegrationTest):

    def setUp(self):
        super(TestNovaServerCluster, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)

    @test.attr(type=['integration'])
    @decorators.idempotent_id('c26eae1c-5c46-4a5f-be63-954d7229c8cc')
    def test_cluster_create_delete(self):
        pass
