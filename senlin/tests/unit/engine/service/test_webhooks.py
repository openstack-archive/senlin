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
import six
import testtools

from senlin.common import consts
from senlin.common import exception
from senlin.common import utils as common_utils
from senlin.engine.actions import base as action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import service
from senlin.engine import webhook as webhook_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


@testtools.skip("Skip until webhook rework is completed.")
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

    @mock.patch.object(service.EngineService, 'webhook_find')
    def test_webhook_trigger_obj_id_not_found(self, mock_get):
        wh = mock.Mock()
        wh.obj_id = 'FAKE_ID'
        wh.obj_type = 'cluster'
        mock_get.return_value = wh

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_trigger,
                               self.ctx, 'FAKE_WEBHOOK')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: The referenced object '
                         '(FAKE_ID) is not found.',
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'FAKE_WEBHOOK')
        mock_get.reset_mock()

        wh.obj_type = 'node'
        mock_get.return_value = wh

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_trigger,
                               self.ctx, 'FAKE_WEBHOOK')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: The referenced object '
                         '(FAKE_ID) is not found.',
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'FAKE_WEBHOOK')
