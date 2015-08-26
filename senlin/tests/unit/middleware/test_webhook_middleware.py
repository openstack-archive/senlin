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
from oslo_serialization import jsonutils
from oslo_utils import timeutils

from senlin.api.middleware import webhook as webhook_middleware
from senlin.common import exception
from senlin.common import policy
from senlin.drivers import base as driver_base
from senlin.engine import webhook as webhook_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestWebhookMiddleware(base.SenlinTestCase):

    def setUp(self):
        super(TestWebhookMiddleware, self).setUp()
        self.ctx = utils.dummy_context()
        self.middleware = webhook_middleware.WebhookMiddleware(None)

        self.url_slices = {
            '00_url_base': 'http://HOST_IP:PORT/v1/',
            '01_tenant_id': 'TENANT_ID',
            '02_webhook_str': '/webhooks/',
            '03_webhook_id': 'WEBHOOK_ID',
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
        slices = sorted(self.url_slices.items(), key=lambda d: d[0])
        return ''.join(s[1] for s in slices)

    def test_parse_url(self):
        # Get webhook_id correctly
        res = self.middleware._parse_url(self._generate_url())
        self.assertEqual(('TENANT_ID', 'WEBHOOK_ID', 'TEST_KEY'), res)

    def test_parse_url_webhooks_not_found(self):
        # String 'webhooks' is not found in url
        self.url_slices['02_webhook_str'] = '/foo/'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_trigger_not_found(self):
        # String 'trigger' is not found in url
        self.url_slices['04_trigger_str'] = '/foo?'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_illegal_format(self):
        # The structure /<webhook_id>/trigger?key=value is not matched
        self.url_slices['04_trigger_str'] = 'trigger?'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_no_trigger_word(self):
        # Bottom string of the url does not start with 'trigger'
        self.url_slices['04_trigger_str'] = '/foo-trigger?'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_no_key_provided(self):
        # Bottom string of the url does not start with 'trigger'
        self.url_slices['05_key_str'] = 'secret='
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

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
                                      'test-action', context=self.ctx,
                                      **kwargs)
        key = webhook.encrypt_credential()
        webhook.store(self.ctx)

        # User credential can be got correctly if valid key is provided
        res = self.middleware._get_credential(self.ctx.project,
                                              webhook.id, key)
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
                                      'test-action', context=self.ctx,
                                      **kwargs)
        webhook.encrypt_credential()
        webhook.store(self.ctx)

        # Credential getting failed for invalid key provided
        self.assertRaises(exception.Forbidden, self.middleware._get_credential,
                          self.ctx.project, webhook.id, 'fake-key')

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_get_token_succeeded(self, mock_senlindriver):
        class FakeAccessInfo(object):
            def __init__(self, auth_token):
                self.auth_token = auth_token

        sd = mock.Mock()
        sd.identity.get_token.return_value = 'TEST_TOKEN'
        mock_senlindriver.return_value = sd

        token = self.middleware._get_token(**self.credential)
        self.assertEqual('TEST_TOKEN', token)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_get_token_failed(self, mock_senlindriver):
        self.credential['webhook_id'] = 'WEBHOOK_ID'

        sd = mock.Mock()
        sd.identity.get_token.side_effect = Exception()
        mock_senlindriver.return_value = sd

        self.assertRaises(exception.Forbidden, self.middleware._get_token,
                          **self.credential)

    def test_process_request(self):
        req = mock.Mock()
        req.method = 'POST'
        req.url = 'http://url1'
        req.params = {'key': 'FAKE_KEY'}
        req.headers = {}
        cfg.CONF.set_override('auth_url', 'AUTH_URL', group='authentication')
        cfg.CONF.set_override('service_username', 'USERNAME',
                              group='authentication')
        cfg.CONF.set_override('service_user_domain', 'DOMAIN',
                              group='authentication')
        cfg.CONF.set_override('service_password', 'PASSWORD',
                              group='authentication')

        fake_return = ('TENANT', 'WEBHOOK', 'FAKE_KEY')
        mock_extract = self.patchobject(self.middleware, '_parse_url',
                                        return_value=fake_return)
        mock_cred = self.patchobject(self.middleware, '_get_credential',
                                     return_value={'KEY': 'VAL'})
        mock_token = self.patchobject(self.middleware, '_get_token',
                                      return_value='FAKE_TOKEN')

        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        self.assertEqual('FAKE_TOKEN', req.headers['X-Auth-Token'])
        mock_extract.assert_called_once_with('http://url1')
        mock_cred.assert_called_once_with('TENANT', 'WEBHOOK', 'FAKE_KEY')
        mock_token.assert_called_once_with(
            auth_url='AUTH_URL', password='PASSWORD', username='USERNAME',
            KEY='VAL', user_domain_name='DOMAIN')

    def test_process_request_method_not_post(self):
        # Request method is not POST
        req = mock.Mock()
        req.method = 'GET'
        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        self.assertNotIn('X-Auth-Token', req.headers)

    def test_process_request_no_webhook_id(self):
        # no webhook_id extracted
        req = mock.Mock()
        req.method = 'POST'
        req.url = 'http://url1'
        mock_extract = self.patchobject(self.middleware, '_parse_url',
                                        return_value=None)

        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        mock_extract.assert_called_once_with(req.url)
        self.assertNotIn('X-Auth-Token', req.headers)

    def test_process_request_no_credential(self):
        req = mock.Mock()
        req.method = 'POST'
        req.url = 'http://url1'
        req.params = {'key': 'FAKE_KEY'}
        req.headers = {}
        fake_return = ('TENANT_ID', 'WEBHOOK_ID', 'TEST_KEY')
        mock_extract = self.patchobject(self.middleware, '_parse_url',
                                        return_value=fake_return)
        mock_cred = self.patchobject(self.middleware, '_get_credential',
                                     return_value=None)

        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        mock_extract.assert_called_once_with(req.url)
        mock_cred.assert_called_once_with('TENANT_ID', 'WEBHOOK_ID',
                                          'TEST_KEY')
        self.assertNotIn('X-Auth-Token', req.headers)
