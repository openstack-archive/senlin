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
import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import utils as encrypt_utils
from senlin.db.sqlalchemy import api as db_api
from senlin.drivers.openstack import keystone_v3 as ksdriver
from senlin.engine import webhook as webhook_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestWebhook(base.SenlinTestCase):

    def setUp(self):
        super(TestWebhook, self).setUp()
        self.context = utils.dummy_context()
        cdata = {
            'auth_url': 'TEST_URL',
            'user_id': '123',
            'password': 'abc'
        }
        self.credential = jsonutils.dumps(cdata)
        self.params = {
            'key1': 'value1',
            'key2': 'value2',
        }

    def _create_webhook(self, webhook_name, webhook_id=None):
        values = {
            'id': webhook_id,
            'name': webhook_name,
            'obj_id': 'test-obj-id',
            'obj_type': 'test-obj-type',
            'action': 'test-action',
            'user': self.context.user,
            'project': self.context.project,
            'domain': self.context.domain,
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': self.credential,
            'params': self.params
        }

        return db_api.webhook_create(self.context, values)

    def test_webhook_init(self):
        kwargs = {
            'id': 'WEBHOOK_ID',
            'name': 'test-webhook',
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': self.credential,
            'params': self.params
        }

        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', **kwargs)

        self.assertEqual('test-obj-id', webhook.obj_id)
        self.assertEqual('test-obj-type', webhook.obj_type)
        self.assertEqual('test-action', webhook.action)

        self.assertEqual(kwargs['id'], webhook.id)
        self.assertEqual(kwargs['name'], webhook.name)
        self.assertEqual(kwargs['user'], webhook.user)
        self.assertEqual(kwargs['project'], webhook.project)
        self.assertEqual(kwargs['domain'], webhook.domain)
        self.assertEqual(kwargs['created_time'], webhook.created_time)
        self.assertEqual(kwargs['deleted_time'], webhook.deleted_time)
        self.assertEqual(kwargs['credential'], webhook.credential)
        self.assertEqual(kwargs['params'], webhook.params)

    def test_webhook_init_default_value(self):
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action')

        self.assertEqual('test-obj-id', webhook.obj_id)
        self.assertEqual('test-obj-type', webhook.obj_type)
        self.assertEqual('test-action', webhook.action)

        self.assertIsNotNone(webhook.id)
        self.assertEqual(None, webhook.name)
        self.assertEqual('', webhook.user)
        self.assertEqual('', webhook.project)
        self.assertEqual('', webhook.domain)
        self.assertEqual(None, webhook.created_time)
        self.assertEqual(None, webhook.deleted_time)
        self.assertEqual(None, webhook.credential)
        self.assertEqual({}, webhook.params)

    def test_webhook_init_with_context(self):
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', context=self.context)

        self.assertEqual(self.context.user, webhook.user)
        self.assertEqual(self.context.project, webhook.project)
        self.assertEqual(self.context.domain, webhook.domain)

    def test_webhook_store(self):
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action')

        self.assertIsNotNone(webhook.id)
        webhook_id = webhook.store(self.context)
        self.assertIsNotNone(webhook_id)
        self.assertEqual(webhook_id, webhook.id)

        result = db_api.webhook_get(self.context, webhook_id)

        self.assertIsNotNone(result)
        self.assertEqual(webhook_id, result.id)
        self.assertEqual(webhook.name, result.name)
        self.assertEqual(webhook.user, result.user)
        self.assertEqual(webhook.project, result.project)
        self.assertEqual(webhook.domain, result.domain)
        self.assertEqual(webhook.created_time, result.created_time)
        self.assertEqual(webhook.deleted_time, result.deleted_time)
        self.assertEqual(webhook.credential, result.credential)
        self.assertEqual(webhook.params, result.params)

        self.assertEqual('test-obj-id', result.obj_id)
        self.assertEqual('test-obj-type', result.obj_type)
        self.assertEqual('test-action', result.action)

        self.assertIsNotNone(result.created_time)
        self.assertIsNone(result.deleted_time)

    def test_webhook_store_already_created(self):
        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action')
        webhook.id = 'FAKE_ID'
        webhook_id = webhook.store(self.context)
        self.assertEqual('FAKE_ID', webhook_id)

    def test_webhook_load(self):
        ex = self.assertRaises(exception.WebhookNotFound,
                               webhook_mod.Webhook.load,
                               self.context, 'fake-webhook', None)
        self.assertEqual('The webhook (fake-webhook) could not be found.',
                         six.text_type(ex))

        webhook = self._create_webhook('webhook-1', 'WEBHOOK_ID')
        result = webhook_mod.Webhook.load(self.context, webhook.id)

        self.assertEqual(webhook.id, result.id)
        self.assertEqual(webhook.name, result.name)
        self.assertEqual(webhook.obj_id, result.obj_id)
        self.assertEqual(webhook.obj_type, result.obj_type)
        self.assertEqual(webhook.action, result.action)
        self.assertEqual(webhook.user, result.user)
        self.assertEqual(webhook.project, result.project)
        self.assertEqual(webhook.domain, result.domain)
        self.assertEqual(webhook.credential, result.credential)
        self.assertEqual(webhook.params, result.params)

        self.assertEqual(webhook.created_time, result.created_time)
        self.assertEqual(webhook.deleted_time, result.deleted_time)

    def test_webhook_load_all(self):
        result = webhook_mod.Webhook.load_all(self.context)
        self.assertEqual([], [w for w in result])

        webhook1 = self._create_webhook('webhook-1', 'ID1')
        webhook2 = self._create_webhook('webhook-2', 'ID2')

        result = webhook_mod.Webhook.load_all(self.context)
        webhooks = [w for w in result]
        self.assertEqual(2, len(webhooks))
        self.assertEqual(webhook1.id, webhooks[0].id)
        self.assertEqual(webhook2.id, webhooks[1].id)

    def test_webhook_to_dict(self):
        webhook = self._create_webhook('test-webhook', 'WEBHOOK_ID')
        self.assertIsNotNone(webhook.id)
        expected = {
            'id': webhook.id,
            'name': webhook.name,
            'user': webhook.user,
            'project': webhook.project,
            'domain': webhook.domain,
            'obj_id': webhook.obj_id,
            'obj_type': webhook.obj_type,
            'action': webhook.action,
            'credential': webhook.credential,
            'params': webhook.params,
            'created_time': webhook.created_time.isoformat(),
            'deleted_time': webhook.deleted_time,
        }

        result = webhook_mod.Webhook.load(self.context, webhook_id=webhook.id)
        self.assertEqual(expected, result.to_dict())

    def test_webhook_from_dict(self):
        params = {
            'id': 'WEBHOOK_ID',
            'name': 'test-webhook',
            'obj_id': 'test-obj-id',
            'obj_type': 'test-obj-type',
            'action': 'test-action',
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'credential': self.credential,
            'params': self.params,
            'created_time': timeutils.utcnow(),
            'deleted_time': timeutils.utcnow(),
        }

        webhook = webhook_mod.Webhook.from_dict(**params)
        self.assertEqual(params['id'], webhook.id)
        self.assertEqual(params['name'], webhook.name)
        self.assertEqual(params['user'], webhook.user)
        self.assertEqual(params['project'], webhook.project)
        self.assertEqual(params['domain'], webhook.domain)
        self.assertEqual(params['obj_id'], webhook.obj_id)
        self.assertEqual(params['obj_type'], webhook.obj_type)
        self.assertEqual(params['action'], webhook.action)
        self.assertEqual(params['credential'], webhook.credential)
        self.assertEqual(params['params'], webhook.params)
        self.assertEqual(params['created_time'], webhook.created_time)
        self.assertEqual(params['deleted_time'], webhook.deleted_time)

    def test_webhook_from_dict_with_context(self):
        params = {
            'id': 'WEBHOOK_ID',
            'obj_id': 'test-obj-id',
            'obj_type': 'test-obj-type',
            'action': 'test-action',
        }

        webhook = webhook_mod.Webhook.from_dict(context=self.context,
                                                **params)
        self.assertEqual(params['id'], webhook.id)
        self.assertEqual(self.context.user, webhook.user)
        self.assertEqual(self.context.project, webhook.project)
        self.assertEqual(self.context.domain, webhook.domain)
        self.assertEqual(params['obj_id'], webhook.obj_id)
        self.assertEqual(params['obj_type'], webhook.obj_type)
        self.assertEqual(params['action'], webhook.action)

    def test_webhook_delete(self):
        webhook = self._create_webhook('test-webhook')
        webhook_id = webhook.id
        result = webhook_mod.Webhook.load(self.context, webhook_id)
        self.assertIsNotNone(result)
        self.assertEqual(webhook_id, result.id)

        webhook_mod.Webhook.delete(self.context, webhook_id)
        self.assertRaises(exception.WebhookNotFound, webhook_mod.Webhook.load,
                          self.context, webhook_id, None)

    def test_webhook_delete_not_found(self):
        result = webhook_mod.Webhook.delete(self.context, 'fake-webhook-id')
        self.assertEqual(None, result)

    def test_encrypt_credential(self):
        kwargs = {
            'id': 'WEBHOOK_ID',
            'name': 'test-webhook',
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': self.credential,
            'params': self.params
        }

        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', **kwargs)

        key = webhook.encrypt_credential()
        cdata = encrypt_utils.decrypt(webhook.credential, key)
        credential = jsonutils.loads(cdata)
        self.assertEqual('abc', credential['password'])

    @mock.patch.object(ksdriver.KeystoneClient, '__init__')
    @mock.patch.object(ksdriver.KeystoneClient, 'endpoint_get')
    @mock.patch.object(ksdriver.KeystoneClient, 'service_get')
    def test_generate_url(self, mock_service_get, mock_endpoint_get,
                          mock_init):
        mock_init.return_value = None
        mock_service_get.return_value = {
            'id': 'SENLIN_SERVICE_ID'
        }
        mock_endpoint_get.return_value = {
            'url': 'HTTP://HOST_IP:PORT/V1/$(tenant_id)s'
        }

        kwargs = {
            'id': 'WEBHOOK_ID',
            'name': 'test-webhook',
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'created_time': timeutils.utcnow(),
            'deleted_time': None,
            'credential': self.credential,
            'params': self.params
        }

        webhook = webhook_mod.Webhook('test-obj-id', 'test-obj-type',
                                      'test-action', **kwargs)
        key = 'test-key'
        res1, res2 = webhook.generate_url(key)

        expected_url = _('HTTP://HOST_IP:PORT/V1/%(tenant_id)s/webhooks/'
                         '%(webhook_id)s/trigger?key=%(key)s'
                         ) % {'tenant_id': 'test-project',
                              'webhook_id': webhook.id,
                              'key': six.text_type(key)}
        self.assertEqual(expected_url, res1)
        self.assertEqual(key, res2)

        # Senlin service not found
        mock_service_get.return_value = None
        ex = self.assertRaises(exception.ResourceNotFound,
                               webhook.generate_url, key)
        resource = _('service:type=clustering,name=senlin')
        msg = _('The resource (%(resource)s) could not be found.'
                ) % {'resource': resource}
        self.assertEqual(msg, six.text_type(ex))

        # Senlin endpoint not found
        mock_service_get.return_value = {
            'id': 'SENLIN_SERVICE_ID'
        }
        service_id = mock_service_get.return_value['id']
        mock_endpoint_get.return_value = None
        ex = self.assertRaises(exception.ResourceNotFound,
                               webhook.generate_url, key)
        resource = _('endpoint: service=%(service)s,region='
                     '%(region)s,visibility=%(interface)s'
                     ) % {'service': service_id,
                          'region': None,
                          'interface': 'public'}
        msg = _('The resource (%(resource)s) could not be found.'
                ) % {'resource': resource}
        self.assertEqual(msg, six.text_type(ex))
