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
from senlin.engine import node as nm
from senlin.objects import action as ao
from senlin.objects import dependency as dobj
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterAddNodesTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterAddNodesTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    @mock.patch.object(nm.Node, 'load')
    def test_do_add_nodes_single(self, mock_load_node, mock_wait, mock_start,
                                 mock_update, mock_dep, mock_action,
                                 mock_count, mock_get, mock_load):
        cluster = mock.Mock(id='CLUSTER_ID', min_size=1, max_size=5)
        mock_load.return_value = cluster
        mock_count.return_value = 2
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  id='CLUSTER_ACTION_ID',
                                  inputs={'nodes': ['NODE_1']},
                                  data={}, outputs={})
        db_node = mock.Mock(id='NODE_1', cluster_id='', ACTIVE='ACTIVE',
                            status='ACTIVE')
        mock_get.return_value = db_node
        mock_action.return_value = 'NODE_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed adding nodes.', res_msg)

        mock_load.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_get.assert_called_once_with(action.context, 'NODE_1')
        mock_count.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_JOIN',
            name='node_join_NODE_1', cause='Derived Action',
            inputs={'cluster_id': 'CLUSTER_ID'})
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(
            action.context, 'NODE_ACTION_ID', {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_ADD_NODES, desired_capacity=3)
        self.assertEqual({'nodes_added': ['NODE_1']}, action.outputs)
        self.assertEqual({'creation': {'nodes': ['NODE_1']}},
                         action.data)
        mock_load_node.assert_called_once_with(action.context, db_node=db_node)
        cluster.add_node.assert_called_once_with(mock_load_node.return_value)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    @mock.patch.object(nm.Node, 'load')
    def test_do_add_nodes_multi(self, mock_load_node, mock_wait, mock_start,
                                mock_update, mock_dep, mock_action,
                                mock_count, mock_get, mock_load):

        cluster = mock.Mock(id='CLUSTER_ID', min_size=1, max_size=5)
        mock_load.return_value = cluster
        mock_count.return_value = 2
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  id='CLUSTER_ACTION_ID',
                                  inputs={'nodes': ['NODE_1', 'NODE_2']},
                                  outputs={}, data={})

        node1 = mock.Mock(id='NODE_1', cluster_id='', ACTIVE='ACTIVE',
                          status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='', ACTIVE='ACTIVE',
                          status='ACTIVE')
        mock_get.side_effect = [node1, node2]
        node_obj_1 = mock.Mock()
        node_obj_2 = mock.Mock()
        mock_load_node.side_effect = [node_obj_1, node_obj_2]
        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']
        mock_wait.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed adding nodes.', res_msg)

        mock_load.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_get.assert_has_calls([
            mock.call(action.context, 'NODE_1'),
            mock.call(action.context, 'NODE_2')])
        mock_count.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_action.assert_has_calls([
            mock.call(action.context, 'NODE_1', 'NODE_JOIN',
                      name='node_join_NODE_1', cause='Derived Action',
                      inputs={'cluster_id': 'CLUSTER_ID'}),
            mock.call(action.context, 'NODE_2', 'NODE_JOIN',
                      name='node_join_NODE_2', cause='Derived Action',
                      inputs={'cluster_id': 'CLUSTER_ID'})])

        mock_dep.assert_called_once_with(
            action.context,
            ['NODE_ACTION_1', 'NODE_ACTION_2'],
            'CLUSTER_ACTION_ID')
        mock_update.assert_has_calls([
            mock.call(action.context, 'NODE_ACTION_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_ACTION_2', {'status': 'READY'})
        ])
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_ADD_NODES, desired_capacity=4)
        self.assertEqual({'nodes_added': ['NODE_1', 'NODE_2']}, action.outputs)
        self.assertEqual({'creation': {'nodes': ['NODE_1', 'NODE_2']}},
                         action.data)
        mock_load_node.assert_has_calls([
            mock.call(action.context, db_node=node1),
            mock.call(action.context, db_node=node2)
        ])
        cluster.add_node.assert_has_calls([
            mock.call(node_obj_1), mock.call(node_obj_2)])

    @mock.patch.object(no.Node, 'get')
    def test_do_add_nodes_node_not_found(self, mock_get, mock_load):
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  inputs={'nodes': ['NODE_1']})
        mock_get.return_value = None

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node NODE_1 is not found.", res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_add_nodes_node_already_member(self, mock_get, mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  inputs={'nodes': ['NODE_1']}, data={})
        mock_get.return_value = mock.Mock(cluster_id='FAKE_CLUSTER')

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node NODE_1 is already owned by cluster "
                         "FAKE_CLUSTER.", res_msg)
        self.assertEqual({}, action.data)

    @mock.patch.object(no.Node, 'get')
    def test_do_add_nodes_node_in_other_cluster(self, mock_get, mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  inputs={'nodes': ['NODE_1']}, data={})
        mock_get.return_value = mock.Mock(cluster_id='ANOTHER_CLUSTER')

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node NODE_1 is already owned by cluster "
                         "ANOTHER_CLUSTER.", res_msg)

    @mock.patch.object(no.Node, 'get')
    def test_do_add_nodes_node_not_active(self, mock_get, mock_load):
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  inputs={'nodes': ['NODE_1']}, data={})
        mock_get.return_value = mock.Mock(cluster_id='', status='ERROR')

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node NODE_1 is not in ACTIVE status.", res_msg)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_add_nodes_failed_check(self, mock_count, mock_get,
                                       mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=2)
        mock_load.return_value = cluster
        node1 = mock.Mock(id='nid1', cluster_id='', ACTIVE='ACTIVE',
                          status='ACTIVE')
        node2 = mock.Mock(id='nid2', cluster_id='', ACTIVE='ACTIVE',
                          status='ACTIVE')
        mock_get.side_effect = [node1, node2]
        inputs = {'nodes': [node1.id, node2.id]}
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs=inputs)
        mock_count.return_value = 1

        # execute
        res_code, res_msg = action.do_add_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("The target capacity (3) is greater than the "
                         "cluster's max_size (2).", res_msg)
        self.assertEqual(2, mock_get.call_count)
        mock_count.assert_called_once_with(action.context, 'CID')

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    @mock.patch.object(nm.Node, 'load')
    def test_do_add_nodes_failed_waiting(self, mock_load_node, mock_wait,
                                         mock_start, mock_update, mock_dep,
                                         mock_action, mock_count, mock_get,
                                         mock_load):
        cluster = mock.Mock(id='CLUSTER_ID', min_size=1, max_size=5)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  id='CLUSTER_ACTION_ID', data={},
                                  inputs={'nodes': ['NODE_1']})
        mock_get.return_value = mock.Mock(id='NODE_1', cluster_id='',
                                          status='ACTIVE', ACTIVE='ACTIVE')
        mock_count.return_value = 3
        mock_action.return_value = 'NODE_ACTION_ID'
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        # do it
        res_code, res_msg = action.do_add_nodes()

        # assertions
        mock_load.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_get.assert_called_once_with(action.context, 'NODE_1')
        mock_count.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_JOIN',
            name='node_join_NODE_1', cause='Derived Action',
            inputs={'cluster_id': 'CLUSTER_ID'})
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(
            action.context, 'NODE_ACTION_ID', {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        self.assertEqual(0, cluster.eval_status.call_count)
        self.assertEqual({}, action.outputs)
        self.assertEqual({}, action.data)
        self.assertEqual(0, mock_load_node.call_count)
        self.assertEqual(0, cluster.add_node.call_count)
