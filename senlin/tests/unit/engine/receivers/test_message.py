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
import socket

from oslo_config import cfg

from senlin.common import exception
from senlin.drivers import base as driver_base
from senlin.engine.receivers import message as mmod
from senlin.tests.unit.common import base

UUID = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'


class TestMessage(base.SenlinTestCase):

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_zaqar_client(self, mock_senlindriver):
        sd = mock.Mock()
        zc = mock.Mock()
        sd.message.return_value = zc
        mock_senlindriver.return_value = sd

        message = mmod.Message('message', None, None, user='user1',
                               project='project1')

        # cached will be returned
        message._zaqarclient = zc
        self.assertEqual(zc, message.zaqar())

        # new zaqar client created if no cache found
        message._zaqarclient = None
        params = mock.Mock()
        mock_param = self.patchobject(mmod.Message, '_build_conn_params',
                                      return_value=params)
        res = message.zaqar()
        self.assertEqual(zc, res)
        self.assertEqual(zc, message._zaqarclient)
        mock_param.assert_called_once_with('user1', 'project1')
        sd.message.assert_called_once_with(params)

    def test__generate_subscriber_url_host_provided(self):
        cfg.CONF.set_override('host', 'web.com', 'webhook')
        cfg.CONF.set_override('port', '1234', 'webhook')
        message = mmod.Message('message', None, None, id=UUID)
        res = message._generate_subscriber_url()

        expected = 'trust+http://web.com:1234/v1/receivers/%s/notify' % UUID
        self.assertEqual(expected, res)

    @mock.patch.object(mmod.Message, '_get_base_url')
    def test__generate_subscriber_url_host_not_provided(
            self, mock_get_base_url):
        mock_get_base_url.return_value = 'http://web.com:1234/v1'
        message = mmod.Message('message', None, None, id=UUID)
        res = message._generate_subscriber_url()

        expected = 'trust+http://web.com:1234/v1/receivers/%s/notify' % UUID
        self.assertEqual(expected, res)

    @mock.patch.object(socket, 'gethostname')
    @mock.patch.object(mmod.Message, '_get_base_url')
    def test__generate_subscriber_url_no_host_no_base(
            self, mock_get_base_url, mock_gethostname):
        mock_get_base_url.return_value = None
        mock_gethostname.return_value = 'test-host'
        message = mmod.Message('message', None, None, id=UUID)
        res = message._generate_subscriber_url()

        expected = 'trust+http://test-host:8778/v1/receivers/%s/notify' % UUID
        self.assertEqual(expected, res)

    def test_to_dict(self):
        message = mmod.Message('message', None, None, user='user1',
                               project='project1', id=UUID)
        message.channel = {'queue_name': 'test-queue',
                           'subscription': 'subscription-id'}
        res = message.to_dict()
        expected_res = {
            'name': None,
            'id': UUID,
            'user': 'user1',
            'project': 'project1',
            'domain': '',
            'type': 'message',
            'channel': {'queue_name': 'test-queue'},
            'action': None,
            'cluster_id': None,
            'actor': {},
            'params': {},
            'created_at': None,
            'updated_at': None,
        }
        self.assertEqual(expected_res, res)

    @mock.patch.object(mmod.Message, '_create_queue')
    @mock.patch.object(mmod.Message, '_generate_subscriber_url')
    @mock.patch.object(mmod.Message, '_create_subscription')
    def test_initialize_channel(self, mock_create_subscription,
                                mock_generate_subscriber_url,
                                mock_create_queue):
        mock_sub = mock.Mock()
        mock_sub.subscription_id = 'test-subscription-id'
        mock_create_subscription.return_value = mock_sub
        mock_generate_subscriber_url.return_value = 'SUBSCRIBER_URL'
        mock_create_queue.return_value = 'test-queue'

        message = mmod.Message('message', None, None)
        res = message.initialize_channel()

        expected_channel = {'queue_name': 'test-queue',
                            'subscription': 'test-subscription-id'}
        self.assertEqual(expected_channel, res)
        mock_create_queue.assert_called_once_with()
        mock_generate_subscriber_url.assert_called_once_with()
        mock_create_subscription.assert_called_once_with('test-queue',
                                                         'SUBSCRIBER_URL')

    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_queue(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'senlin-receiver-%s' % message.id
        kwargs = {
            '_max_messages_post_size': 262144,
            '_default_message_ttl': 3600,
            'description': 'Queue for Senlin receiver.',
            'name': queue_name
        }
        mock_zc.queue_create.return_value = queue_name
        res = message._create_queue()

        self.assertEqual(queue_name, res)
        mock_zc.queue_create.assert_called_once_with(**kwargs)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_queue_fail(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'senlin-receiver-%s' % message.id
        kwargs = {
            '_max_messages_post_size': 262144,
            '_default_message_ttl': 3600,
            'description': 'Queue for Senlin receiver.',
            'name': queue_name
        }
        mock_zc.queue_create.side_effect = exception.InternalError()
        self.assertRaises(exception.EResourceCreation, message._create_queue)
        mock_zc.queue_create.assert_called_once_with(**kwargs)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_subscription(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'test-queue'
        subscriber = 'subscriber_url'
        kwargs = {
            "ttl": 3600,
            "subscriber": subscriber,
            "options": {
                "from": "senlin and zaqar",
                "subject": "hello, senlin"
            }
        }
        mock_zc.subscription_create.return_value = 'subscription'
        res = message._create_subscription(queue_name, subscriber)

        self.assertEqual('subscription', res)
        mock_zc.subscription_create.assert_called_once_with(queue_name,
                                                            **kwargs)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_subscription_fail(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'test-queue'
        subscriber = 'subscriber_url'
        kwargs = {
            "ttl": 3600,
            "subscriber": subscriber,
            "options": {
                "from": "senlin and zaqar",
                "subject": "hello, senlin"
            }
        }

        mock_zc.subscription_create.side_effect = exception.InternalError()
        self.assertRaises(exception.EResourceCreation,
                          message._create_subscription,
                          queue_name, subscriber)
        mock_zc.subscription_create.assert_called_once_with(queue_name,
                                                            **kwargs)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_release_channel(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        channel = {'queue_name': 'test-queue',
                   'subscription': 'test-subscription-id'}
        message = mmod.Message('message', None, None, id=UUID,
                               channel=channel)

        message.release_channel()
        mock_zc.subscription_delete.assert_called_once_with(
            'test-queue', 'test-subscription-id')
        mock_zc.queue_delete.assert_called_once_with('test-queue')

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_release_channel_subscription_delete_fail(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        channel = {'queue_name': 'test-queue',
                   'subscription': 'test-subscription-id'}
        message = mmod.Message('message', None, None, id=UUID,
                               channel=channel)
        mock_zc.subscription_delete.side_effect = exception.InternalError()

        self.assertRaises(exception.EResourceDeletion,
                          message.release_channel)
        mock_zc.subscription_delete.assert_called_once_with(
            'test-queue', 'test-subscription-id')

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_release_channel_queue_delete_fail(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        channel = {'queue_name': 'test-queue',
                   'subscription': 'test-subscription-id'}
        message = mmod.Message('message', None, None, id=UUID,
                               channel=channel)
        mock_zc.queue_delete.side_effect = exception.InternalError()

        self.assertRaises(exception.EResourceDeletion,
                          message.release_channel)
        mock_zc.subscription_delete.assert_called_once_with(
            'test-queue', 'test-subscription-id')
        mock_zc.queue_delete.assert_called_once_with('test-queue')
