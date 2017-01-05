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

import six
from tempest.lib import decorators
from tempest.lib import exceptions

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestNodeOperation(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeOperation, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('a824fe2c-b8cc-455d-9ec1-73ff9606f9cc')
    def test_reboot(self):
        params = {
            'reboot': {
                'type': 'SOFT'
            }
        }
        # Trigger node action
        res = self.client.trigger_operation('nodes', self.node_id, params)

        # Verfiy resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestNodeOperationNegative(base.BaseSenlinAPITest):

    @utils.api_microversion('1.3')
    @decorators.idempotent_id('4b3fc5dd-507a-4414-859c-44c87a2879fc')
    def test_bad_microversion(self):
        params = {'reboot': {}}
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_operation,
                               'nodes', 'FAKE_ID', params)
        self.assertIn('API version 1.3 is not supported', six.text_type(ex))

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('2b53a240-7ec6-4d92-bc2d-aaba2e63ee21')
    def test_no_operation(self):
        params = {}

        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_operation,
                               'nodes', 'FAKE_ID', params)
        self.assertIn('No operation specified', six.text_type(ex))

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('b1c3a00b-e00c-4829-ba4a-475f8d34d1d9')
    def test_multiple_ops(self):
        params = {'foo': {}, 'bar': {}}

        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_operation,
                               'nodes', 'FAKE_ID', params)

        self.assertIn('Multiple operations specified', six.text_type(ex))


class TestNodeOperationNegativeEngineFailure(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestNodeOperationNegativeEngineFailure, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)

        self.node_id = utils.create_a_node(self, profile_id)
        self.addCleanup(utils.delete_a_node, self, self.node_id)

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('bbfbd693-4c46-4670-a9d3-5658a43eb0d5')
    def test_node_not_found(self):
        params = {'dance': {}}

        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_operation,
                          'nodes', 'bbfbd693-4c46-4670-a9d3-5658a43eb0d5',
                          params)

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('5c0a23c0-9efe-4d04-9208-0f11da690e79')
    def test_operation_not_supported(self):
        params = {'dance': {}}

        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_operation,
                               'nodes', self.node_id, params)

        self.assertIn("The requested operation 'dance' is not supported",
                      six.text_type(ex))

    @utils.api_microversion('1.4')
    @decorators.idempotent_id('b00f1ef8-9ae6-4ed3-8622-566e7d0d3a75')
    def test_operation_bad_params(self):
        params = {'reboot': {'type': 'Unknown'}}

        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_operation,
                               'nodes', self.node_id, params)

        self.assertIn("'Unknown' must be one of the allowed values",
                      six.text_type(ex))
