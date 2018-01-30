# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from openstack import exceptions as sdk_exc

from senlin.drivers.os import zaqar_v2
from senlin.drivers import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestZaqarV2(base.SenlinTestCase):

    def setUp(self):
        super(TestZaqarV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.mock_conn = mock.Mock()
        self.mock_create = self.patchobject(
            sdk, 'create_connection',
            return_value=self.mock_conn)
        self.message = self.mock_conn.message

    def test_init(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        self.mock_create.assert_called_once_with(self.conn_params)
        self.assertEqual(self.mock_conn, zc.conn)

    def test_queue_create(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.queue_create(name='foo')
        self.message.create_queue.assert_called_once_with(name='foo')

    def test_queue_exists(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        res = zc.queue_exists('foo')
        self.message.get_queue.assert_called_once_with('foo')
        self.assertTrue(res)

    def test_queue_exists_false(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        self.message.get_queue = mock.Mock()
        self.message.get_queue.side_effect = sdk_exc.ResourceNotFound

        res = zc.queue_exists('foo')
        self.message.get_queue.assert_called_once_with('foo')
        self.assertFalse(res)

    def test_queue_delete(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.queue_delete('foo', True)
        self.message.delete_queue.assert_called_once_with('foo', True)
        self.message.delete_queue.reset_mock()

        zc.queue_delete('foo', False)
        self.message.delete_queue.assert_called_once_with('foo', False)
        self.message.delete_queue.reset_mock()

        zc.queue_delete('foo')
        self.message.delete_queue.assert_called_once_with('foo', True)

    def test_subscription_create(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        attrs = {'k1': 'v1'}
        zc.subscription_create('foo', **attrs)
        self.message.create_subscription.assert_called_once_with(
            'foo', k1='v1')

    def test_subscription_delete(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.subscription_delete('foo', 'SUBSCRIPTION_ID', True)
        self.message.delete_subscription.assert_called_once_with(
            'foo', 'SUBSCRIPTION_ID', True)
        self.message.delete_subscription.reset_mock()

        zc.subscription_delete('foo', 'SUBSCRIPTION_ID', False)
        self.message.delete_subscription.assert_called_once_with(
            'foo', 'SUBSCRIPTION_ID', False)
        self.message.delete_subscription.reset_mock()

        zc.subscription_delete('foo', 'SUBSCRIPTION_ID')
        self.message.delete_subscription.assert_called_once_with(
            'foo', 'SUBSCRIPTION_ID', True)

    def test_claim_create(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        attrs = {'k1': 'v1'}

        zc.claim_create('foo', **attrs)

        self.message.create_claim.assert_called_once_with('foo', k1='v1')

    def test_claim_delete(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.claim_delete('foo', 'CLAIM_ID', True)
        self.message.delete_claim.assert_called_once_with(
            'foo', 'CLAIM_ID', True)
        self.message.delete_claim.reset_mock()

        zc.claim_delete('foo', 'CLAIM_ID', False)
        self.message.delete_claim.assert_called_once_with(
            'foo', 'CLAIM_ID', False)
        self.message.delete_claim.reset_mock()

        zc.claim_delete('foo', 'CLAIM_ID')
        self.message.delete_claim.assert_called_once_with(
            'foo', 'CLAIM_ID', True)

    def test_message_delete(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.message_delete('foo', 'MESSAGE_ID', None, True)
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', None, True)
        self.message.delete_message.reset_mock()

        zc.message_delete('foo', 'MESSAGE_ID', None, False)
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', None, False)
        self.message.delete_message.reset_mock()

        zc.message_delete('foo', 'MESSAGE_ID')
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', None, True)
        self.message.delete_message.reset_mock()

        zc.message_delete('foo', 'MESSAGE_ID', 'CLAIM_ID')
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', 'CLAIM_ID', True)

    def test_message_post(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.message_post('foo', 'MESSAGE')
        self.message.post_message.assert_called_once_with('foo', 'MESSAGE')
