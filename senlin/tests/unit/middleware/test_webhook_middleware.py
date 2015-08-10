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

from oslo_serialization import jsonutils
from oslo_utils import timeutils

from senlin.api.middleware import webhook as webhook_middleware
from senlin.common import context
from senlin.common import exception
from senlin.common import policy
from senlin.drivers.openstack import keystone_v3
from senlin.engine import webhook as webhook_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

'''
A valid webhook_url looks like this:

    http://172.16.100.85:8778/v1/<TENANT_ID>/webhooks/<WEBHOOK_ID>/trigger?\
    key=<KEY>
'''


class TestWebhookMiddleware(base.SenlinTestCase):

    def setUp(self):
        super(TestWebhookMiddleware, self).setUp()
        self.context = utils.dummy_context()
        self.middleware = webhook_middleware.WebhookMiddleware(None)

        self.url_slices = {
            '00_url_base': 'http://HOST_IP:PORT/v1/',
            '01_tenant_id': 'TEST_TENANT_ID',
            '02_webhook_str': '/webhooks/',
            '03_webhook_id': 'TEST_WEBHOOK_ID',
            '04_trigger_str': '/trigger?',
            '05_key_str': 'key=',
            '06_key': 'TEST_KEY',
        }
        self.credential = {
            'auth_url': 'TEST_URL',
            'user_id': '123',
            'password': 'abc'
        }

    def _generate_url(self):
        url_slices = sorted(self.url_slices.items(), key=lambda d: d[0],
                            reverse=False)
        return ''.join([s[1] for s in url_slices])

    def test_extract_webhook_id(self):

        # Get webhook_id correctly
        res = self.middleware._extract_webhook_id(self._generate_url())
        self.assertEqual(self.url_slices['03_webhook_id'], res)

        # String 'webhooks' is not found in url
        self.url_slices['02_webhook_str'] = '/foo/'
        res = self.middleware._extract_webhook_id(self._generate_url())
        self.assertIsNone(res)
        self.url_slices['02_webhook_str'] = '/webhooks/'

        # String 'trigger' is not found in url
        self.url_slices['04_trigger_str'] = '/foo?'
        res = self.middleware._extract_webhook_id(self._generate_url())
        self.assertIsNone(res)
        self.url_slices['04_trigger_str'] = '/trigger?'

        # The structure /<webhook_id>/trigger?key=value is not matched
        self.url_slices['02_webhook_str'] = '/webhook'
        res = self.middleware._extract_webhook_id(self._generate_url())
        self.assertIsNone(res)
        self.url_slices['02_webhook_str'] = '/webhooks/'

        # Bottom string of the url does not start with 'trigger'
        self.url_slices['04_trigger_str'] = '/foo-trigger?'
        res = self.middleware._extract_webhook_id(self._generate_url())
        self.assertIsNone(res)
        self.url_slices['04_trigger_str'] = '/trigger?'

    @mock.patch.object(policy, 'enforce')
    def test_get_credential_succeed(self, mock_enforce):
        kwargs = {
            'id': None,
            'name': 'test-webhook',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': jsonutils.dumps(self.credential),
            'params': {}
        }
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', context=self.context,
                                      **kwargs)
        key = webhook.encrypt_credential()
        webhook.store(self.context)

        # User credential can be got correctly if valid key is provided
        res = self.middleware._get_credential(webhook.id, key)
        self.assertEqual('123', res['user_id'])
        self.assertEqual('abc', res['password'])
        self.assertEqual('TEST_URL', res['auth_url'])

    @mock.patch.object(policy, 'enforce')
    def test_get_credential_failed(self, mock_enforce):
        kwargs = {
            'id': None,
            'name': 'test-webhook',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': jsonutils.dumps(self.credential),
            'params': {}
        }
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', context=self.context,
                                      **kwargs)
        webhook.encrypt_credential()
        webhook.store(self.context)

        # Credential getting failed for invalid key provided
        self.assertRaises(exception.Forbidden, self.middleware._get_credential,
                          webhook.id, 'fake-key')

    @mock.patch.object(policy, 'enforce')
    def test_get_credential_auth_url_missing(self, mock_enforce):
        self.credential.pop('auth_url')
        kwargs = {
            'id': None,
            'name': 'test-webhook',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': jsonutils.dumps(self.credential),
            'params': {}
        }
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', context=self.context,
                                      **kwargs)
        key = webhook.encrypt_credential()
        webhook.store(self.context)

        # Auth_url of service context will be used if it is not
        # provided within credential
        service_context = context.get_service_context()
        expected_auth_url = service_context['auth_url']
        res = self.middleware._get_credential(webhook.id, key)
        self.assertEqual(expected_auth_url, res['auth_url'])

    @mock.patch.object(keystone_v3, 'get_token')
    def test_get_token_succeeded(self, mock_get_token):
        class FakeAccessInfo(object):
            def __init__(self, auth_token):
                self.auth_token = auth_token

        mock_get_token.return_value = 'TEST_TOKEN'

        token = self.middleware._get_token(self.credential)
        self.assertEqual('TEST_TOKEN', token)

    @mock.patch.object(keystone_v3, 'get_token')
    def test_get_token_failed(self, mock_get_token):
        self.credential['webhook_id'] = 'WEBHOOK_ID'
        mock_get_token.side_effect = Exception()

        self.assertRaises(exception.Forbidden, self.middleware._get_token,
                          self.credential)

    @mock.patch.object(webhook_middleware.WebhookMiddleware, '_get_token')
    @mock.patch.object(policy, 'enforce')
    def test_process_request(self, mock_enforce, mock_get_token):
        mock_get_token.return_value = 'TEST_TOKEN'
        kwargs = {
            'id': None,
            'name': 'test-webhook',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': jsonutils.dumps(self.credential),
            'params': {}
        }
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', context=self.context,
                                      **kwargs)
        key = webhook.encrypt_credential()
        webhook.store(self.context)
        req = mock.Mock()

        # Request method is not POST
        req.method = 'GET'
        req.params = {'key': key}
        req.headers = {}
        req.url = self._generate_url().replace('TEST_WEBHOOK_ID', webhook.id)
        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        self.assertNotIn('X-Auth-Token', req.headers)

        # Parameter 'key' is not provided
        req.method = 'POST'
        req.params = {}
        req.headers = {}
        req.url = self._generate_url().replace('TEST_WEBHOOK_ID', webhook.id)
        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        self.assertNotIn('X-Auth-Token', req.headers)

        # Get token successfully
        req.method = 'POST'
        req.params = {'key': key}
        req.headers = {}
        req.url = self._generate_url().replace('TEST_WEBHOOK_ID', webhook.id)
        res = self.middleware.process_request(req)
        self.assertEqual('TEST_TOKEN', req.headers['X-Auth-Token'])
