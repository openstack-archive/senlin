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

    def test_webhook_trigger(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = None
        webhook_id = 'test_webhook_id'
        action_id = 'test_action_id'

        engine_response = {
            'action': action_id,
        }

        req = self._post('/webhooks/test_webhook_id/trigger',
                         jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=None)

        mock_call.assert_called_with(
            req.context,
            ('webhook_trigger', {
                'params': None,
                'identity': webhook_id,
            })
        )

        expected = engine_response
        location = {'location': '/actions/test_action_id'}
        expected.update(location)
        self.assertEqual(expected, resp)

    def test_webhook_trigger_with_params(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'trigger', True)
        body = {'params': {'key': 'value'}}
        webhook_id = 'test_webhook_id'

        engine_response = {'action': 'FAKE_ACTION'}

        req = self._post('/webhooks/test_webhook_id/trigger',
                         jsonutils.dumps(body))
        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_response)

        resp = self.controller.trigger(req, webhook_id=webhook_id, body=body)

        mock_call.assert_called_with(req.context,
                                     ('webhook_trigger',
                                      {'params': {'key': 'value'},
                                       'identity': webhook_id}))

        expected = engine_response
        self.assertEqual(expected, resp)
