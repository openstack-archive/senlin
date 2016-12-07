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

from senlin.objects.requests import webhooks
from senlin.tests.unit.common import base as test_base


class TestWebhookTrigger(test_base.SenlinTestCase):

    def test_webhook_trigger_body_none(self):
        sot = webhooks.WebhookTriggerRequestBody(params=None)
        self.assertIsNone(sot.params)

    def test_webhook_trigger_body(self):
        sot = webhooks.WebhookTriggerRequestBody(params={'foo': 'boo'})
        self.assertEqual({'foo': 'boo'}, sot.params)

    def test_webhook_trigger_body_to_primitive(self):
        sot = sot = webhooks.WebhookTriggerRequestBody(params={'foo': 'boo'})
        res = sot.obj_to_primitive()
        self.assertIn('params', res['senlin_object.changes'])
        self.assertEqual({'params': '{"foo": "boo"}'},
                         res['senlin_object.data'])
        self.assertEqual(
            'WebhookTriggerRequestBody', res['senlin_object.name'])
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertEqual('senlin', res['senlin_object.namespace'])

    def test_webhook_trigger_none_param(self):
        body = webhooks.WebhookTriggerRequestBody(params=None)
        sot = webhooks.WebhookTriggerRequest(identity='fake', params=body)
        self.assertEqual('fake', sot.identity)
        self.assertIsInstance(sot.params, webhooks.WebhookTriggerRequestBody)

    def test_webhook_trigger(self):
        body = webhooks.WebhookTriggerRequestBody(params={'foo': 'boo'})
        sot = webhooks.WebhookTriggerRequest(identity='fake', params=body)
        self.assertEqual('fake', sot.identity)
        self.assertIsInstance(sot.params, webhooks.WebhookTriggerRequestBody)

    def test_webhook_trigger_to_primitive(self):
        body = webhooks.WebhookTriggerRequestBody(params={'foo': 'boo'})
        sot = webhooks.WebhookTriggerRequest(identity='fake', params=body)
        self.assertEqual('fake', sot.identity)
        self.assertIsInstance(sot.params, webhooks.WebhookTriggerRequestBody)

        res = sot.obj_to_primitive()

        self.assertIn('identity', res['senlin_object.changes'])
        self.assertIn('WebhookTriggerRequest', res['senlin_object.name'])
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual(u'fake', res['senlin_object.data']['identity'])
