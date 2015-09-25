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
from oslo_messaging.rpc import dispatcher as rpc
from oslo_serialization import jsonutils
import six

from senlin.common import consts
from senlin.common import exception
from senlin.common import utils as common_utils
from senlin.db.sqlalchemy import api as db_api
from senlin.engine.actions import base as action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import service
from senlin.engine import webhook as webhook_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class WebhookTest(base.SenlinTestCase):

    def setUp(self):
        super(WebhookTest, self).setUp()
        self.ctx = utils.dummy_context(project='webhook_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        self.eng.dispatcher = mock.Mock()

        env = environment.global_env()
        env.register_profile('TestProfile', fakes.TestProfile)

        spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {
                'INT': 10,
                'STR': 'string'
            }
        }
        self.profile = self.eng.profile_create(self.ctx, 'p-test', spec,
                                               permission='1111')

    def _verify_action(self, obj, action, name, target, cause, inputs=None):
        if inputs is None:
            inputs = {}
        self.assertEqual(action, obj['action'])
        self.assertEqual(name, obj['name'])
        self.assertEqual(target, obj['target'])
        self.assertEqual(cause, obj['cause'])
        self.assertEqual(inputs, obj['inputs'])

    @mock.patch.object(dispatcher, 'start_action')
    def _create_cluster(self, name, notify):
        cluster = self.eng.cluster_create(self.ctx, name, 0,
                                          self.profile['id'])

        return cluster

    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_create(self, mock_encrypt, mock_url):
        mock_url.return_value = 'test-url', 'test-key'
        mock_encrypt.return_value = 'secret text', 'test-key'

        cluster = self._create_cluster('c1')
        obj_id = cluster['id']
        obj_type = 'cluster'
        action = consts.CLUSTER_SCALE_OUT

        credential = {'user_id': 'test_user_id', 'password': 'test-pass'}
        cdata = jsonutils.dumps(credential)
        params = {'p1': 'v1', 'p2': 'v2'}
        webhook = self.eng.webhook_create(
            self.ctx, obj_id, obj_type,
            action,
            credential=cdata,
            params=params, name='test-webhook-name')

        self.assertIsNotNone(webhook)
        self.assertEqual('test-webhook-name', webhook['name'])
        self.assertEqual(obj_id, webhook['obj_id'])
        self.assertEqual(obj_type, webhook['obj_type'])
        self.assertEqual(action, webhook['action'])
        self.assertEqual('secret text', webhook['credential'])
        self.assertEqual(params, webhook['params'])
        self.assertIsNone(webhook['deleted_time'])
        self.assertIsNotNone(webhook['id'])
        self.assertIsNotNone(webhook['created_time'])

    def test_webhook_create_obj_type_unsupported(self):
        cluster = self._create_cluster('c1')
        obj_id = cluster['id']
        obj_type = 'fake-type'
        action = consts.CLUSTER_SCALE_OUT

        credential = {'userid': 'test-user-id', 'password': 'test-pass'}
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_create,
                               self.ctx, obj_id, obj_type, action,
                               credential=credential)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: '
                         'Webhook obj type %s is not supported.'
                         '' % obj_type,
                         six.text_type(ex.exc_info[1]))

    def test_webhook_create_obj_id_not_found(self):
        obj_id = 'fake-id'
        obj_type = 'cluster'
        action = consts.CLUSTER_SCALE_OUT

        credential = {'userid': 'test-user-id', 'password': 'test-pass'}
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_create,
                               self.ctx, obj_id, obj_type, action,
                               credential=credential)
        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (%s) could not be found.'
                         '' % obj_id,
                         six.text_type(ex.exc_info[1]))

    def test_webhook_create_action_illegal(self):
        cluster = self._create_cluster('c1')
        obj_id = cluster['id']
        obj_type = 'cluster'
        action = 'fake-action'

        credential = {'user_id': 'test-user-id', 'password': 'test-pass'}
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_create,
                               self.ctx, obj_id, obj_type, action,
                               credential=credential)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: '
                         'Illegal action name (%s) specified.'
                         '' % action,
                         six.text_type(ex.exc_info[1]))

    def test_webhook_create_action_unavailable(self):
        cluster = self._create_cluster('c1')
        obj_id = cluster['id']
        obj_type = 'cluster'
        action = consts.NODE_LEAVE

        credential = {'userid': 'test-user-id', 'password': 'test-pass'}
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_create,
                               self.ctx, obj_id, obj_type, action,
                               credential=credential)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: '
                         'Action %s is not applicable to object of type %s.'
                         '' % (action, obj_type),
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(db_api, 'cred_get')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_create_as_admin(self, mock_encrypt, mock_url,
                                     mock_cred):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        mock_cred.return_value = {'cred': {'openstack': {'trust': '123abc'}}}

        self.ctx.is_admin = True
        cluster = self._create_cluster('c1')
        webhook = self.eng.webhook_create(self.ctx, cluster['id'], 'cluster',
                                          consts.CLUSTER_SCALE_OUT)
        self.assertIsNotNone(webhook)

        # an admin with different user ID is okay
        diff_ctx = utils.dummy_context(project='webhook_test_project',
                                       user_id='I am admin')
        diff_ctx.is_admin = True
        webhook = self.eng.webhook_create(self.ctx, cluster['id'], 'cluster',
                                          consts.CLUSTER_SCALE_OUT)
        self.assertIsNotNone(webhook)

    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_create_default_user(self, mock_encrypt, mock_url):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'

        self.ctx.is_admin = False
        cluster = self._create_cluster('c1')

        webhook = self.eng.webhook_create(self.ctx, cluster['id'], 'cluster',
                                          consts.CLUSTER_SCALE_OUT)
        self.assertIsNotNone(webhook)

        diff_ctx = utils.dummy_context(project='webhook_test_project',
                                       user_id='others')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_create,
                               diff_ctx, cluster['id'], 'cluster',
                               consts.CLUSTER_SCALE_OUT)
        self.assertEqual(exception.Forbidden, ex.exc_info[0])

    @mock.patch.object(db_api, 'cred_get')
    def test_create_credential(self, mock_cred):
        self.ctx.trusts = 'trust1'
        self.ctx.is_admin = False
        obj = mock.Mock()
        credential = self.eng._create_credential(self.ctx, obj)
        self.assertEqual(['trust1'], credential['trust_id'])

        self.ctx.is_admin = True
        mock_cred.return_value = {'cred': {'openstack': {'trust': 'trust2'}}}
        credential = self.eng._create_credential(self.ctx, obj)
        self.assertEqual(['trust2'], credential['trust_id'])

    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_get(self, mock_encrypt, mock_url):
        mock_encrypt.return_value = 'encoded text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'

        cluster = self._create_cluster('c1')
        obj_id = cluster['id']

        w = self.eng.webhook_create(self.ctx, obj_id, 'cluster',
                                    consts.CLUSTER_SCALE_OUT, name='w-1')

        for identity in [w['id'], w['id'][:6], 'w-1']:
            result = self.eng.webhook_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(w['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_get, self.ctx, 'fake-id')
        self.assertEqual(exception.WebhookNotFound, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_list(self, mock_encrypt, mock_url, mock_find):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        w1 = self.eng.webhook_create(self.ctx, 'cid-1', 'cluster',
                                     consts.CLUSTER_SCALE_OUT, name='w1')
        w2 = self.eng.webhook_create(self.ctx, 'cid-2', 'cluster',
                                     consts.CLUSTER_SCALE_IN, name='w2')

        result = self.eng.webhook_list(self.ctx)
        self.assertIsInstance(result, list)
        names = [w['name'] for w in result]
        ids = [w['id'] for w in result]
        self.assertIn(w1['name'], names)
        self.assertIn(w2['name'], names)
        self.assertIn(w1['id'], ids)
        self.assertIn(w2['id'], ids)

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_list_with_filters(self, mock_encrypt, mock_url,
                                       mock_find):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        w1 = self.eng.webhook_create(self.ctx, 'cid-1', 'cluster',
                                     consts.CLUSTER_SCALE_OUT, name='w1')
        w2 = self.eng.webhook_create(self.ctx, 'cid-2', 'cluster',
                                     consts.CLUSTER_SCALE_IN, name='w2')

        result = self.eng.webhook_list(self.ctx,
                                       filters={'obj_type': 'cluster'})
        self.assertEqual(2, len(result))
        result = self.eng.webhook_list(self.ctx,
                                       filters={'obj_type': 'node'})
        self.assertEqual(0, len(result))
        result = self.eng.webhook_list(self.ctx,
                                       filters={'obj_id': 'cid-1'})
        self.assertEqual(1, len(result))
        self.assertEqual(w1['id'], result[0]['id'])
        result = self.eng.webhook_list(self.ctx,
                                       filters={'obj_id': 'fake-id'})
        self.assertEqual(0, len(result))
        result = self.eng.webhook_list(
            self.ctx, filters={'action': consts.CLUSTER_SCALE_IN})
        self.assertEqual(1, len(result))
        self.assertEqual(w2['id'], result[0]['id'])

        result = self.eng.webhook_list(self.ctx,
                                       filters={'action': 'fake-action'})
        self.assertEqual(0, len(result))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_list_with_limit_marker(self, mock_encrypt, mock_url,
                                            mock_find):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        w1 = self.eng.webhook_create(self.ctx, 'cid1', 'cluster',
                                     consts.CLUSTER_SCALE_OUT, name='w1')
        w2 = self.eng.webhook_create(self.ctx, 'cid2', 'cluster',
                                     consts.CLUSTER_SCALE_IN, name='w2')

        result = self.eng.webhook_list(self.ctx, limit=0)
        self.assertEqual(0, len(result))
        result = self.eng.webhook_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.webhook_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))

        result = self.eng.webhook_list(self.ctx, marker=w1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.webhook_list(self.ctx, marker=w2['id'])
        self.assertEqual(0, len(result))

        w3 = self.eng.webhook_create(self.ctx, 'cid3', 'cluster',
                                     consts.CLUSTER_SCALE_IN, name='w3')

        result = self.eng.webhook_list(self.ctx, limit=1, marker=w1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.webhook_list(self.ctx, limit=2, marker=w1['id'])
        self.assertEqual(2, len(result))
        result = self.eng.webhook_list(self.ctx, limit=2, marker=w3['id'])
        self.assertEqual(0, len(result))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_list_with_sort_keys(self, mock_encrypt, mock_url,
                                         mock_find):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        w1 = self.eng.webhook_create(self.ctx, 'obj-id-1', 'cluster',
                                     consts.CLUSTER_SCALE_OUT,
                                     name='w3')
        w2 = self.eng.webhook_create(self.ctx, 'obj-id-2', 'cluster',
                                     consts.CLUSTER_SCALE_IN,
                                     name='w2')
        w3 = self.eng.webhook_create(self.ctx, 'obj-id-1', 'cluster',
                                     consts.CLUSTER_SCALE_IN,
                                     name='w1')

        # default by obj_id
        result = self.eng.webhook_list(self.ctx)
        self.assertEqual(w2['id'], result[2]['id'])

        # use name for sorting
        result = self.eng.webhook_list(self.ctx, sort_keys=['name'])
        self.assertEqual(w1['id'], result[2]['id'])
        self.assertEqual(w2['id'], result[1]['id'])
        self.assertEqual(w3['id'], result[0]['id'])

        # use created_time for sorting
        result = self.eng.webhook_list(self.ctx, sort_keys=['created_time'])
        self.assertEqual(w1['id'], result[0]['id'])
        self.assertEqual(w2['id'], result[1]['id'])
        self.assertEqual(w3['id'], result[2]['id'])

        # use created_time and obj_id for sorting
        result = self.eng.webhook_list(self.ctx,
                                       sort_keys=['obj_id', 'created_time'])
        self.assertEqual(3, len(result))
        self.assertEqual(w1['id'], result[0]['id'])
        self.assertEqual(w2['id'], result[2]['id'])
        self.assertEqual(w3['id'], result[1]['id'])

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_list_with_sort_dir(self, mock_encrypt, mock_url,
                                        mock_find):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        w1 = self.eng.webhook_create(self.ctx, 'cid-1', 'cluster',
                                     consts.CLUSTER_SCALE_OUT, name='w1')
        w2 = self.eng.webhook_create(self.ctx, 'cid-2', 'cluster',
                                     consts.CLUSTER_SCALE_IN, name='w2')

        # use name for sorting, descending
        result = self.eng.webhook_list(self.ctx, sort_keys=['name'],
                                       sort_dir='desc')
        self.assertEqual(w1['id'], result[1]['id'])
        self.assertEqual(w2['id'], result[0]['id'])

        # Unknown sort direction for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.webhook_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_trigger(self, mock_encrypt, mock_url, mock_find, notify,
                             mock_load):
        mock_encrypt.return_value = 'secret text', 'test-key'
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        fake_cluster.project = self.ctx.project
        fake_cluster.domain = self.ctx.domain
        fake_cluster.id = 'CLUSTER_FULL_ID'
        mock_load.return_value = fake_cluster
        mock_find.return_value = fake_cluster

        obj_id = 'cluster-id-1'
        webhook = self.eng.webhook_create(self.ctx, obj_id, 'cluster',
                                          consts.CLUSTER_SCALE_OUT,
                                          name='test-webhook-name')

        self.assertIsNotNone(webhook)

        res = self.eng.webhook_trigger(self.ctx, webhook['id'])

        # verify action is fired
        action_id = res['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, consts.CLUSTER_SCALE_OUT,
                            'webhook_action_%s' % webhook['id'][:8],
                            'CLUSTER_FULL_ID', cause=action_mod.CAUSE_RPC,
                            inputs={})

        notify.assert_called_once_with(action_id=action_id)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_trigger_with_params(self, mock_encrypt, mock_url,
                                         mock_find, notify, mock_load):
        mock_url.return_value = 'test-url', 'test-key'
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        fake_cluster.project = self.ctx.project
        fake_cluster.domain = self.ctx.domain
        fake_cluster.id = 'CLUSTER_FULL_ID'
        mock_load.return_value = fake_cluster
        mock_find.return_value = fake_cluster
        mock_encrypt.return_value = 'secret text', 'test-key'

        obj_id = 'cluster-id-1'
        params = {'p1': 'v1', 'p2': 'v2'}
        webhook = self.eng.webhook_create(self.ctx, obj_id, 'cluster',
                                          consts.CLUSTER_SCALE_OUT,
                                          params=params)
        self.assertIsNotNone(webhook)

        params2 = {'p1': 'v3', 'p2': 'v4'}
        res = self.eng.webhook_trigger(self.ctx, webhook['id'], params2)

        # verify action is fired
        action_id = res['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, consts.CLUSTER_SCALE_OUT,
                            'webhook_action_%s' % webhook['id'][:8],
                            'CLUSTER_FULL_ID', cause=action_mod.CAUSE_RPC,
                            inputs=params2)

        notify.assert_called_once_with(action_id=action_id)

    @mock.patch.object(webhook_mod.Webhook, 'generate_url')
    @mock.patch.object(common_utils, 'encrypt')
    def test_webhook_delete(self, mock_encrypt, mock_url):
        mock_url.return_value = 'test-url', 'test-key'
        mock_encrypt.return_value = 'encrypted text', 'test-key'

        cluster = self._create_cluster('c1')
        webhook = self.eng.webhook_create(self.ctx, cluster['id'], 'cluster',
                                          consts.CLUSTER_SCALE_OUT)

        webhook_id = webhook['id']
        result = self.eng.webhook_delete(self.ctx, webhook_id)
        self.assertIsNone(result)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_get, self.ctx, webhook_id)
        self.assertEqual(exception.WebhookNotFound, ex.exc_info[0])

    def test_webhook_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_get, self.ctx, 'fake-id')

        self.assertEqual(exception.WebhookNotFound, ex.exc_info[0])
