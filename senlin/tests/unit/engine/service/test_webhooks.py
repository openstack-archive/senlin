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

from senlin.common import exception
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class WebhookTest(base.SenlinTestCase):

    def setUp(self):
        super(WebhookTest, self).setUp()
        self.ctx = utils.dummy_context(project='webhook_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_webhook_trigger(self, mock_get, mock_find, mock_action, notify):
        mock_find.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_get.return_value = mock.Mock(id='01234567-abcd-efef',
                                          cluster_id='FAKE_CLUSTER',
                                          action='DANCE',
                                          params={'foo': 'bar'})
        mock_action.return_value = 'ACTION_ID'

        res = self.eng.webhook_trigger(self.ctx, 'FAKE_RECEIVER',
                                       params={'kee': 'vee'})

        self.assertEqual({'action': 'ACTION_ID'}, res)

        mock_get.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, 'FAKE_CLUSTER', 'DANCE',
            name='webhook_01234567',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'kee': 'vee', 'foo': 'bar'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_webhook_trigger_receiver_not_found(self, mock_find):
        mock_find.side_effect = exception.ReceiverNotFound(receiver='RRR')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_trigger,
                               self.ctx, 'RRR')

        self.assertEqual(exception.ReceiverNotFound, ex.exc_info[0])
        self.assertEqual('The receiver (RRR) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'RRR')

    @mock.patch.object(service.EngineService, 'receiver_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_webhook_trigger_cluster_not_found(self, mock_cluster, mock_find):
        receiver = mock.Mock()
        receiver.cluster_id = 'BOGUS'
        mock_find.return_value = receiver
        mock_cluster.side_effect = exception.ClusterNotFound(cluster='BOGUS')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.webhook_trigger,
                               self.ctx, 'RRR')

        self.assertEqual(exception.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: The referenced cluster '
                         '(BOGUS) is not found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'RRR')
        mock_cluster.assert_called_once_with(self.ctx, 'BOGUS')
