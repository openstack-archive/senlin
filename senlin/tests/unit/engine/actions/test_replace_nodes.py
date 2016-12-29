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
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterReplaceNodesTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterReplaceNodesTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_replace_nodes(self, mock_wait, mock_start, mock_dep,
                              mock_get_node, mock_action, mock_update,
                              mock_load):
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=10)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'O_NODE_1': 'R_NODE_1'}
        action.outputs = {}

        origin_node = mock.Mock(id='O_NODE_1', cluster_id='CLUSTER_ID',
                                ACTIVE='ACTIVE', status='ACTIVE')
        replace_node = mock.Mock(id='R_NODE_1', cluster_id='',
                                 ACTIVE='ACTIVE', status='ACTIVE')
        mock_get_node.side_effect = [origin_node, replace_node]
        mock_action.side_effect = ['NODE_LEAVE_1', 'NODE_JOIN_1']
        mock_wait.return_value = (action.RES_OK, 'Free to fly!')

        # do the action
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed replacing nodes.', res_msg)

        mock_get_node.assert_has_calls([
            mock.call(action.context, 'O_NODE_1'),
            mock.call(action.context, 'R_NODE_1')])
        mock_load.assert_called_once_with(
            action.context,
            'CLUSTER_ID')
        mock_action.assert_has_calls([
            mock.call(action.context, 'O_NODE_1', 'NODE_LEAVE',
                      name='node_leave_O_NODE_1',
                      cause='Derived Action'),
            mock.call(action.context, 'R_NODE_1', 'NODE_JOIN',
                      name='node_join_R_NODE_1',
                      cause='Derived Action',
                      inputs={'cluster_id': 'CLUSTER_ID'})])

        mock_dep.assert_has_calls([
            mock.call(action.context,
                      ['NODE_JOIN_1'],
                      'CLUSTER_ACTION_ID'),
            mock.call(action.context,
                      ['NODE_JOIN_1'],
                      'NODE_LEAVE_1')])

        mock_update.assert_has_calls([
            mock.call(action.context,
                      'NODE_JOIN_1',
                      {'status': 'READY'}),
            mock.call(action.context,
                      'NODE_LEAVE_1',
                      {'status': 'READY'})])
        mock_start.assert_called_once_with()

        mock_wait.assert_called_once_with()

        cluster.remove_node.assert_called_once_with(origin_node)
        cluster.add_node.assert_called_once_with(replace_node)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_REPLACE_NODES)

    @mock.patch.object(no.Node, 'get')
    def test_do_replace_nodes_original_not_found(self, mock_get_node,
                                                 mock_load):
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'ORIGIN_NODE': 'REPLACE_NODE'}
        origin_node = None
        replace_node = mock.Mock(id='REPLACE_NODE', cluster_id='',
                                 ACTIVE='ACTIVE', status='ACTIVE')
        mock_get_node.side_effect = [origin_node, replace_node]
        # do the action
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Original node ORIGIN_NODE not found.',
                         res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_replace_nodes_replacement_not_found(self, mock_get_node,
                                                    mock_load):
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'ORIGIN_NODE': 'REPLACE_NODE'}
        origin_node = mock.Mock(id='ORIGIN_NODE', cluster_id='CLUSTER_ID',
                                ACTIVE='ACTIVE', status='ACTIVE')
        replace_node = None
        mock_get_node.side_effect = [origin_node, replace_node]
        # do the action
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Replacement node REPLACE_NODE not found.',
                         res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_replace_nodes_not_a_member(self, mock_get_node,
                                           mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'ORIGIN_NODE': 'REPLACE_NODE'}

        origin_node = mock.Mock(id='ORIGIN_NODE', cluster_id='')
        mock_get_node.return_value = origin_node
        # do action
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node ORIGIN_NODE is not a member of the '
                         'cluster FAKE_CLUSTER.', res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_replace_nodes_node_already_member(self, mock_get_node,
                                                  mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'ORIGIN_NODE': 'REPLACE_NODE'}

        replace_node = mock.Mock(id='REPLACE_NODE',
                                 cluster_id='FAKE_CLUSTER')
        mock_get_node.return_value = replace_node

        # do it
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node REPLACE_NODE is already owned by cluster '
                         'FAKE_CLUSTER.', res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_replace_nodes_in_other_cluster(self, mock_get_node,
                                               mock_load):
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=10)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'ORIGIN_NODE': 'REPLACE_NODE'}
        action.outputs = {}

        origin_node = mock.Mock(id='ORIGIN_NODE', cluster_id='CLUSTER_ID',
                                ACTIVE='ACTIVE', status='ACTIVE')
        replace_node = mock.Mock(id='REPLACE_NODE', cluster_id='FAKE_CLUSTER',
                                 ACTIVE='ACTIVE', status='ACTIVE')
        mock_get_node.side_effect = [origin_node, replace_node]

        # do it
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node REPLACE_NODE is already owned by cluster '
                         'FAKE_CLUSTER.', res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_replace_nodes_node_not_active(self, mock_get_node, mock_load):
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=10)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'ORIGIN_NODE': 'REPLACE_NODE'}
        action.outputs = {}

        origin_node = mock.Mock(id='ORIGIN_NODE', cluster_id='CLUSTER_ID',
                                ACTIVE='ACTIVE', status='ACTIVE')
        replace_node = mock.Mock(id='REPLACE_NODE', cluster_id='',
                                 ACTIVE='ACTIVE', status='ERROR')
        mock_get_node.side_effect = [origin_node, replace_node]

        # do it
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node REPLACE_NODE is not in ACTIVE status.", res_msg)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_replace_failed_waiting(self, mock_wait, mock_start, mock_dep,
                                       mock_get_node, mock_action,
                                       mock_update, mock_load):
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=10)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'O_NODE_1': 'R_NODE_1'}
        action.outputs = {}

        origin_node = mock.Mock(id='O_NODE_1', cluster_id='CLUSTER_ID',
                                ACTIVE='ACTIVE', status='ACTIVE')
        replace_node = mock.Mock(id='R_NODE_1', cluster_id='',
                                 ACTIVE='ACTIVE', status='ACTIVE')
        mock_get_node.side_effect = [origin_node, replace_node]
        mock_action.side_effect = ['NODE_LEAVE_1', 'NODE_JOIN_1']
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        # do the action
        res_code, res_msg = action.do_replace_nodes()

        # assertions
        mock_action.assert_has_calls([
            mock.call(action.context, 'O_NODE_1', 'NODE_LEAVE',
                      name='node_leave_O_NODE_1',
                      cause='Derived Action'),
            mock.call(action.context, 'R_NODE_1', 'NODE_JOIN',
                      name='node_join_R_NODE_1',
                      cause='Derived Action',
                      inputs={'cluster_id': 'CLUSTER_ID'})])

        mock_dep.assert_has_calls([
            mock.call(action.context,
                      ['NODE_JOIN_1'],
                      'CLUSTER_ACTION_ID'),
            mock.call(action.context,
                      ['NODE_JOIN_1'],
                      'NODE_LEAVE_1')])

        mock_update.assert_has_calls([
            mock.call(action.context,
                      'NODE_JOIN_1',
                      {'status': 'READY'}),
            mock.call(action.context,
                      'NODE_LEAVE_1',
                      {'status': 'READY'})])

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)
