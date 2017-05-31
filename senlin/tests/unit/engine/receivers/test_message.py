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

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_utils import uuidutils

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.drivers import base as driver_base
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine.receivers import message as mmod
from senlin.objects import cluster as co
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

UUID = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'


class TestMessage(base.SenlinTestCase):
    def setUp(self):
        super(TestMessage, self).setUp()
        self.context = utils.dummy_context()

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_keystone_client(self, mock_senlindriver):
        sd = mock.Mock()
        kc = mock.Mock()
        sd.identity.return_value = kc
        mock_senlindriver.return_value = sd

        message = mmod.Message('message', None, None, user='user1',
                               project='project1')

        # cached will be returned
        message._keystoneclient = kc
        self.assertEqual(kc, message.keystone())

        # new keystone client created if no cache found
        message._keystoneclient = None
        params = mock.Mock()
        mock_param = self.patchobject(mmod.Message, '_build_conn_params',
                                      return_value=params)
        res = message.keystone()
        self.assertEqual(kc, res)
        self.assertEqual(kc, message._keystoneclient)
        mock_param.assert_called_once_with('user1', 'project1')
        sd.identity.assert_called_once_with(params)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_zaqar_client(self, mock_senlindriver):
        sd = mock.Mock()
        zc = mock.Mock()
        sd.message.return_value = zc
        mock_senlindriver.return_value = sd

        message = mmod.Message('message', None, None, user='user1',
                               project='project1')

        # cached will be returned
        message._zaqarclient = zc
        self.assertEqual(zc, message.zaqar())

        # new zaqar client created if no cache found
        message._zaqarclient = None
        params = mock.Mock()
        mock_param = self.patchobject(mmod.Message, '_build_conn_params',
                                      return_value=params)
        res = message.zaqar()
        self.assertEqual(zc, res)
        self.assertEqual(zc, message._zaqarclient)
        mock_param.assert_called_once_with('user1', 'project1')
        sd.message.assert_called_once_with(params)

    def test__generate_subscriber_url_host_provided(self):
        cfg.CONF.set_override('host', 'web.com', 'receiver')
        cfg.CONF.set_override('port', '1234', 'receiver')
        message = mmod.Message('message', None, None, id=UUID)
        res = message._generate_subscriber_url()

        expected = 'trust+http://web.com:1234/v1/receivers/%s/notify' % UUID
        self.assertEqual(expected, res)

    @mock.patch.object(mmod.Message, '_get_base_url')
    def test__generate_subscriber_url_host_not_provided(
            self, mock_get_base_url):
        mock_get_base_url.return_value = 'http://web.com:1234/v1'
        message = mmod.Message('message', None, None, id=UUID)
        res = message._generate_subscriber_url()

        expected = 'trust+http://web.com:1234/v1/receivers/%s/notify' % UUID
        self.assertEqual(expected, res)

    @mock.patch.object(socket, 'gethostname')
    @mock.patch.object(mmod.Message, '_get_base_url')
    def test__generate_subscriber_url_no_host_no_base(
            self, mock_get_base_url, mock_gethostname):
        mock_get_base_url.return_value = None
        mock_gethostname.return_value = 'test-host'
        message = mmod.Message('message', None, None, id=UUID)
        res = message._generate_subscriber_url()

        expected = 'trust+http://test-host:8778/v1/receivers/%s/notify' % UUID
        self.assertEqual(expected, res)

    def test_to_dict(self):
        message = mmod.Message('message', None, None, user='user1',
                               project='project1', id=UUID)
        message.channel = {'queue_name': 'test-queue',
                           'subscription': 'subscription-id'}
        res = message.to_dict()
        expected_res = {
            'name': None,
            'id': UUID,
            'user': 'user1',
            'project': 'project1',
            'domain': '',
            'type': 'message',
            'channel': {'queue_name': 'test-queue'},
            'action': None,
            'cluster_id': None,
            'actor': {},
            'params': {},
            'created_at': None,
            'updated_at': None,
        }
        self.assertEqual(expected_res, res)

    @mock.patch.object(mmod.Message, '_create_queue')
    @mock.patch.object(mmod.Message, '_create_subscription')
    def test_initialize_channel(self, mock_create_subscription,
                                mock_create_queue):
        mock_sub = mock.Mock()
        mock_sub.subscription_id = 'test-subscription-id'
        mock_create_subscription.return_value = mock_sub
        mock_create_queue.return_value = 'test-queue'

        message = mmod.Message('message', None, None)
        res = message.initialize_channel(self.context)

        expected_channel = {'queue_name': 'test-queue',
                            'subscription': 'test-subscription-id'}
        self.assertEqual(expected_channel, res)
        mock_create_queue.assert_called_once_with()
        mock_create_subscription.assert_called_once_with('test-queue')

    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_queue(self, mock_zaqar):
        cfg.CONF.set_override('max_message_size', 8192, 'receiver')
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'senlin-receiver-%s' % message.id
        kwargs = {
            '_max_messages_post_size': 8192,
            'description': 'Senlin receiver %s.' % message.id,
            'name': queue_name
        }
        mock_zc.queue_create.return_value = queue_name
        res = message._create_queue()

        self.assertEqual(queue_name, res)
        mock_zc.queue_create.assert_called_once_with(**kwargs)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_queue_fail(self, mock_zaqar):
        cfg.CONF.set_override('max_message_size', 8192, 'receiver')
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'senlin-receiver-%s' % message.id
        kwargs = {
            '_max_messages_post_size': 8192,
            'description': 'Senlin receiver %s.' % message.id,
            'name': queue_name
        }
        mock_zc.queue_create.side_effect = exception.InternalError()
        self.assertRaises(exception.EResourceCreation, message._create_queue)
        mock_zc.queue_create.assert_called_once_with(**kwargs)

    @mock.patch.object(mmod.Message, '_generate_subscriber_url')
    @mock.patch.object(mmod.Message, '_build_trust')
    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_subscription(self, mock_zaqar, mock_build_trust,
                                  mock_generate_subscriber_url):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        mock_build_trust.return_value = '123abc'
        subscriber = 'subscriber_url'
        mock_generate_subscriber_url.return_value = subscriber
        message = mmod.Message('message', None, None, id=UUID)
        queue_name = 'test-queue'
        kwargs = {
            "ttl": 2 ** 36,
            "subscriber": subscriber,
            "options": {
                "trust_id": "123abc"
            }
        }
        mock_zc.subscription_create.return_value = 'subscription'
        res = message._create_subscription(queue_name)

        self.assertEqual('subscription', res)
        mock_generate_subscriber_url.assert_called_once_with()
        mock_zc.subscription_create.assert_called_once_with(queue_name,
                                                            **kwargs)

    @mock.patch.object(mmod.Message, '_generate_subscriber_url')
    @mock.patch.object(mmod.Message, '_build_trust')
    @mock.patch.object(mmod.Message, 'zaqar')
    def test__create_subscription_fail(self, mock_zaqar, mock_build_trust,
                                       mock_generate_subscriber_url):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        mock_build_trust.return_value = '123abc'
        subscriber = 'subscriber_url'
        mock_generate_subscriber_url.return_value = subscriber
        message = mmod.Message('message', None, None, id=UUID)
        message.id = UUID
        queue_name = 'test-queue'
        kwargs = {
            "ttl": 2 ** 36,
            "subscriber": subscriber,
            "options": {
                "trust_id": "123abc"
            }
        }

        mock_zc.subscription_create.side_effect = exception.InternalError()
        self.assertRaises(exception.EResourceCreation,
                          message._create_subscription, queue_name)
        mock_generate_subscriber_url.assert_called_once_with()
        mock_zc.subscription_create.assert_called_once_with(queue_name,
                                                            **kwargs)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_release_channel(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        channel = {'queue_name': 'test-queue',
                   'subscription': 'test-subscription-id'}
        message = mmod.Message('message', None, None, id=UUID,
                               channel=channel)

        message.release_channel(self.context)
        mock_zc.subscription_delete.assert_called_once_with(
            'test-queue', 'test-subscription-id')
        mock_zc.queue_delete.assert_called_once_with('test-queue')

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_release_channel_subscription_delete_fail(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        channel = {'queue_name': 'test-queue',
                   'subscription': 'test-subscription-id'}
        message = mmod.Message('message', None, None, id=UUID,
                               channel=channel)
        mock_zc.subscription_delete.side_effect = exception.InternalError()

        self.assertRaises(exception.EResourceDeletion,
                          message.release_channel, self.context)
        mock_zc.subscription_delete.assert_called_once_with(
            'test-queue', 'test-subscription-id')

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_release_channel_queue_delete_fail(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        channel = {'queue_name': 'test-queue',
                   'subscription': 'test-subscription-id'}
        message = mmod.Message('message', None, None, id=UUID,
                               channel=channel)
        mock_zc.queue_delete.side_effect = exception.InternalError()

        self.assertRaises(exception.EResourceDeletion,
                          message.release_channel, self.context)
        mock_zc.subscription_delete.assert_called_once_with(
            'test-queue', 'test-subscription-id')
        mock_zc.queue_delete.assert_called_once_with('test-queue')

    @mock.patch.object(ks_loading, 'load_auth_from_conf_options')
    @mock.patch.object(ks_loading, 'load_session_from_conf_options')
    @mock.patch.object(mmod.Message, 'keystone')
    def test__build_trust_exists(self, mock_keystone, mock_load_session,
                                 mock_load_auth):
        mock_auth = mock.Mock()
        mock_session = mock.Mock()
        mock_session.get_user_id.return_value = 'zaqar-trustee-user-id'
        mock_load_session.return_value = mock_session
        mock_load_auth.return_value = mock_auth
        mock_kc = mock.Mock()
        mock_keystone.return_value = mock_kc
        mock_trust = mock.Mock()
        mock_trust.id = 'mock-trust-id'
        message = mmod.Message('message', None, None, id=UUID,
                               user='user1', project='project1',
                               params={'notifier_roles': ['test-role']})
        mock_kc.trust_get_by_trustor.return_value = mock_trust

        res = message._build_trust()

        self.assertEqual('mock-trust-id', res)
        mock_kc.trust_get_by_trustor.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1')
        mock_load_auth.assert_called_once_with(cfg.CONF, 'zaqar')
        mock_load_session.assert_called_once_with(cfg.CONF, 'zaqar')
        mock_session.get_user_id.assert_called_once_with(auth=mock_auth)

    @mock.patch.object(ks_loading, 'load_auth_from_conf_options')
    @mock.patch.object(ks_loading, 'load_session_from_conf_options')
    @mock.patch.object(mmod.Message, 'keystone')
    def test__build_trust_create_new_multiroles(
            self, mock_keystone, mock_load_session, mock_load_auth):
        mock_auth = mock.Mock()
        mock_session = mock.Mock()
        mock_session.get_user_id.return_value = 'zaqar-trustee-user-id'
        mock_load_session.return_value = mock_session
        mock_load_auth.return_value = mock_auth
        mock_kc = mock.Mock()
        mock_keystone.return_value = mock_kc
        mock_trust = mock.Mock()
        mock_trust.id = 'mock-trust-id'
        message = mmod.Message('message', None, None, id=UUID,
                               user='user1', project='project1')
        message.notifier_roles = ['test_role']
        mock_kc.trust_get_by_trustor.return_value = None
        mock_kc.trust_create.return_value = mock_trust

        res = message._build_trust()

        self.assertEqual('mock-trust-id', res)
        mock_kc.trust_get_by_trustor.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1')
        mock_kc.trust_create.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1', ['test_role'])

    @mock.patch.object(ks_loading, 'load_auth_from_conf_options')
    @mock.patch.object(ks_loading, 'load_session_from_conf_options')
    @mock.patch.object(mmod.Message, 'keystone')
    def test__build_trust_create_new_single_admin_role(
            self, mock_keystone, mock_load_session, mock_load_auth):
        mock_auth = mock.Mock()
        mock_session = mock.Mock()
        mock_session.get_user_id.return_value = 'zaqar-trustee-user-id'
        mock_load_session.return_value = mock_session
        mock_load_auth.return_value = mock_auth
        mock_kc = mock.Mock()
        mock_keystone.return_value = mock_kc
        mock_trust = mock.Mock()
        mock_trust.id = 'mock-trust-id'
        message = mmod.Message('message', None, None, id=UUID,
                               user='user1', project='project1')
        message.notifier_roles = ['admin']
        mock_kc.trust_get_by_trustor.return_value = None
        mock_kc.trust_create.return_value = mock_trust

        res = message._build_trust()

        self.assertEqual('mock-trust-id', res)
        mock_kc.trust_get_by_trustor.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1')
        mock_kc.trust_create.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1', ['admin'])

    @mock.patch.object(ks_loading, 'load_auth_from_conf_options')
    @mock.patch.object(ks_loading, 'load_session_from_conf_options')
    @mock.patch.object(mmod.Message, 'keystone')
    def test__build_trust_create_new_trust_failed(self, mock_keystone,
                                                  mock_load_session,
                                                  mock_load_auth):
        mock_auth = mock.Mock()
        mock_session = mock.Mock()
        mock_session.get_user_id.return_value = 'zaqar-trustee-user-id'
        mock_load_session.return_value = mock_session
        mock_load_auth.return_value = mock_auth
        mock_kc = mock.Mock()
        mock_keystone.return_value = mock_kc
        mock_trust = mock.Mock()
        mock_trust.id = 'mock-trust-id'
        message = mmod.Message('message', None, None, id=UUID,
                               user='user1', project='project1')
        message.notifier_roles = ['test_role']
        mock_kc.trust_get_by_trustor.return_value = None
        mock_kc.trust_create.side_effect = exception.InternalError()

        self.assertRaises(exception.EResourceCreation,
                          message._build_trust)

        mock_kc.trust_get_by_trustor.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1')
        mock_kc.trust_create.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1', ['test_role'])

    @mock.patch.object(ks_loading, 'load_auth_from_conf_options')
    @mock.patch.object(ks_loading, 'load_session_from_conf_options')
    @mock.patch.object(mmod.Message, 'keystone')
    def test__build_trust_get_trust_exception(self, mock_keystone,
                                              mock_load_session,
                                              mock_load_auth):
        mock_auth = mock.Mock()
        mock_session = mock.Mock()
        mock_session.get_user_id.return_value = 'zaqar-trustee-user-id'
        mock_load_session.return_value = mock_session
        mock_load_auth.return_value = mock_auth
        mock_kc = mock.Mock()
        mock_keystone.return_value = mock_kc
        mock_trust = mock.Mock()
        mock_trust.id = 'mock-trust-id'
        message = mmod.Message('message', None, None, id=UUID,
                               user='user1', project='project1')
        mock_kc.trust_get_by_trustor.side_effect = exception.InternalError()

        self.assertRaises(exception.EResourceCreation,
                          message._build_trust)

        mock_kc.trust_get_by_trustor.assert_called_once_with(
            'user1', 'zaqar-trustee-user-id', 'project1')

    @mock.patch.object(co.Cluster, 'get')
    def test_find_cluster_by_uuid(self, mock_get):
        x_cluster = mock.Mock()
        mock_get.return_value = x_cluster

        aid = uuidutils.generate_uuid()
        message = mmod.Message('message', None, None, id=UUID)
        result = message._find_cluster(self.context, aid)

        self.assertEqual(x_cluster, result)
        mock_get.assert_called_once_with(self.context, aid)

    @mock.patch.object(co.Cluster, 'get_by_name')
    @mock.patch.object(co.Cluster, 'get')
    def test_find_cluster_by_uuid_as_name(self, mock_get, mock_get_name):
        x_cluster = mock.Mock()
        mock_get_name.return_value = x_cluster
        mock_get.return_value = None

        aid = uuidutils.generate_uuid()
        message = mmod.Message('message', None, None, id=UUID)
        result = message._find_cluster(self.context, aid)

        self.assertEqual(x_cluster, result)
        mock_get.assert_called_once_with(self.context, aid)
        mock_get_name.assert_called_once_with(self.context, aid)

    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_find_cluster_by_name(self, mock_get_name):
        x_cluster = mock.Mock()
        mock_get_name.return_value = x_cluster

        aid = 'this-is-not-uuid'
        message = mmod.Message('message', None, None, id=UUID)
        result = message._find_cluster(self.context, aid)

        self.assertEqual(x_cluster, result)
        mock_get_name.assert_called_once_with(self.context, aid)

    @mock.patch.object(co.Cluster, 'get_by_short_id')
    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_find_cluster_by_shortid(self, mock_get_name, mock_get_shortid):
        x_cluster = mock.Mock()
        mock_get_shortid.return_value = x_cluster
        mock_get_name.return_value = None

        aid = 'abcd-1234-abcd'
        message = mmod.Message('message', None, None, id=UUID)
        result = message._find_cluster(self.context, aid)

        self.assertEqual(x_cluster, result)
        mock_get_name.assert_called_once_with(self.context, aid)
        mock_get_shortid.assert_called_once_with(self.context, aid)

    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_find_cluster_not_found(self, mock_get_name):
        mock_get_name.return_value = None

        message = mmod.Message('message', None, None, id=UUID)
        self.assertRaises(exception.ResourceNotFound, message._find_cluster,
                          self.context, 'bogus')

        mock_get_name.assert_called_once_with(self.context, 'bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(mmod.Message, '_build_action')
    @mock.patch.object(mmod.Message, 'zaqar')
    def test_notify(self, mock_zaqar, mock_build_action, mock_start_action):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        mock_claim = mock.Mock()
        mock_claim.id = 'claim_id'
        message1 = {
            'body': {'cluster': 'c1', 'action': 'CLUSTER_SCALE_IN'},
            'id': 'ID1'
        }
        message2 = {
            'body': {'cluster': 'c2', 'action': 'CLUSTER_SCALE_OUT'},
            'id': 'ID2'
        }
        mock_claim.messages = [message1, message2]
        mock_zc.claim_create.return_value = mock_claim
        mock_build_action.side_effect = ['action_id1', 'action_id2']

        message = mmod.Message('message', None, None, id=UUID)
        message.channel = {'queue_name': 'queue1'}
        res = message.notify(self.context)
        self.assertEqual(['action_id1', 'action_id2'], res)
        mock_zc.claim_create.assert_called_once_with('queue1')
        mock_zc.claim_delete.assert_called_once_with('queue1', 'claim_id')
        mock_calls = [
            mock.call(self.context, message1),
            mock.call(self.context, message2)
        ]
        mock_build_action.assert_has_calls(mock_calls)
        mock_start_action.assert_called_once_with()
        mock_calls2 = [
            mock.call('queue1', 'ID1', 'claim_id'),
            mock.call('queue1', 'ID2', 'claim_id')
        ]
        mock_zc.message_delete.assert_has_calls(mock_calls2)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_notify_no_message(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        mock_claim = mock.Mock()
        mock_claim.messages = None
        mock_zc.claim_create.return_value = mock_claim

        message = mmod.Message('message', None, None, id=UUID)
        message.channel = {'queue_name': 'queue1'}
        res = message.notify(self.context)
        self.assertEqual([], res)
        mock_zc.claim_create.assert_called_once_with('queue1')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(mmod.Message, '_build_action')
    @mock.patch.object(mmod.Message, 'zaqar')
    def test_notify_some_actions_building_failed(self, mock_zaqar,
                                                 mock_build_action,
                                                 mock_start_action):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        mock_claim = mock.Mock()
        mock_claim.id = 'claim_id'
        message1 = {
            'body': {'cluster': 'c1', 'action': 'CLUSTER_SCALE_IN'},
            'id': 'ID1'
        }
        message2 = {
            'body': {'cluster': 'foo', 'action': 'CLUSTER_SCALE_OUT'},
            'id': 'ID2'
        }
        mock_claim.messages = [message1, message2]
        mock_zc.claim_create.return_value = mock_claim
        mock_build_action.side_effect = [exception.InternalError(),
                                         'action_id1']

        message = mmod.Message('message', None, None, id=UUID)
        message.channel = {'queue_name': 'queue1'}
        res = message.notify(self.context)
        self.assertEqual(['action_id1'], res)
        mock_zc.claim_create.assert_called_once_with('queue1')
        mock_calls = [
            mock.call(self.context, message1),
            mock.call(self.context, message2)
        ]
        mock_build_action.assert_has_calls(mock_calls)
        mock_start_action.assert_called_once_with()
        mock_calls2 = [
            mock.call('queue1', 'ID1', 'claim_id'),
            mock.call('queue1', 'ID2', 'claim_id')
        ]
        mock_zc.message_delete.assert_has_calls(mock_calls2)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_notify_claiming_message_failed(self, mock_zaqar):
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        mock_zc.claim_create.side_effect = exception.InternalError()

        message = mmod.Message('message', None, None, id=UUID)
        message.channel = {'queue_name': 'queue1'}
        res = message.notify(self.context)
        self.assertIsNone(res)
        mock_zc.claim_create.assert_called_once_with('queue1')

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(mmod.Message, '_find_cluster')
    def test_build_action(self, mock_find_cluster, mock_action_create):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'user1'
        fake_cluster.id = 'cid1'
        mock_find_cluster.return_value = fake_cluster
        mock_action_create.return_value = 'action_id1'
        msg = {
            'body': {'cluster': 'c1', 'action': 'CLUSTER_SCALE_IN'},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        message.id = 'ID654321'
        message.user = 'user1'
        expected_kwargs = {
            'name': 'receiver_ID654321_ID123456',
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': {}
        }

        res = message._build_action(self.context, msg)
        self.assertEqual('action_id1', res)
        mock_find_cluster.assert_called_once_with(self.context, 'c1')
        mock_action_create.assert_called_once_with(self.context, 'cid1',
                                                   'CLUSTER_SCALE_IN',
                                                   **expected_kwargs)

    def test_build_action_message_body_empty(self):
        msg = {
            'body': {},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        ex = self.assertRaises(exception.InternalError, message._build_action,
                               self.context, msg)
        ex_msg = _('Message body is empty.')
        self.assertEqual(ex_msg, ex.message)

    def test_build_action_no_cluster_in_message_body(self):
        msg = {
            'body': {'action': 'CLUSTER_SCALE_IN'},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        ex = self.assertRaises(exception.InternalError, message._build_action,
                               self.context, msg)
        ex_msg = _('Both cluster identity and action must be specified.')
        self.assertEqual(ex_msg, ex.message)

    def test_build_action_no_action_in_message_body(self):
        msg = {
            'body': {'cluster': 'c1'},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        ex = self.assertRaises(exception.InternalError, message._build_action,
                               self.context, msg)
        ex_msg = _('Both cluster identity and action must be specified.')
        self.assertEqual(ex_msg, ex.message)

    @mock.patch.object(mmod.Message, '_find_cluster')
    def test_build_action_cluster_notfound(self, mock_find_cluster):
        mock_find_cluster.side_effect = exception.ResourceNotFound(
            type='cluster', id='c1')
        msg = {
            'body': {'cluster': 'c1', 'action': 'CLUSTER_SCALE_IN'},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        ex = self.assertRaises(exception.InternalError, message._build_action,
                               self.context, msg)
        ex_msg = _('Cluster (c1) cannot be found.')
        self.assertEqual(ex_msg, ex.message)

    @mock.patch.object(mmod.Message, '_find_cluster')
    def test_build_action_permission_denied(self, mock_find_cluster):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'user1'
        mock_find_cluster.return_value = fake_cluster
        msg = {
            'body': {'cluster': 'c1', 'action': 'CLUSTER_SCALE_IN'},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        message.user = 'user2'
        ex = self.assertRaises(exception.InternalError, message._build_action,
                               self.context, msg)
        ex_msg = _('%(user)s is not allowed to trigger actions on '
                   'cluster %(cid)s.') % {'user': message.user,
                                          'cid': 'c1'}
        self.assertEqual(ex_msg, ex.message)

    @mock.patch.object(mmod.Message, '_find_cluster')
    def test_build_action_invalid_action_name(self, mock_find_cluster):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'user1'
        mock_find_cluster.return_value = fake_cluster
        msg = {
            'body': {'cluster': 'c1', 'action': 'foo'},
            'id': 'ID123456'
        }
        message = mmod.Message('message', None, None, id=UUID)
        message.user = 'user1'
        ex = self.assertRaises(exception.InternalError, message._build_action,
                               self.context, msg)
        ex_msg = _("Illegal cluster action 'foo' specified.")
        self.assertEqual(ex_msg, ex.message)
