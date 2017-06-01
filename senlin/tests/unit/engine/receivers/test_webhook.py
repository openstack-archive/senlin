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

from senlin.engine.receivers import webhook as wmod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'
UUID1 = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'
UUID2 = '60efdaa1-06c2-4fcf-ae44-17a2d85ff3ea'


class TestWebhook(base.SenlinTestCase):
    def setUp(self):
        super(TestWebhook, self).setUp()
        self.context = utils.dummy_context()

    def test_initialize_channel_host_provided(self):
        cfg.CONF.set_override('host', 'web.com', 'receiver')
        cfg.CONF.set_override('port', '1234', 'receiver')
        webhook = wmod.Webhook('webhook', CLUSTER_ID, 'FAKE_ACTION',
                               id=UUID1)
        channel = webhook.initialize_channel(self.context)

        expected = {
            'alarm_url': ('http://web.com:1234/v1/webhooks/%s/trigger'
                          '?V=1' % UUID1)
        }
        self.assertEqual(expected, channel)
        self.assertEqual(expected, webhook.channel)

    @mock.patch.object(wmod.Webhook, "_get_base_url")
    def test_initialize_channel_host_not_provided(self, mock_get_base_url):
        mock_get_base_url.return_value = 'http://web.com:1234/v1'
        webhook = wmod.Webhook('webhook', CLUSTER_ID, 'FAKE_ACTION',
                               id=UUID1)
        channel = webhook.initialize_channel(self.context)

        expected = {
            'alarm_url': ('http://web.com:1234/v1/webhooks/%s/trigger'
                          '?V=1' % UUID1)
        }
        self.assertEqual(expected, channel)
        self.assertEqual(expected, webhook.channel)

    @mock.patch.object(socket, "gethostname")
    @mock.patch.object(wmod.Webhook, "_get_base_url")
    def test_initialize_channel_no_host_no_base(self, mock_get_base_url,
                                                mock_gethostname):
        mock_get_base_url.return_value = None
        mock_gethostname.return_value = 'test-host'
        webhook = wmod.Webhook('webhook', CLUSTER_ID, 'FAKE_ACTION',
                               id=UUID1)
        channel = webhook.initialize_channel(self.context)

        expected = {
            'alarm_url': ('http://test-host:8778/v1/webhooks/%s/trigger'
                          '?V=1' % UUID1)
        }
        self.assertEqual(expected, channel)
        self.assertEqual(expected, webhook.channel)

    def test_initialize_channel_with_params(self):
        cfg.CONF.set_override('host', 'web.com', 'receiver')
        cfg.CONF.set_override('port', '1234', 'receiver')
        webhook = wmod.Webhook(
            'webhook', CLUSTER_ID, 'FAKE_ACTION',
            id=UUID1, params={'KEY': 884, 'FOO': 'BAR'})

        channel = webhook.initialize_channel(self.context)

        expected = {
            'alarm_url': ('http://web.com:1234/v1/webhooks/%s/trigger'
                          '?V=1&FOO=BAR&KEY=884' % UUID1)
        }
        self.assertEqual(expected, channel)
        self.assertEqual(expected, webhook.channel)
