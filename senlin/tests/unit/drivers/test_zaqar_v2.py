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

from senlin.drivers.openstack import sdk
from senlin.drivers.openstack import zaqar_v2
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

    def test_queue_get(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.queue_get('foo')
        self.message.get_queue.assert_called_once_with('foo')

    def test_queue_list(self):
        self.message.queues.return_value = [{'name': 'q1'},
                                            {'name': 'q2'}]
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.queue_list()
        self.message.queues.assert_called_once_with()
        self.message.queues.reset_mock()

        zc.queue_list(foo='bar')
        self.message.queues.assert_called_once_with(foo='bar')

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

    def test_messgae_post(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        messages = {'k1': 'v1'}
        zc.message_post('foo', messages)
        self.message.post_message.assert_called_once_with(
            'foo', messages)

    def test_message_get(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.message_get('foo', 'MESSAGE_ID')
        self.message.get_message.assert_called_once_with(
            'foo', 'MESSAGE_ID')

    def test_message_list(self):
        self.message.messages.return_value = [{'id': 'ID1'},
                                              {'id': 'ID2'}]
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.message_list('foo')
        self.message.messages.assert_called_once_with('foo')
        self.message.messages.reset_mock()

        zc.message_list('foo', marker='ID1')
        self.message.messages.assert_called_once_with(
            'foo', marker='ID1')

    def test_message_delete(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.message_delete('foo', 'MESSAGE_ID', True)
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', True)
        self.message.delete_message.reset_mock()

        zc.message_delete('foo', 'MESSAGE_ID', False)
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', False)
        self.message.delete_message.reset_mock()

        zc.message_delete('foo', 'MESSAGE_ID')
        self.message.delete_message.assert_called_once_with(
            'foo', 'MESSAGE_ID', True)

    def test_subscription_create(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        attrs = {'k1': 'v1'}
        zc.subscription_create('foo', **attrs)
        self.message.create_subscription.assert_called_once_with(
            'foo', k1='v1')

    def test_subscription_get(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.subscription_get('foo', 'SUBSCRIPTION_ID')
        self.message.get_subscription.assert_called_once_with(
            'foo', 'SUBSCRIPTION_ID')

    def test_subscription_list(self):
        self.message.subscriptions.return_value = [{'id': 'ID1'},
                                                   {'id': 'ID2'}]
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.subscription_list('foo')
        self.message.subscriptions.assert_called_once_with('foo')
        self.message.subscriptions.reset_mock()

        zc.subscription_list('foo', marker='ID1')
        self.message.subscriptions.assert_called_once_with(
            'foo', marker='ID1')

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
        self.message.create_claim.assert_called_once_with(
            'foo', k1='v1')

    def test_claim_get(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        zc.claim_get('foo', 'CLAIM_ID')
        self.message.get_claim.assert_called_once_with(
            'foo', 'CLAIM_ID')

    def test_claim_update(self):
        zc = zaqar_v2.ZaqarClient(self.conn_params)
        attrs = {'k1': 'v1'}
        zc.claim_update('foo', 'CLAIM_ID', **attrs)
        self.message.update_claim.assert_called_once_with(
            'foo', 'CLAIM_ID', k1='v1')

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
