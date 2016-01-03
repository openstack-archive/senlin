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
from oslo_config import cfg
from oslo_utils import timeutils
import six

from senlin.common import exception
from senlin.common import utils as common_utils
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import receiver as receiver_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestReceiver(base.SenlinTestCase):

    def setUp(self):
        super(TestReceiver, self).setUp()
        self.context = utils.dummy_context()
        self.actor = {
            'auth_url': 'TEST_URL',
            'user_id': '123',
            'password': 'abc'
        }
        self.params = {
            'key1': 'value1',
            'key2': 'value2',
        }

    def _create_receiver(self, receiver_name, receiver_id=None):
        values = {
            'id': receiver_id,
            'name': receiver_name,
            'type': 'webhook',
            'cluster_id': 'fake-cluster',
            'action': 'test-action',
            'user': self.context.user,
            'project': self.context.project,
            'domain': self.context.domain,
            'created_at': timeutils.utcnow(),
            'updated_at': None,
            'actor': self.actor,
            'params': self.params,
            'channel': None,
        }

        return db_api.receiver_create(self.context, values)

    def test_receiver_init(self):
        kwargs = {
            'id': 'FAKE_ID',
            'name': 'test-receiver',
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'created_at': timeutils.utcnow(),
            'updated_at': None,
            'actor': self.actor,
            'params': self.params,
            'channel': {'alarm_url': 'http://url1'},
        }

        receiver = receiver_mod.Receiver('webhook', 'FAKE_CLUSTER',
                                         'test-action', **kwargs)

        self.assertEqual(kwargs['id'], receiver.id)
        self.assertEqual(kwargs['name'], receiver.name)
        self.assertEqual('webhook', receiver.type)
        self.assertEqual('test-action', receiver.action)
        self.assertEqual(kwargs['user'], receiver.user)
        self.assertEqual(kwargs['project'], receiver.project)
        self.assertEqual(kwargs['domain'], receiver.domain)

        self.assertEqual(kwargs['created_at'], receiver.created_at)
        self.assertEqual(kwargs['updated_at'], receiver.updated_at)

        self.assertEqual('FAKE_CLUSTER', receiver.cluster_id)
        self.assertEqual('test-action', receiver.action)
        self.assertEqual(self.actor, receiver.actor)
        self.assertEqual(self.params, receiver.params)
        self.assertEqual(kwargs['channel'], receiver.channel)

    def test_receiver_init_default_value(self):
        receiver = receiver_mod.Receiver('webhook', 'FAKE_CLUSTER',
                                         'test-action')
        self.assertIsNone(receiver.id)
        self.assertIsNone(receiver.name)
        self.assertEqual('webhook', receiver.type)
        self.assertEqual('', receiver.user)
        self.assertEqual('', receiver.project)
        self.assertEqual('', receiver.domain)

        self.assertIsNone(receiver.created_at)
        self.assertIsNone(receiver.updated_at)

        self.assertEqual('FAKE_CLUSTER', receiver.cluster_id)
        self.assertEqual('test-action', receiver.action)
        self.assertEqual({}, receiver.actor)
        self.assertEqual({}, receiver.params)
        self.assertEqual({}, receiver.channel)

    def test_receiver_store(self):
        receiver = receiver_mod.Receiver('webhook', 'FAKE_CLUSTER',
                                         'test-action',
                                         project=self.context.project)
        self.assertIsNone(receiver.id)

        receiver_id = receiver.store(self.context)

        self.assertIsNotNone(receiver_id)
        self.assertEqual(receiver_id, receiver.id)

        result = db_api.receiver_get(self.context, receiver_id)

        self.assertIsNotNone(result)
        self.assertEqual(receiver_id, result.id)
        self.assertEqual(receiver.type, result.type)
        self.assertEqual(receiver.name, result.name)
        self.assertEqual(receiver.user, result.user)
        self.assertEqual(receiver.project, result.project)
        self.assertEqual(receiver.domain, result.domain)
        self.assertEqual(receiver.created_at, result.created_at)
        self.assertEqual(receiver.updated_at, result.updated_at)
        self.assertEqual(receiver.action, result.action)
        self.assertEqual(receiver.actor, result.actor)
        self.assertEqual(receiver.params, result.params)
        self.assertEqual(receiver.channel, result.channel)

    def test_receiver_create(self):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        receiver = receiver_mod.Receiver.create(
            self.context, 'webhook', cluster, 'FAKE_ACTION')

        self.assertEqual(self.context.user, receiver.user)
        self.assertEqual(self.context.project, receiver.project)
        self.assertEqual(self.context.domain, receiver.domain)

    def _verify_receiver(self, receiver, result):
        self.assertEqual(receiver.id, result.id)
        self.assertEqual(receiver.name, result.name)
        self.assertEqual(receiver.type, result.type)
        self.assertEqual(receiver.user, result.user)
        self.assertEqual(receiver.project, result.project)
        self.assertEqual(receiver.domain, result.domain)

        self.assertEqual(receiver.created_at, result.created_at)
        self.assertEqual(receiver.updated_at, result.updated_at)

        self.assertEqual(receiver.cluster_id, result.cluster_id)
        self.assertEqual(receiver.actor, result.actor)
        self.assertEqual(receiver.action, result.action)
        self.assertEqual(receiver.params, result.params)
        self.assertEqual(receiver.channel, result.channel)

    def test_receiver_load_with_id(self):
        receiver = self._create_receiver('receiver-1', 'FAKE_ID')
        result = receiver_mod.Receiver.load(self.context,
                                            receiver_id=receiver.id)
        self._verify_receiver(receiver, result)

    def test_receiver_load_with_object(self):
        receiver = self._create_receiver('receiver-1', 'FAKE_ID')
        result = receiver_mod.Receiver.load(self.context,
                                            receiver_obj=receiver)
        self._verify_receiver(receiver, result)

    def test_receiver_load_not_found(self):
        ex = self.assertRaises(exception.ReceiverNotFound,
                               receiver_mod.Receiver.load,
                               self.context, 'fake-receiver', None)
        self.assertEqual('The receiver (fake-receiver) could not be found.',
                         six.text_type(ex))

    def test_receiver_load_diff_project(self):
        receiver = self._create_receiver('receiver-1', 'FAKE_ID')

        new_context = utils.dummy_context(project='a-different-project')
        ex = self.assertRaises(exception.ReceiverNotFound,
                               receiver_mod.Receiver.load,
                               new_context, 'FAKE_ID', None)
        self.assertEqual('The receiver (FAKE_ID) could not be found.',
                         six.text_type(ex))

        res = receiver_mod.Receiver.load(new_context, receiver.id,
                                         project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(receiver.id, res.id)

    def test_receiver_load_all(self):
        result = receiver_mod.Receiver.load_all(self.context)
        self.assertEqual([], [w for w in result])

        receiver1 = self._create_receiver('receiver-1', 'ID1')
        receiver2 = self._create_receiver('receiver-2', 'ID2')

        result = receiver_mod.Receiver.load_all(self.context)
        receivers = [w for w in result]
        self.assertEqual(2, len(receivers))
        self.assertEqual(receiver1.id, receivers[0].id)
        self.assertEqual(receiver2.id, receivers[1].id)

    def test_receiver_load_all_diff_project(self):
        self._create_receiver('receiver-1', 'ID1')
        self._create_receiver('receiver-2', 'ID2')

        new_context = utils.dummy_context(project='a-different-project')
        result = receiver_mod.Receiver.load_all(new_context)
        self.assertEqual(0, len(list(result)))
        result = receiver_mod.Receiver.load_all(new_context,
                                                project_safe=False)
        self.assertEqual(2, len(list(result)))

    def test_receiver_to_dict(self):
        receiver = self._create_receiver('test-receiver', 'FAKE_ID')
        self.assertIsNotNone(receiver.id)
        expected = {
            'id': receiver.id,
            'name': receiver.name,
            'type': receiver.type,
            'user': receiver.user,
            'project': receiver.project,
            'domain': receiver.domain,
            'cluster_id': receiver.cluster_id,
            'action': receiver.action,
            'actor': receiver.actor,
            'params': receiver.params,
            'created_at': common_utils.format_time(receiver.created_at),
            'updated_at': receiver.updated_at,
            'channel': None,
        }

        result = receiver_mod.Receiver.load(self.context,
                                            receiver_id=receiver.id)
        self.assertEqual(expected, result.to_dict())


class TestWebhook(base.SenlinTestCase):

    def test_initialize_channel(self):
        cfg.CONF.set_override('host', 'web.com', 'webhook')
        cfg.CONF.set_override('port', '1234', 'webhook')
        webhook = receiver_mod.Webhook('webhook', 'FAKE_CLUSTER',
                                       'FAKE_ACTION', id='FAKE_ID')
        channel = webhook.initialize_channel()

        expected = {
            'alarm_url': ('http://web.com:1234/v1/webhooks/FAKE_ID/trigger'
                          '?V=1')
        }
        self.assertEqual(expected, channel)
        self.assertEqual(expected, webhook.channel)

    def test_initialize_channel_with_params(self):
        cfg.CONF.set_override('host', 'web.com', 'webhook')
        cfg.CONF.set_override('port', '1234', 'webhook')
        webhook = receiver_mod.Webhook(
            'webhook', 'FAKE_CLUSTER', 'FAKE_ACTION',
            id='FAKE_ID', params={'KEY': 884, 'FOO': 'BAR'})

        channel = webhook.initialize_channel()

        expected = {
            'alarm_url': ('http://web.com:1234/v1/webhooks/FAKE_ID/trigger'
                          '?V=1&FOO=BAR&KEY=884')
        }
        self.assertEqual(expected, channel)
        self.assertEqual(expected, webhook.channel)
