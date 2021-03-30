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

from webob import exc

from oslo_serialization import jsonutils

from senlin.api.openstack.v1 import webhooks
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class WebhookControllerBaseTest(shared.ControllerTest, base.SenlinTestCase):
    WEBHOOK_VERSION = '1'
    WEBHOOK_API_MICROVERSION = '1.0'

    def setUp(self):
        super(WebhookControllerBaseTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8777

        cfgopts = DummyConfig()
        self.controller = webhooks.WebhookController(options=cfgopts)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = None
        webhook_id = 'test_webhook_id'
        action_id = 'test_action_id'

        engine_response = {
            'action': action_id,
        }

        req = self._post('/webhooks/test_webhook_id/trigger',
                         jsonutils.dumps(body),
                         version=self.WEBHOOK_API_MICROVERSION,
                         params={'V': self.WEBHOOK_VERSION})
        mock_call.return_value = engine_response

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=None)

        self.assertEqual(action_id, resp['action'])
        self.assertEqual('/actions/test_action_id', resp['location'])

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_with_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = {'params': {'key': 'value'}}
        webhook_id = 'test_webhook_id'

        engine_response = {'action': 'FAKE_ACTION'}

        req = self._post('/webhooks/test_webhook_id/trigger',
                         jsonutils.dumps(body),
                         version=self.WEBHOOK_API_MICROVERSION,
                         params={'V': self.WEBHOOK_VERSION})
        mock_call.return_value = engine_response

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=body)

        self.assertEqual('FAKE_ACTION', resp['action'])
        self.assertEqual('/actions/FAKE_ACTION', resp['location'])


class WebhookV1ControllerInvalidParamsTest(WebhookControllerBaseTest):
    WEBHOOK_VERSION = '1'
    WEBHOOK_API_MICROVERSION = '1.0'

    @mock.patch.object(policy, 'enforce')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_invalid_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        webhook_id = 'fake'
        body = {"bad": "boo"}
        req = self._patch('/webhooks/{}/trigger'.format(webhook_id),
                          jsonutils.dumps(body),
                          version=self.WEBHOOK_API_MICROVERSION,
                          params={'V': self.WEBHOOK_VERSION})

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.trigger,
                               req, webhook_id=webhook_id, body=body)

        self.assertEqual(
            "Additional properties are not allowed ('bad' was unexpected)",
            str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(policy, 'enforce')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_invalid_json(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        webhook_id = 'fake'
        body = {"params": "boo"}
        req = self._patch('/webhooks/{}/trigger'.format(webhook_id),
                          jsonutils.dumps(body),
                          version=self.WEBHOOK_API_MICROVERSION,
                          params={'V': self.WEBHOOK_VERSION})

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.trigger,
                               req, webhook_id=webhook_id, body=body)
        self.assertEqual("The value (boo) is not a valid JSON.",
                         str(ex))
        self.assertFalse(mock_call.called)


class WebhookV1ControllerValidParamsTest(WebhookControllerBaseTest):
    WEBHOOK_VERSION = '1'
    WEBHOOK_API_MICROVERSION = '1.10'

    @mock.patch.object(policy, 'enforce')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_extra_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        webhook_id = 'fake'
        body = {"bad": "boo"}
        engine_response = {'action': 'FAKE_ACTION'}
        mock_call.return_value = engine_response
        req = self._patch('/webhooks/{}/trigger'.format(webhook_id),
                          jsonutils.dumps(body),
                          version=self.WEBHOOK_API_MICROVERSION,
                          params={'V': self.WEBHOOK_VERSION})

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=body)

        self.assertEqual('FAKE_ACTION', resp['action'])
        self.assertEqual('/actions/FAKE_ACTION', resp['location'])

    @mock.patch.object(policy, 'enforce')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_non_json_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        webhook_id = 'fake'
        body = {"params": "boo"}
        engine_response = {'action': 'FAKE_ACTION'}
        mock_call.return_value = engine_response
        req = self._patch('/webhooks/{}/trigger'.format(webhook_id),
                          jsonutils.dumps(body),
                          version=self.WEBHOOK_API_MICROVERSION,
                          params={'V': self.WEBHOOK_VERSION})

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=body)

        self.assertEqual('FAKE_ACTION', resp['action'])
        self.assertEqual('/actions/FAKE_ACTION', resp['location'])


class WebhookV2ControllerTest(WebhookV1ControllerValidParamsTest):
    WEBHOOK_VERSION = '2'
    WEBHOOK_API_MICROVERSION = '1.0'


class WebhookV2_110_ControllerTest(WebhookV1ControllerValidParamsTest):
    WEBHOOK_VERSION = '2'
    WEBHOOK_API_MICROVERSION = '1.10'
