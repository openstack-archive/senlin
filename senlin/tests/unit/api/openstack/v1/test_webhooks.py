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
import six
from webob import exc

from oslo_serialization import jsonutils

from senlin.api.common import util
from senlin.api.openstack.v1 import webhooks
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class WebhookControllerTest(shared.ControllerTest, base.SenlinTestCase):
    def setUp(self):
        super(WebhookControllerTest, self).setUp()

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = webhooks.WebhookController(options=cfgopts)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger(self, mock_call, mock_parse, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = None
        webhook_id = 'test_webhook_id'
        action_id = 'test_action_id'

        engine_response = {
            'action': action_id,
        }

        req = self._post('/webhooks/test_webhook_id/trigger',
                         jsonutils.dumps(body))
        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=None)

        self.assertEqual(action_id, resp['action'])
        self.assertEqual('/actions/test_action_id', resp['location'])
        mock_parse.assert_called_once_with(
            'WebhookTriggerRequest', req, mock.ANY)
        mock_call.assert_called_once_with(req.context, 'webhook_trigger', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_with_params(self, mock_call, mock_parse,
                                         mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = {'params': {'key': 'value'}}
        webhook_id = 'test_webhook_id'

        engine_response = {'action': 'FAKE_ACTION'}

        req = self._post('/webhooks/test_webhook_id/trigger',
                         jsonutils.dumps(body))
        mock_call.return_value = engine_response
        obj = mock.Mock()
        mock_parse.return_value = obj

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=body)

        self.assertEqual('FAKE_ACTION', resp['action'])
        self.assertEqual('/actions/FAKE_ACTION', resp['location'])
        mock_parse.assert_called_once_with(
            'WebhookTriggerRequest', req, mock.ANY)
        mock_call.assert_called_once_with(req.context, 'webhook_trigger', obj)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_invalid_params(self, mock_call, mock_parse,
                                            mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        webhook_id = 'fake'
        body = {"bad": "boo"}
        req = self._patch('/webhooks/%s/trigger' % webhook_id,
                          jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("bad param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.trigger,
                               req, webhook_id=webhook_id, body=body)

        self.assertEqual("bad param", six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(util, 'parse_request')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_webhook_trigger_invalid_json(self, mock_call, mock_parse,
                                          mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        webhook_id = 'fake'
        body = {"params": "boo"}
        req = self._patch('/webhooks/%s/trigger' % webhook_id,
                          jsonutils.dumps(body))

        mock_parse.side_effect = exc.HTTPBadRequest("invalid param")
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.trigger,
                               req, webhook_id=webhook_id, body=body)
        self.assertEqual("invalid param", six.text_type(ex))
        self.assertFalse(mock_call.called)
