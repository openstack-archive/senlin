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
import copy
import mock

from senlin.common import scaleutils as su
from senlin.engine import cluster as cm
from senlin.objects import node as no
from senlin.policies import batch_policy as bp
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestBatchPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestBatchPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.batch',
            'version': '1.0',
            'properties': {
                'min_in_service': 1,
                'max_batch_size': 2,
                'pause_time': 60,
            }
        }

    def test_policy_init(self):
        policy = bp.BatchPolicy('test-batch', self.spec)

        self.assertIsNone(policy.id)
        self.assertEqual('test-batch', policy.name)
        self.assertEqual('senlin.policy.batch-1.0', policy.type)
        self.assertEqual(1, policy.min_in_service)
        self.assertEqual(2, policy.max_batch_size)
        self.assertEqual(60, policy.pause_time)

    def test__cal_batch_size_for_update(self):
        policy = bp.BatchPolicy('test-batch', self.spec)

        size, number = policy._cal_batch_size(5, 'CLUSTER_UPDATE')
        self.assertEqual(2, size)
        self.assertEqual(3, number)

    def test__cal_batch_size_for_delete_greater_than_max(self):
        policy = bp.BatchPolicy('test-batch', self.spec)

        size, number = policy._cal_batch_size(5, 'CLUSTER_DELETE')
        self.assertEqual(2, size)
        self.assertEqual(3, number)

    def test__cal_batch_size_for_delete_less_than_max(self):
        spec = copy.deepcopy(self.spec)
        spec['properties']['max_batch_size'] = 3

        policy = bp.BatchPolicy('test-batch', spec)

        size, number = policy._cal_batch_size(4, 'CLUSTER_DELETE')
        self.assertEqual(2, size)
        self.assertEqual(2, number)

    def test__cal_batch_size_less_than_min(self):
        spec = copy.deepcopy(self.spec)
        spec['properties']['min_in_service'] = 2
        policy = bp.BatchPolicy('test-batch', spec)

        size, number = policy._cal_batch_size(1, 'CLUSTER_UPDATE')
        self.assertEqual(1, size)
        self.assertEqual(1, number)

    def test__cal_batch_size_with_default_max(self):
        spec = copy.deepcopy(self.spec)
        spec['properties']['max_batch_size'] = -1

        policy = bp.BatchPolicy('test-batch', spec)

        size, number = policy._cal_batch_size(5, 'CLUSTER_UPDATE')
        self.assertEqual(4, size)
        self.assertEqual(2, number)

    def test__pick_nodes_all_active(self):
        node1 = mock.Mock(id='1', status='ACTIVE')
        node2 = mock.Mock(id='2', status='ACTIVE')
        node3 = mock.Mock(id='3', status='ACTIVE')

        bad = []
        good = [node1, node2, node3]

        policy = bp.BatchPolicy('test-batch', self.spec)
        nodes = policy._pick_nodes(2, 2, bad, good)

        self.assertEqual(2, len(nodes))
        self.assertIn(node1.id, nodes[0])
        self.assertIn(node2.id, nodes[0])
        self.assertIn(node3.id, nodes[1])

    def test__pick_nodes_with_error_nodes(self):
        node1 = mock.Mock(id='1', status='ACTIVE')
        node2 = mock.Mock(id='2', status='ACTIVE')
        node3 = mock.Mock(id='3', status='ERROR')

        bad = [node3.id]
        good = [node1, node2]

        policy = bp.BatchPolicy('test-batch', self.spec)

        nodes = policy._pick_nodes(2, 2, bad, good)

        self.assertEqual(2, len(nodes))
        self.assertIn(node3.id, nodes[0])
        self.assertIn(node1.id, nodes[0])
        self.assertIn(node2.id, nodes[1])

    @mock.patch.object(bp.BatchPolicy, '_pick_nodes')
    @mock.patch.object(bp.BatchPolicy, '_cal_batch_size')
    @mock.patch.object(su, 'filter_error_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test__create_plan_for_update(self, mock_count, mock_filter,
                                     mock_cal, mock_pick):
        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_UPDATE'
        cluster = mock.Mock(id='cid')
        node1 = mock.Mock(id='1', status='ACTIVE')
        node2 = mock.Mock(id='2', status='ACTIVE')
        node3 = mock.Mock(id='3', status='ACTIVE')
        cluster.nodes = [node1, node2, node3]

        count = 3
        mock_count.return_value = count
        mock_filter.return_value = ([], [node1, node2, node3])
        mock_cal.return_value = (2, 2)
        mock_pick.return_value = [{'1', '2'}, {'3'}]

        policy = bp.BatchPolicy('test-batch', self.spec)
        res, plan = policy._create_plan(cluster, action)
        excepted_plan = {
            'pause_time': self.spec['properties']['pause_time'],
            'plan': [{'1', '2'}, {'3'}]
        }
        self.assertTrue(res)
        self.assertEqual(excepted_plan, plan)

        mock_count.assert_called_once_with(action.context, cluster.id)
        mock_filter.assert_called_once_with(cluster.nodes)
        mock_cal.assert_called_once_with(count, 'CLUSTER_UPDATE')
        mock_pick.assert_called_once_with(2, 2, [], [node1, node2, node3])

    @mock.patch.object(bp.BatchPolicy, '_cal_batch_size')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test__create_plan_for_delete(self, mock_count, mock_cal):
        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_DELETE'
        cluster = mock.Mock(id='cid')
        node1 = mock.Mock(id='1', status='ACTIVE')
        node2 = mock.Mock(id='2', status='ACTIVE')
        node3 = mock.Mock(id='3', status='ACTIVE')
        cluster.nodes = [node1, node2, node3]

        count = 3
        mock_count.return_value = count
        mock_cal.return_value = (2, 2)

        policy = bp.BatchPolicy('test-batch', self.spec)
        res, plan = policy._create_plan(cluster, action)
        excepted_plan = {
            'pause_time': self.spec['properties']['pause_time'],
            'batch_size': 2
        }
        self.assertTrue(res)
        self.assertEqual(excepted_plan, plan)

        mock_count.assert_called_once_with(action.context, cluster.id)
        mock_cal.assert_called_once_with(count, 'CLUSTER_DELETE')

    @mock.patch.object(no.Node, 'count_by_cluster')
    def test__create_plan_for_update_no_node(self, mock_count):
        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_UPDATE'
        cluster = mock.Mock(id='cid')
        mock_count.return_value = 0

        policy = bp.BatchPolicy('test-batch', self.spec)
        excepted_plan = {
            'pause_time': self.spec['properties']['pause_time'],
            'plan': [{}]
        }
        res, value = policy._create_plan(cluster, action)
        self.assertTrue(res)
        self.assertEqual(excepted_plan, value)
        mock_count.assert_called_once_with(action.context, cluster.id)

    @mock.patch.object(no.Node, 'count_by_cluster')
    def test__create_plan_for_delete_no_node(self, mock_count):
        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_DELETE'
        cluster = mock.Mock(id='cid')
        mock_count.return_value = 0

        policy = bp.BatchPolicy('test-batch', self.spec)
        excepted_plan = {
            'pause_time': self.spec['properties']['pause_time'],
            'batch_size': 0,
        }
        res, value = policy._create_plan(cluster, action)
        self.assertTrue(res)
        self.assertEqual(excepted_plan, value)
        mock_count.assert_called_once_with(action.context, cluster.id)

    @mock.patch.object(bp.BatchPolicy, '_create_plan')
    @mock.patch.object(cm.Cluster, 'load')
    def test_pre_op_for_update(self, mock_load, mock_plan):
        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_UPDATE'
        cluster = mock.Mock(id='cid')

        mock_load.return_value = cluster

        excepted_plan = {
            'pause_time': self.spec['properties']['pause_time'],
            'plan': [{'1', '2'}, {'3'}]
        }
        mock_plan.return_value = (True, excepted_plan)

        policy = bp.BatchPolicy('test-batch', self.spec)
        policy.pre_op(cluster.id, action)

        mock_load.assert_called_once_with(action.context, cluster.id)
        mock_plan.assert_called_once_with(cluster, action)

    @mock.patch.object(bp.BatchPolicy, '_create_plan')
    @mock.patch.object(cm.Cluster, 'load')
    def test_pre_op_for_delete(self, mock_load, mock_plan):
        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_DELETE'
        cluster = mock.Mock(id='cid')

        mock_load.return_value = cluster

        excepted_plan = {
            'pause_time': self.spec['properties']['pause_time'],
            'batch_size': 2,
        }
        mock_plan.return_value = (True, excepted_plan)

        policy = bp.BatchPolicy('test-batch', self.spec)
        policy.pre_op(cluster.id, action)

        mock_load.assert_called_once_with(action.context, cluster.id)
        mock_plan.assert_called_once_with(cluster, action)
