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
from senlin.tests.tempest.api import utils


class TestReceiverShowNegativeNotFound(base.BaseSenlinTest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0cca923f-3e6c-4e23-8d42-2e1c70243c9d')
    def test_receiver_show_not_found(self):
        self.assertRaises(exceptions.NotFound,
                          self.client.get_obj,
                          'receivers',
                          '0cca923f-3e6c-4e23-8d42-2e1c70243c9d')


class TestReceiverShowNegativeBadRequest(base.BaseSenlinTest):

    def setUp(self):
        super(TestReceiverShowNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, cluster_id)

        self.receiver_id1 = utils.create_a_receiver(self.client, cluster_id,
                                                    'CLUSTER_RESIZE',
                                                    name='r-01')
        self.receiver_id2 = utils.create_a_receiver(self.client, cluster_id,
                                                    'CLUSTER_RESIZE',
                                                    name='r-01')
        self.addCleanup(self.client.delete_obj, 'receivers', self.receiver_id1)
        self.addCleanup(self.client.delete_obj, 'receivers', self.receiver_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('5bbfde20-c083-4212-81fb-4eea63271bbb')
    def test_recevier_show_multiple_choice(self):
        self.assertRaises(exceptions.BadRequest,
                          self.client.get_obj,
                          'receivers', 'r-01')
