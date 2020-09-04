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

from unittest import mock

from oslo_config import cfg
from oslo_utils import uuidutils
import webob

from senlin.api.common import util as common_util
from senlin.api.common import version_request as vr
from senlin.api.middleware import webhook as webhook_middleware
from senlin.common import context
from senlin.common import exception
from senlin.drivers import base as driver_base
from senlin.rpc import client as rpc
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestWebhookMiddleware(base.SenlinTestCase):

    def setUp(self):
        super(TestWebhookMiddleware, self).setUp()
        self.ctx = utils.dummy_context()
        self.middleware = webhook_middleware.WebhookMiddleware(None)

        self.url_slices = {
            '00_url_base': 'http://HOST_IP:PORT/v1',
            '01_webhook_str': '/webhooks/',
            '02_webhook_id': 'WEBHOOK_ID',
            '03_trigger_str': '/trigger?',
            '04_version': 'V=2',
            '05_params': '&key=TEST_KEY',
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
        self.assertEqual(('WEBHOOK_ID', {'key': 'TEST_KEY'}), res)

    def test_parse_url_version_provided_no_key(self):
        # The structure /<webhook_id>/trigger?V=1 should be valid
        self.url_slices.pop('05_params')

        res = self.middleware._parse_url(self._generate_url())
        self.assertEqual(('WEBHOOK_ID', {}), res)

    def test_parse_url_no_version_provided_no_key_provided(self):
        # The structure /<webhook_id>/trigger should be invalid
        # because version is missing
        self.url_slices.pop('04_version')
        self.url_slices.pop('05_params')

        ex = self.assertRaises(webob.exc.HTTPBadRequest,
                               self.middleware._parse_url,
                               self._generate_url())

        self.assertEqual("V query parameter is required in webhook trigger "
                         "URL", str(ex))

    def test_parse_url_no_version_provided_key_provided(self):
        # The structure /<webhook_id>/trigger?key=value should be invalid
        # because version is missing
        self.url_slices.pop('04_version')
        self.url_slices.pop('05_params')
        self.url_slices['05_params'] = 'key=TEST_KEY'

        ex = self.assertRaises(webob.exc.HTTPBadRequest,
                               self.middleware._parse_url,
                               self._generate_url())

        self.assertEqual("V query parameter is required in webhook trigger "
                         "URL", str(ex))

    def test_parse_url_webhooks_not_found(self):
        # String 'webhooks' is not found in url
        self.url_slices['01_webhook_str'] = '/foo/'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_trigger_not_found(self):
        # String 'trigger' is not found in url
        self.url_slices['03_trigger_str'] = '/foo?'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_illegal_format(self):
        # The structure /<webhook_id>/trigger?key=value is not matched
        self.url_slices['03_trigger_str'] = 'trigger?'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

    def test_parse_url_no_trigger_word(self):
        # Bottom string of the url does not start with 'trigger'
        self.url_slices['03_trigger_str'] = '/foo-trigger?'
        res = self.middleware._parse_url(self._generate_url())
        self.assertIsNone(res)

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

    @mock.patch.object(common_util, 'parse_request')
    @mock.patch.object(context, 'RequestContext')
    @mock.patch.object(rpc, 'get_engine_client')
    def test_process_request(self, mock_client, mock_ctx, mock_parse):
        cfg.CONF.set_override('auth_url', 'AUTH_URL', group='authentication')
        cfg.CONF.set_override('service_username', 'USERNAME',
                              group='authentication')
        cfg.CONF.set_override('service_user_domain', 'DOMAIN',
                              group='authentication')
        cfg.CONF.set_override('service_project_domain', 'DOMAIN1',
                              group='authentication')
        cfg.CONF.set_override('service_password', 'PASSWORD',
                              group='authentication')
        cfg.CONF.set_override('verify_ssl', False,
                              group='authentication')
        cfg.CONF.set_override('interface', 'admin',
                              group='authentication')

        req = mock.Mock()
        req.method = 'POST'
        req.url = 'http://url1/v1'
        req.script_name = '/v1'
        req.params = {'key': 'FAKE_KEY'}
        req.headers = {}
        req.version_request = vr.APIVersionRequest('1.0')

        rpcc = mock.Mock()
        fake_receiver = {
            'id': 'FAKE_ID',
            'actor': {'foo': 'bar'}
        }
        rpcc.call.return_value = fake_receiver
        mock_client.return_value = rpcc
        dbctx = mock.Mock()
        mock_ctx.return_value = dbctx

        obj = mock.Mock()
        mock_parse.return_value = obj

        fake_return = ('WEBHOOK', {})
        mock_extract = self.patchobject(self.middleware, '_parse_url',
                                        return_value=fake_return)
        mock_token = self.patchobject(self.middleware, '_get_token',
                                      return_value='FAKE_TOKEN')

        res = self.middleware.process_request(req)
        self.assertIsNone(res)

        self.assertEqual('FAKE_TOKEN', req.headers['X-Auth-Token'])
        mock_extract.assert_called_once_with('http://url1/v1')
        mock_token.assert_called_once_with(
            auth_url='AUTH_URL', password='PASSWORD', username='USERNAME',
            user_domain_name='DOMAIN', foo='bar', verify=False,
            project_domain_name='DOMAIN1', interface='admin')

        mock_parse.assert_called_once_with('ReceiverGetRequest', req,
                                           {'identity': 'WEBHOOK'})
        rpcc.call.assert_called_with(dbctx, 'receiver_get', obj)

    def test_process_request_method_not_post(self):
        # Request method is not POST
        req = mock.Mock()
        req.method = 'GET'
        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        self.assertNotIn('X-Auth-Token', req.headers)

    def test_process_request_bad_format(self):
        # no webhook_id extracted
        req = mock.Mock()
        req.method = 'POST'
        req.url = 'http://url1/v1'
        req.script_name = '/v1'
        mock_extract = self.patchobject(self.middleware, '_parse_url',
                                        return_value=None)

        res = self.middleware.process_request(req)
        self.assertIsNone(res)
        mock_extract.assert_called_once_with(req.url)
        self.assertNotIn('X-Auth-Token', req.headers)

    def test_parse_url_valid(self):
        uid = uuidutils.generate_uuid()

        result = self.middleware._parse_url(
            'https://url1/cluster/v1/webhooks/%s/trigger?V=2&k=v' % uid
        )

        self.assertEqual(
            (uid, {'k': 'v'}), result
        )

    def test_parse_url_valid_with_port(self):
        uid = uuidutils.generate_uuid()

        result = self.middleware._parse_url(
            'http://url1:5000/v1/webhooks/%s/trigger?V=2&k=v' % uid
        )

        self.assertEqual(
            (uid, {'k': 'v'}), result
        )

    def test_parse_url_invalid(self):
        result = self.middleware._parse_url(
            'http://url1'
        )

        self.assertIsNone(result)

    def test_parse_url_missing_version(self):
        uid = uuidutils.generate_uuid()

        result = self.middleware._parse_url(
            'https://url1/cluster/webhooks/%s/trigger?V=2&k=v' % uid
        )

        self.assertIsNone(result)

    def test_parse_url_missing_webhooks(self):
        uid = uuidutils.generate_uuid()

        result = self.middleware._parse_url(
            'https://url1/cluster/v1/%s/trigger?V=2&k=v' % uid
        )

        self.assertIsNone(result)
