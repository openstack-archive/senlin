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
class ClusterOperationTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterOperationTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_operation(self, mock_wait, mock_start, mock_dep, mock_action,
                          mock_update, mock_load):
        cluster = mock.Mock(id='FAKE_ID')
        cluster.do_operation.return_value = True
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_OPERATION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {
            'operation': 'dance',
            'params': {'style': 'tango'},
            'nodes': ['NODE_ID_1', 'NODE_ID_2'],
        }
        mock_action.side_effect = ['NODE_OP_ID_1', 'NODE_OP_ID_2']
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_operation()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual("Cluster operation 'dance' completed.", res_msg)

        cluster.do_operation.assert_called_once_with(action.context,
                                                     operation='dance')
        mock_action.assert_has_calls([
            mock.call(action.context, 'NODE_ID_1', 'NODE_OPERATION',
                      name='node_dance_NODE_ID_', cause=consts.CAUSE_DERIVED,
                      inputs={
                          'operation': 'dance',
                          'params': {'style': 'tango'}
                      }),
            mock.call(action.context, 'NODE_ID_2', 'NODE_OPERATION',
                      name='node_dance_NODE_ID_', cause=consts.CAUSE_DERIVED,
                      inputs={
                          'operation': 'dance',
                          'params': {'style': 'tango'}
                      }),
        ])
        mock_dep.assert_called_once_with(
            action.context, ['NODE_OP_ID_1', 'NODE_OP_ID_2'],
            'CLUSTER_ACTION_ID')
        mock_update.assert_has_calls([
            mock.call(action.context, 'NODE_OP_ID_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_OP_ID_2', {'status': 'READY'}),
        ])
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(action.context, 'dance')

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_operation_failed_wait(self, mock_wait, mock_start, mock_dep,
                                      mock_action, mock_update, mock_load):
        cluster = mock.Mock(id='FAKE_ID')
        cluster.do_operation.return_value = True
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_OPERATION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {
            'operation': 'dance',
            'params': {'style': 'tango'},
            'nodes': ['NODE_ID_1', 'NODE_ID_2'],
        }
        mock_action.side_effect = ['NODE_OP_ID_1', 'NODE_OP_ID_2']
        mock_wait.return_value = (action.RES_ERROR, 'Something is wrong')

        # do it
        res_code, res_msg = action.do_operation()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Something is wrong", res_msg)

        cluster.do_operation.assert_called_once_with(action.context,
                                                     operation='dance')
        mock_action.assert_has_calls([
            mock.call(action.context, 'NODE_ID_1', 'NODE_OPERATION',
                      name='node_dance_NODE_ID_', cause=consts.CAUSE_DERIVED,
                      inputs={
                          'operation': 'dance',
                          'params': {'style': 'tango'}
                      }),
            mock.call(action.context, 'NODE_ID_2', 'NODE_OPERATION',
                      name='node_dance_NODE_ID_', cause=consts.CAUSE_DERIVED,
                      inputs={
                          'operation': 'dance',
                          'params': {'style': 'tango'}
                      }),
        ])
        mock_dep.assert_called_once_with(
            action.context, ['NODE_OP_ID_1', 'NODE_OP_ID_2'],
            'CLUSTER_ACTION_ID')
        mock_update.assert_has_calls([
            mock.call(action.context, 'NODE_OP_ID_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_OP_ID_2', {'status': 'READY'}),
        ])
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(action.context, 'dance')
