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


class TestReceiverDeleteNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('799395ff-8bb5-49d6-9e3b-0d2d4428e8c1')
    def test_receiver_delete_not_found(self):
        # Verify notfound exception(404) is raised.
        self.assertRaises(exceptions.NotFound,
                          self.client.delete_obj,
                          'receivers', '799395ff-8bb5-49d6-9e3b-0d2d4428e8c1')


class TestReceiverDeleteNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestReceiverDeleteNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        self.receiver_id1 = utils.create_a_receiver(self, cluster_id,
                                                    'CLUSTER_RESIZE',
                                                    name='r-01')
        self.addCleanup(utils.delete_a_receiver, self, self.receiver_id1)
        self.receiver_id2 = utils.create_a_receiver(self, cluster_id,
                                                    'CLUSTER_RESIZE',
                                                    name='r-01')
        self.addCleanup(utils.delete_a_receiver, self, self.receiver_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f6f2377c-f125-4c35-be5f-42f94ba81a0e')
    def test_receiver_delete_multiple_choice(self):
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.delete_obj,
                          'receivers', 'r-01')
