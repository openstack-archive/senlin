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
from oslo_context import context as oslo_ctx
from oslo_utils import timeutils
import six

from senlin.common import context
from senlin.common import exception
from senlin.common import utils as common_utils
from senlin.drivers import base as driver_base
from senlin.engine.receivers import base as rb
from senlin.engine.receivers import message as rm
from senlin.engine.receivers import webhook as rw
from senlin.objects import credential as co
from senlin.objects import receiver as ro
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'
UUID1 = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'
UUID2 = '60efdaa1-06c2-4fcf-ae44-17a2d85ff3ea'


class TestReceiver(base.SenlinTestCase):

    def setUp(self):
        super(TestReceiver, self).setUp()
        self.context = utils.dummy_context()
        self.actor = {
            'auth_url': 'TEST_URL',
            'user_id': '123',
            'password': 'abc'
        }
        self.params = {
            'key1': 'value1',
            'key2': 'value2',
        }

    def _create_receiver(self, receiver_name, receiver_id=None):
        values = {
            'id': receiver_id,
            'name': receiver_name,
            'type': 'webhook',
            'cluster_id': CLUSTER_ID,
            'action': 'test-action',
            'user': self.context.user_id,
            'project': self.context.project_id,
            'domain': self.context.domain_id,
            'created_at': timeutils.utcnow(True),
            'updated_at': None,
            'actor': self.actor,
            'params': self.params,
            'channel': None,
        }

        return ro.Receiver.create(self.context, values)

    def test_receiver_init(self):
        kwargs = {
            'id': UUID1,
            'name': 'test-receiver',
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'created_at': timeutils.utcnow(True),
            'updated_at': None,
            'actor': self.actor,
            'params': self.params,
            'channel': {'alarm_url': 'http://url1'},
        }

        receiver = rb.Receiver('webhook', CLUSTER_ID, 'test-action', **kwargs)

        self.assertEqual(kwargs['id'], receiver.id)
        self.assertEqual(kwargs['name'], receiver.name)
        self.assertEqual('webhook', receiver.type)
        self.assertEqual('test-action', receiver.action)
        self.assertEqual(kwargs['user'], receiver.user)
        self.assertEqual(kwargs['project'], receiver.project)
        self.assertEqual(kwargs['domain'], receiver.domain)

        self.assertEqual(kwargs['created_at'], receiver.created_at)
        self.assertEqual(kwargs['updated_at'], receiver.updated_at)

        self.assertEqual(CLUSTER_ID, receiver.cluster_id)
        self.assertEqual('test-action', receiver.action)
        self.assertEqual(self.actor, receiver.actor)
        self.assertEqual(self.params, receiver.params)
        self.assertEqual(kwargs['channel'], receiver.channel)

    def test_receiver_init_default_value(self):
        receiver = rb.Receiver('webhook', CLUSTER_ID, 'test-action')
        self.assertIsNone(receiver.id)
        self.assertIsNone(receiver.name)
        self.assertEqual('webhook', receiver.type)
        self.assertEqual('', receiver.user)
        self.assertEqual('', receiver.project)
        self.assertEqual('', receiver.domain)

        self.assertIsNone(receiver.created_at)
        self.assertIsNone(receiver.updated_at)

        self.assertEqual(CLUSTER_ID, receiver.cluster_id)
        self.assertEqual('test-action', receiver.action)
        self.assertEqual({}, receiver.actor)
        self.assertEqual({}, receiver.params)
        self.assertEqual({}, receiver.channel)

    def test_receiver_store(self):
        receiver = rb.Receiver('webhook', CLUSTER_ID, 'test-action',
                               name='test_receiver_123456',
                               project=self.context.project_id)
        self.assertIsNone(receiver.id)

        receiver_id = receiver.store(self.context)

        self.assertIsNotNone(receiver_id)
        self.assertEqual(receiver_id, receiver.id)

        result = ro.Receiver.get(self.context, receiver_id)

        self.assertIsNotNone(result)
        self.assertEqual(receiver_id, result.id)
        self.assertEqual(receiver.type, result.type)
        self.assertEqual(receiver.name, result.name)
        self.assertEqual(receiver.user, result.user)
        self.assertEqual(receiver.project, result.project)
        self.assertEqual(receiver.domain, result.domain)
        self.assertEqual(common_utils.isotime(receiver.created_at),
                         common_utils.isotime(result.created_at)),
        self.assertEqual(receiver.updated_at, result.updated_at)
        self.assertEqual(receiver.action, result.action)
        self.assertEqual(receiver.actor, result.actor)
        self.assertEqual(receiver.params, result.params)
        self.assertEqual(receiver.channel, result.channel)

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(rw.Webhook, 'initialize_channel')
    def test_receiver_create_webhook_admin(self, mock_initialize_channel,
                                           mock_c_get):
        mock_c_get.return_value = {
            'cred': {'openstack': {'trust': '123abc'}}
        }
        ctx = utils.dummy_context(is_admin=True)
        cluster = mock.Mock()
        cluster.id = CLUSTER_ID
        cluster.user = 'user1'
        cluster.project = 'project1'
        receiver = rb.Receiver.create(ctx, 'webhook', cluster,
                                      'FAKE_ACTION',
                                      name='test_receiver_2234')

        self.assertEqual(ctx.user_id, receiver.user)
        self.assertEqual(ctx.project_id, receiver.project)
        self.assertEqual(ctx.domain_id, receiver.domain)
        self.assertEqual('123abc', receiver.actor['trust_id'])
        mock_c_get.assert_called_once_with(ctx, 'user1', 'project1')

    @mock.patch.object(rw.Webhook, 'initialize_channel')
    def test_receiver_create_webhook_non_admin(self, mock_initialize_channel):
        ctx = utils.dummy_context(is_admin=False)
        cluster = mock.Mock()
        cluster.id = CLUSTER_ID
        receiver = rb.Receiver.create(ctx, 'webhook', cluster,
                                      'FAKE_ACTION',
                                      name='test_receiver_2234')

        self.assertEqual(ctx.user_id, receiver.user)
        self.assertEqual(ctx.project_id, receiver.project)
        self.assertEqual(ctx.domain_id, receiver.domain)
        self.assertIsNone(receiver.actor['trust_id'])

    @mock.patch.object(rm.Message, 'initialize_channel')
    def test_receiver_create_message(self, mock_initialize_channel):
        receiver = rb.Receiver.create(self.context, 'message', None,
                                      None, name='test_receiver_2234')

        self.assertEqual(self.context.user_id, receiver.user)
        self.assertEqual(self.context.project_id, receiver.project)
        self.assertEqual(self.context.domain_id, receiver.domain)

    def _verify_receiver(self, receiver, result):
        self.assertEqual(receiver.id, result.id)
        self.assertEqual(receiver.name, result.name)
        self.assertEqual(receiver.type, result.type)
        self.assertEqual(receiver.user, result.user)
        self.assertEqual(receiver.project, result.project)
        self.assertEqual(receiver.domain, result.domain)

        self.assertEqual(receiver.created_at, result.created_at)
        self.assertEqual(receiver.updated_at, result.updated_at)

        self.assertEqual(receiver.cluster_id, result.cluster_id)
        self.assertEqual(receiver.actor, result.actor)
        self.assertEqual(receiver.action, result.action)
        self.assertEqual(receiver.params, result.params)
        self.assertEqual(receiver.channel, result.channel)

    def test_receiver_load_with_id(self):
        receiver = self._create_receiver('receiver-1', UUID1)
        result = rb.Receiver.load(self.context, receiver_id=receiver.id)
        self._verify_receiver(receiver, result)

    def test_receiver_load_with_object(self):
        receiver = self._create_receiver('receiver-1', UUID1)
        result = rb.Receiver.load(self.context, receiver_obj=receiver)
        self._verify_receiver(receiver, result)

    def test_receiver_load_not_found(self):
        ex = self.assertRaises(exception.ResourceNotFound,
                               rb.Receiver.load,
                               self.context, 'fake-receiver', None)
        self.assertEqual("The receiver 'fake-receiver' could not "
                         "be found.", six.text_type(ex))

    def test_receiver_load_diff_project(self):
        receiver = self._create_receiver('receiver-1', UUID1)

        new_context = utils.dummy_context(project='a-different-project')
        ex = self.assertRaises(exception.ResourceNotFound,
                               rb.Receiver.load,
                               new_context, UUID1, None)
        self.assertEqual("The receiver '%s' could not be found." % UUID1,
                         six.text_type(ex))

        res = rb.Receiver.load(new_context, receiver.id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(receiver.id, res.id)

    def test_receiver_to_dict(self):
        receiver = self._create_receiver('test-receiver', UUID1)
        self.assertIsNotNone(receiver.id)
        expected = {
            'id': receiver.id,
            'name': receiver.name,
            'type': receiver.type,
            'user': receiver.user,
            'project': receiver.project,
            'domain': receiver.domain,
            'cluster_id': receiver.cluster_id,
            'action': receiver.action,
            'actor': receiver.actor,
            'params': receiver.params,
            'created_at': common_utils.isotime(receiver.created_at),
            'updated_at': common_utils.isotime(receiver.updated_at),
            'channel': None,
        }

        result = rb.Receiver.load(self.context, receiver_id=receiver.id)
        self.assertEqual(expected, result.to_dict())

    def test_release_channel(self):
        receiver = self._create_receiver('test-receiver', UUID1)
        receiver = rb.Receiver.load(self.context, UUID1)
        res = receiver.release_channel(self.context)
        self.assertIsNone(res)

    def test_notify(self):
        receiver = self._create_receiver('test-receiver', UUID1)
        receiver = rb.Receiver.load(self.context, UUID1)
        res = receiver.notify(self.context)
        self.assertIsNone(res)

    @mock.patch.object(ro.Receiver, 'delete')
    @mock.patch.object(rb.Receiver, 'load')
    def test_receiver_delete(self, mock_load, mock_delete):
        mock_receiver = mock.Mock()
        mock_receiver.id = 'test-receiver-id'
        mock_load.return_value = mock_receiver

        rb.Receiver.delete(self.context, 'test-receiver-id')

        mock_load.assert_called_once_with(self.context,
                                          receiver_id='test-receiver-id')
        mock_receiver.release_channel.assert_called_once_with(self.context)
        mock_delete.assert_called_once_with(self.context, 'test-receiver-id')

    @mock.patch.object(context, "get_service_credentials")
    @mock.patch.object(driver_base, "SenlinDriver")
    def test__get_base_url_succeeded(self, mock_senlin_driver,
                                     mock_get_service_creds):
        cfg.CONF.set_override('default_region_name', 'RegionOne')
        fake_driver = mock.Mock()
        fake_kc = mock.Mock()
        fake_cred = mock.Mock()
        mock_senlin_driver.return_value = fake_driver
        fake_driver.identity.return_value = fake_kc
        mock_get_service_creds.return_value = fake_cred

        fake_kc.get_senlin_endpoint.return_value = "http://web.com:1234/v1"

        receiver = rb.Receiver(
            'webhook', CLUSTER_ID, 'FAKE_ACTION',
            id=UUID1, params={'KEY': 884, 'FOO': 'BAR'})

        res = receiver._get_base_url()
        self.assertEqual("http://web.com:1234/v1", res)
        mock_get_service_creds.assert_called_once_with()
        fake_kc.get_senlin_endpoint.assert_called_once_with()

    @mock.patch.object(context, "get_service_credentials")
    @mock.patch.object(driver_base, "SenlinDriver")
    def test__get_base_url_failed_get_endpoint_exception(
            self, mock_senlin_driver, mock_get_service_creds):
        cfg.CONF.set_override('default_region_name', 'RegionOne')
        fake_driver = mock.Mock()
        fake_kc = mock.Mock()
        fake_cred = mock.Mock()
        mock_senlin_driver.return_value = fake_driver
        fake_driver.identity.return_value = fake_kc
        mock_get_service_creds.return_value = fake_cred

        fake_kc.get_senlin_endpoint.side_effect = exception.InternalError(
            message='Error!')

        receiver = rb.Receiver(
            'webhook', CLUSTER_ID, 'FAKE_ACTION',
            id=UUID1, params={'KEY': 884, 'FOO': 'BAR'})

        res = receiver._get_base_url()
        self.assertIsNone(res)
        mock_get_service_creds.assert_called_once_with()
        fake_kc.get_senlin_endpoint.assert_called_once_with()

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(context, 'get_service_credentials')
    @mock.patch.object(oslo_ctx, 'get_current')
    def test_build_conn_params(self, mock_get_current, mock_get_service_creds,
                               mock_cred_get):
        user = 'user1'
        project = 'project1'
        service_cred = {
            'auth_url': 'AUTH_URL',
            'username': 'senlin',
            'user_domain_name': 'default',
            'password': '123'
        }
        current_ctx = {
            'auth_url': 'auth_url',
            'user_name': user,
            'user_domain_name': 'default',
            'password': '456'
        }
        cred_info = {
            'openstack': {
                'trust': 'TRUST_ID',
            }
        }

        cred = mock.Mock()
        cred.cred = cred_info
        mock_get_service_creds.return_value = service_cred
        mock_get_current.return_value = current_ctx
        mock_cred_get.return_value = cred

        receiver = self._create_receiver('receiver-1', UUID1)
        receiver = rb.Receiver.load(self.context, receiver_obj=receiver)
        expected_result = {
            'auth_url': 'AUTH_URL',
            'username': 'senlin',
            'user_domain_name': 'default',
            'password': '123',
            'trust_id': 'TRUST_ID'
        }
        res = receiver._build_conn_params(user, project)
        self.assertEqual(expected_result, res)
        mock_get_service_creds.assert_called_once_with()
        mock_cred_get.assert_called_once_with(current_ctx, user, project)

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(context, 'get_service_credentials')
    @mock.patch.object(oslo_ctx, 'get_current')
    def test_build_conn_params_trust_not_found(
            self, mock_get_current, mock_get_service_creds, mock_cred_get):

        user = 'user1'
        project = 'project1'
        service_cred = {
            'auth_url': 'AUTH_URL',
            'username': 'senlin',
            'user_domain_name': 'default',
            'password': '123'
        }

        mock_get_service_creds.return_value = service_cred
        mock_cred_get.return_value = None

        receiver = self._create_receiver('receiver-1', UUID1)
        receiver = rb.Receiver.load(self.context, receiver_obj=receiver)
        ex = self.assertRaises(exception.TrustNotFound,
                               receiver._build_conn_params, user, project)
        msg = "The trust for trustor 'user1' could not be found."
        self.assertEqual(msg, six.text_type(ex))
