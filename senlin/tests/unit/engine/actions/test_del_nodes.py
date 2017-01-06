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
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterDelNodesTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterDelNodesTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_del_nodes(self, mock_count, mock_delete, mock_get, mock_sleep,
                          mock_load):

        cluster = mock.Mock(id='FAKE_CLUSTER', min_size=0, max_size=5)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  id='CLUSTER_ACTION_ID', data={},
                                  inputs={'candidates': ['NODE_1', 'NODE_2']})

        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_CLUSTER')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_CLUSTER')
        mock_get.side_effect = [node1, node2]
        mock_count.return_value = 2
        mock_delete.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed deleting nodes.', res_msg)

        # these are default settings
        expected = {
            'deletion': {
                'destroy_after_deletion': False,
                'grace_period': 0,
                'reduce_desired_capacity': True,
            }
        }
        self.assertEqual(expected, action.data)

        mock_get.assert_has_calls([
            mock.call(action.context, 'NODE_1'),
            mock.call(action.context, 'NODE_2')])
        mock_count.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        mock_delete.assert_called_once_with(['NODE_1', 'NODE_2'])
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_DEL_NODES, desired_capacity=0)

    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_del_nodes_with_deletion_policy(self, mock_count, mock_delete,
                                               mock_get, mock_sleep,
                                               mock_load):
        cid = 'FAKE_CLUSTER'
        cluster = mock.Mock(id=cid, min_size=0, max_size=5,
                            desired_capacity=4)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  id='CLUSTER_ACTION_ID',
                                  inputs={'candidates': ['NODE_1', 'NODE_2']})
        action.data = {
            'deletion': {
                'count': 2,
                # the 'candidates' value will be ignored
                'candidates': ['NODE_1', 'NODE_2'],
                'destroy_after_deletion': True,
                'grace_period': 2,
                'reduce_desired_capacity': False,
            }
        }

        node1 = mock.Mock(id='NODE_1', cluster_id=cid)
        node2 = mock.Mock(id='NODE_2', cluster_id=cid)
        mock_get.side_effect = [node1, node2]
        mock_count.return_value = 4
        mock_delete.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed deleting nodes.', res_msg)
        mock_get.assert_has_calls([
            mock.call(action.context, 'NODE_1'),
            mock.call(action.context, 'NODE_2')])
        mock_count.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        mock_delete.assert_called_once_with(['NODE_1', 'NODE_2'])
        self.assertTrue(action.data['deletion']['destroy_after_deletion'])
        mock_sleep.assert_called_once_with(2)
        # Note: desired_capacity not decreased due to policy enforcement
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_DEL_NODES)

    @mock.patch.object(no.Node, 'get')
    def test_do_del_nodes_node_not_found(self, mock_get, mock_load):
        cluster = mock.Mock()
        mock_load.return_value = cluster
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  inputs={'candidates': ['NODE_1', 'NODE_2']})
        mock_get.return_value = None

        # do it
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Nodes not found: ['NODE_1', 'NODE_2'].", res_msg)
        expected = {
            'deletion': {
                'destroy_after_deletion': False,
                'grace_period': 0,
                'reduce_desired_capacity': True,
            }
        }
        self.assertEqual(expected, action.data)

    @mock.patch.object(no.Node, 'get')
    def test_do_del_nodes_node_not_member(self, mock_get, mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_load.return_value = cluster
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  inputs={'candidates': ['NODE_1', 'NODE_2']})
        node1 = mock.Mock(cluster_id='')
        node2 = mock.Mock(cluster_id='ANOTHER_CLUSTER')
        mock_get.side_effect = [node1, node2]

        # do it
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual("Completed deleting nodes.", res_msg)
        expected = {
            'deletion': {
                'destroy_after_deletion': False,
                'grace_period': 0,
                'reduce_desired_capacity': True,
            }
        }
        self.assertEqual(expected, action.data)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_del_nodes_failed_delete(self, mock_count, mock_delete,
                                        mock_get, mock_load):

        cluster = mock.Mock(id='FAKE_CLUSTER', min_size=0, max_size=5)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  inputs={'candidates': ['NODE_1']}, data={})
        node1 = mock.Mock(cluster_id='FAKE_CLUSTER')
        mock_get.side_effect = [node1]
        mock_count.return_value = 3
        mock_delete.return_value = (action.RES_ERROR, 'Things went bad.')

        # do it
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Things went bad.", res_msg)
        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        mock_get.assert_called_once_with(action.context, 'NODE_1')
        mock_count.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_DEL_NODES, desired_capacity=2)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_del_nodes_failed_check(self, mock_count, mock_get,
                                       mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=2)
        mock_load.return_value = cluster
        node1 = mock.Mock(id='nid1', cluster_id='CID', ACTIVE='ACTIVE',
                          status='ACTIVE')
        mock_get.side_effect = [node1]
        inputs = {'candidates': [node1.id]}
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs=inputs)
        mock_count.return_value = 1

        # execute
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("The target capacity (0) is less than the "
                         "cluster's min_size (1).", res_msg)
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_get.assert_called_once_with(action.context, 'nid1')
