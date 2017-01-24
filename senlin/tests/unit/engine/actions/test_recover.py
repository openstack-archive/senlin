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

from senlin.common import consts
from senlin.engine.actions import base as ab
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.engine import dispatcher
from senlin.objects import action as ao
from senlin.objects import dependency as dobj
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterRecoverTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterRecoverTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover(self, mock_wait, mock_start, mock_dep, mock_action,
                        mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', statu='ERROR')

        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING')
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster
        cluster.nodes = [node1, node2]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {}

        mock_action.return_value = 'NODE_RECOVER_ID'
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_recover()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)

        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_2', 'NODE_RECOVER',
            name='node_recover_NODE_2',
            cause=consts.CAUSE_DERIVED,
            inputs={}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover_with_data(self, mock_wait, mock_start, mock_dep,
                                  mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ERROR')
        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING')
        cluster.nodes = [node1]
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'health': {
                'recover_action': [{'name': 'REBOOT', 'params': None}],
                'fencing': ['COMPUTE'],
            }
        }

        mock_action.return_value = 'NODE_RECOVER_ID'
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_recover()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)

        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_RECOVER',
            name='node_recover_NODE_1',
            cause=consts.CAUSE_DERIVED,
            inputs={'operation': 'REBOOT', 'params': {'force': True}}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)

    def test_do_recover_all_nodes_active(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID')
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', status='ACTIVE')
        cluster.nodes = [node1, node2]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)

        # do it
        res_code, res_msg = action.do_recover()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)
        cluster.do_recover.assert_called_once_with(self.ctx)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover_failed_waiting(self, mock_wait, mock_start, mock_dep,
                                       mock_action, mock_update, mock_load):
        node = mock.Mock(id='NODE_1', cluster_id='CID', status='ERROR')
        cluster = mock.Mock(id='CID')
        cluster.do_recover.return_value = True
        cluster.nodes = [node]
        mock_load.return_value = cluster
        mock_action.return_value = 'NODE_ACTION_ID'

        action = ca.ClusterAction('FAKE_CLUSTER', 'CLUSTER_REOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'

        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        res_code, res_msg = action.do_recover()

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)

        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_RECOVER',
            name='node_recover_NODE_1',
            cause=consts.CAUSE_DERIVED,
            inputs={}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)
