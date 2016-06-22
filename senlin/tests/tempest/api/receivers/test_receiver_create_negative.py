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


class TestReceiverCreateNegativeBadRequest(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('b55d204c-8ba2-43fd-bde4-d7d9d0e54c29')
    def test_receiver_create_receiver_data_not_specified(self):
        # receiver key is missing in request data
        params = {
            'receive': {
                'name': 'test-receiver',
                'cluster_id': 'CLUSTER_ID',
                'type': 'webhook',
                'action': 'CLUSTER_SCALE_IN',
                'params': {"count": 5}
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'receivers', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0e5cadcf-d9b7-4617-a83f-49557765f9bf')
    def test_receiver_create_unsupported_receiver_type(self):
        # Unsupported receiver type is specified
        params = {
            'receiver': {
                'name': 'test-receiver',
                'cluster_id': 'CLUSTER_ID',
                'type': 'bogus',
                'action': 'CLUSTER_SCALE_IN',
                'params': {"count": 5}
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'receivers', params)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('e281873f-0dff-4be6-8795-f781efe7cc14')
    def test_receiver_create_target_cluster_not_found(self):
        # Target cluster cannot be found
        params = {
            'receiver': {
                'name': 'test-receiver',
                'cluster_id': 'e281873f-0dff-4be6-8795-f781efe7cc14',
                'type': 'webhook',
                'action': 'CLUSTER_SCALE_IN',
                'params': {"count": 5}
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'receivers', params)


class TestReceiverCreateNegativeInvalidAction(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestReceiverCreateNegativeInvalidAction, self).setUp()
        self.profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, self.profile_id)
        self.cluster_id = utils.create_a_cluster(self, self.profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('80e16a56-7d56-4038-b5f4-6d1ccd76c3f2')
    def test_receiver_create_invalid_action(self):
        # Target action type is illegal
        params = {
            'receiver': {
                'name': 'test-receiver',
                'cluster_id': self.cluster_id,
                'type': 'webhook',
                'action': 'ILLEGAL_ACTION',
                'params': {"count": 5}
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.create_obj,
                          'receivers', params)
