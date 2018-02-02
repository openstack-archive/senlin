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

import eventlet
import mock

from senlin.common import consts
from senlin.common import scaleutils
from senlin.engine.actions import base as base_action
from senlin.engine.actions import node_action
from senlin.engine import cluster as cluster_mod
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock as lock
from senlin.objects import action as ao
from senlin.objects import node as node_obj
from senlin.policies import base as policy_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(node_mod.Node, 'load')
class NodeActionTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_do_create_okay(self, mock_load):
        node = mock.Mock(id='NID')
        node.do_create = mock.Mock(return_value=True)
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)

        res_code, res_msg = action.do_create()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node created successfully.', res_msg)
        node.do_create.assert_called_once_with(action.context)

    def test_do_create_failed(self, mock_load):
        node = mock.Mock(id='NID')
        node.do_create = mock.Mock(return_value=False)
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)

        # Test node creation failure path
        res_code, res_msg = action.do_create()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node creation failed.', res_msg)
        node.do_create.assert_called_once_with(action.context)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_create_with_cluster_id_success(self, mock_c_load, mock_count,
                                               mock_check, mock_load):
        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_create = mock.Mock(return_value=True)
        mock_load.return_value = node
        mock_count.return_value = 11
        mock_check.return_value = None
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_RPC)

        # do it
        res_code, res_msg = action.do_create()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 11, None, None, True)
        node.do_create.assert_called_once_with(action.context)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_CREATE, desired_capacity=11)

    @mock.patch.object(node_obj.Node, 'update')
    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_create_with_cluster_id_failed_checking(
            self, mock_c_load, mock_count, mock_check, mock_update, mock_load):

        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_create = mock.Mock(return_value=True)
        mock_load.return_value = node
        mock_count.return_value = 11
        mock_check.return_value = 'overflow'
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_RPC)

        # do it
        res_code, res_msg = action.do_create()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('overflow', res_msg)
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 11, None, None, True)
        mock_update.assert_called_once_with(action.context, 'NID',
                                            {'cluster_id': '',
                                             'status': consts.NS_ERROR})
        self.assertEqual(0, node.do_create.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_create_with_cluster_id_failed_creation(
            self, mock_c_load, mock_count, mock_check, mock_load):

        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_create = mock.Mock(return_value=False)
        mock_load.return_value = node
        mock_count.return_value = 11
        mock_check.return_value = ''
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_RPC)

        # do it
        res_code, res_msg = action.do_create()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node creation failed.', res_msg)
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 11, None, None, True)
        node.do_create.assert_called_once_with(action.context)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_CREATE, desired_capacity=11)

    @mock.patch.object(ao.Action, 'delete_by_target')
    def test_do_delete_okay(self, mock_action, mock_load):
        node = mock.Mock(id='NID')
        node.do_delete = mock.Mock(return_value=True)
        mock_load.return_value = node
        action = node_action.NodeAction('ID', 'ACTION', self.ctx)

        # do it
        res_code, res_msg = action.do_delete()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        node.do_delete.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'ID', action_excluded=['NODE_DELETE'],
            status=['SUCCEEDED', 'FAILED'])

    def test_do_delete_failed(self, mock_load):
        node = mock.Mock(id='NID')
        node.do_delete = mock.Mock(return_value=False)
        mock_load.return_value = node
        action = node_action.NodeAction('ID', 'ACTION', self.ctx)

        # Test failed node deletion path
        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node deletion failed.', res_msg)
        node.do_delete.assert_called_once_with(action.context)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_success(self, mock_c_load, mock_count,
                                               mock_check, mock_load):
        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_delete.return_value = True
        mock_load.return_value = node
        mock_count.return_value = 2
        mock_check.return_value = None
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_RPC)

        # do it
        res_code, res_msg = action.do_delete()

        # assertion
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_DELETE, desired_capacity=1)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_failed_checking(
            self, mock_c_load, mock_count, mock_check, mock_load):

        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_delete.return_value = True
        mock_load.return_value = node
        mock_count.return_value = 2
        mock_check.return_value = 'underflow'
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_RPC)

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('underflow', res_msg)

        mock_load.assert_called_once_with(action.context, node_id='NID')
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        self.assertEqual(0, node.do_delete.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_failed_deletion(
            self, mock_c_load, mock_count, mock_check, mock_load):

        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_delete.return_value = False
        mock_load.return_value = node
        mock_count.return_value = 2
        mock_check.return_value = None
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_RPC)

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node deletion failed.', res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NID')
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        node.do_delete.assert_called_once_with(action.context)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_DELETE)

    @mock.patch.object(eventlet, 'sleep')
    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_and_grace_period(
            self, mock_c_load, mock_count, mock_check, mock_sleep, mock_load):

        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_delete.return_value = True
        mock_load.return_value = node
        mock_count.return_value = 2
        mock_check.return_value = None
        action = node_action.NodeAction(
            node.id, 'ACTION', self.ctx, cause=consts.CAUSE_RPC,
            data={'deletion': {'grace_period': 10}})

        # do it
        res_code, res_msg = action.do_delete()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NID')
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        mock_sleep.assert_called_once_with(10)
        node.do_delete.assert_called_once_with(action.context)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_DELETE, desired_capacity=1)

    @mock.patch.object(eventlet, 'sleep')
    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_and_forced_reduce(
            self, mock_c_load, mock_count, mock_check, mock_sleep, mock_load):
        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_delete.return_value = True
        mock_load.return_value = node
        mock_count.return_value = 2
        mock_check.return_value = None
        action = node_action.NodeAction(
            'NID', 'ACTION', self.ctx,
            cause=consts.CAUSE_RPC,
            data={'deletion': {'reduce_desired_capacity': True}})

        # do it
        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NID')
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        node.do_delete.assert_called_once_with(action.context)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_DELETE, desired_capacity=1)

    @mock.patch.object(eventlet, 'sleep')
    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(node_obj.Node, 'count_by_cluster')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_and_forced_no_reduce(
            self, mock_c_load, mock_count, mock_check, mock_sleep, mock_load):
        cluster = mock.Mock(id='CID')
        mock_c_load.return_value = cluster
        node = mock.Mock(id='NID', cluster_id='CID')
        node.do_delete.return_value = True
        mock_load.return_value = node
        mock_count.return_value = 2
        mock_check.return_value = None
        action = node_action.NodeAction(
            'NID', 'ACTION', self.ctx,
            cause=consts.CAUSE_RPC,
            data={'deletion': {'reduce_desired_capacity': False}})

        # do it
        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NID')
        mock_c_load.assert_called_once_with(action.context, 'CID')
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        node.do_delete.assert_called_once_with(action.context)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.NODE_DELETE)

    def test_do_delete_derived_success(self, mock_load):

        node = mock.Mock(id='NID', cluster_id='CLUSTER_ID')
        node.do_delete.return_value = True
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_DERIVED)

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NID')

    def test_do_delete_derived_failed_deletion(self, mock_load):

        node = mock.Mock(id='NID', cluster_id='CLUSTER_ID')
        node.do_delete.return_value = False
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=consts.CAUSE_DERIVED)

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node deletion failed.', res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NID')

    def test_do_update(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        inputs = {"new_profile_id": "FAKE_PROFILE_ID"}
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        inputs=inputs)

        # Test failed node update path
        node.do_update = mock.Mock(return_value=None)
        res_code, res_msg = action.do_update()
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node update failed.', res_msg)
        node.do_update.assert_called_once_with(action.context, inputs)
        node.reset_mock()

        # Test node update success path
        node.do_update = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_update()
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node updated successfully.', res_msg)
        node.do_update.assert_called_once_with(action.context, inputs)

    def test_do_update_no_need_update(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        node.profile_id = 'PROFILE_ID'
        mock_load.return_value = node
        inputs = {"new_profile_id": "PROFILE_ID"}
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        inputs=inputs)

        # Test node update success path
        node.do_update = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_update()
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('No property to update.', res_msg)
        self.assertFalse(node.do_update.called)

    def test_do_join_success(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(node.id, 'NODE_JOIN', self.ctx,
                                        inputs=inputs)
        node.do_join = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_join()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node successfully joined cluster.', res_msg)
        node.do_join.assert_called_once_with(action.context, 'FAKE_ID')

    def test_do_join_failed_do_join(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(node.id, 'NODE_JOIN', self.ctx,
                                        inputs=inputs)
        node.do_join = mock.Mock(return_value=False)

        # Test failed node join path
        res_code, res_msg = action.do_join()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node failed in joining cluster.', res_msg)
        node.do_join.assert_called_once_with(action.context, 'FAKE_ID')

    def test_do_leave_success(self, mock_load):
        node = mock.Mock(id='NID', cluster_id='CID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'NODE_LEAVE', self.ctx)
        node.do_leave = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_leave()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node successfully left cluster.', res_msg)
        node.do_leave.assert_called_once_with(action.context)

    def test_do_leave_failed_leave(self, mock_load):
        node = mock.Mock(id='NID', cluster_id='CID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'NODE_LEAVE', self.ctx)
        node.do_leave = mock.Mock(return_value=False)

        # Test failed node join path
        res_code, res_msg = action.do_leave()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node failed in leaving cluster.', res_msg)
        node.do_leave.assert_called_once_with(action.context)

    def test_do_check_success(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)
        node.do_check = mock.Mock(return_value=True)

        res_code, res_msg = action.do_check()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node check succeeded.', res_msg)
        node.do_check.assert_called_once_with(action.context)

    def test_do_check_failed(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)
        node.do_check = mock.Mock(return_value=False)

        res_code, res_msg = action.do_check()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node check failed.', res_msg)
        node.do_check.assert_called_once_with(action.context)

    def test_do_recover_success(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)
        action.inputs = {'operation': ['SWIM', 'DANCE']}
        node.do_recover = mock.Mock(return_value=True)

        res_code, res_msg = action.do_recover()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node recovered successfully.', res_msg)
        node.do_recover.assert_called_once_with(action.context, action)

    def test_do_recover_failed(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)
        action.inputs = {'operation': ['SWIM', 'DANCE']}

        # Test node recover failure path
        node.do_recover = mock.Mock(return_value=False)
        res_code, res_msg = action.do_recover()
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node recover failed.', res_msg)
        node.do_recover.assert_called_once_with(action.context, action)

    def test_do_operation_success(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)
        action.inputs = {'operation': 'dance', 'params': {}}
        node.do_operation = mock.Mock(return_value=True)

        res_code, res_msg = action.do_operation()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual("Node operation 'dance' succeeded.", res_msg)
        node.do_operation.assert_called_once_with(action.context,
                                                  operation='dance',
                                                  params={})

    def test_do_operation_failed(self, mock_load):
        node = mock.Mock(id='NID')
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)
        action.inputs = {'operation': 'dance', 'params': {}}
        node.do_operation = mock.Mock(return_value=False)

        res_code, res_msg = action.do_operation()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node operation 'dance' failed.", res_msg)
        node.do_operation.assert_called_once_with(action.context,
                                                  operation='dance',
                                                  params={})

    def test_execute(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'NODE_SING', self.ctx)
        action.do_sing = mock.Mock(return_value=(action.RES_OK, 'GOOD'))

        res_code, res_msg = action._execute()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('GOOD', res_msg)
        action.do_sing.assert_called_once_with()

    @mock.patch.object(EVENT, 'error')
    def test_execute_bad_action(self, mock_error, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'NODE_DANCE', self.ctx)

        res_code, res_msg = action._execute()

        self.assertEqual(action.RES_ERROR, res_code)
        reason = 'Unsupported action: NODE_DANCE'
        self.assertEqual(reason, res_msg)
        mock_error.assert_called_once_with(action, 'error', reason)

    @mock.patch.object(lock, 'cluster_lock_acquire')
    def test_execute_failed_lock_cluster(self, mock_acquire, mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        node.id = 'NID'
        mock_load.return_value = node
        action = node_action.NodeAction('NODE_ID', 'NODE_FLY', self.ctx,
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        mock_acquire.return_value = None

        res_code, res_msg = action.execute()

        reason = 'Failed in locking cluster'
        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                             'ACTION_ID', None,
                                             lock.NODE_SCOPE, False)

    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    def test_execute_failed_policy_check(self, mock_check, mock_release,
                                         mock_acquire, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        node.cluster_id = 'FAKE_CLUSTER'
        mock_load.return_value = node

        action = node_action.NodeAction('NODE_ID', 'NODE_FLY', self.ctx,
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        action.data = {
            'status': policy_mod.CHECK_ERROR,
            'reason': 'Failed policy checking'
        }
        mock_acquire.return_value = action.id

        res_code, res_msg = action.execute()

        reason = 'Policy check: Failed policy checking'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                             'ACTION_ID', None,
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')

    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(lock, 'node_lock_acquire')
    @mock.patch.object(lock, 'node_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    def test_execute_no_policy_check(self, mock_check,
                                     mock_nl_release, mock_nl_acquire,
                                     mock_cl_release, mock_cl_acquire,
                                     mock_load):
        node_id = 'NODE_ID'
        node = mock.Mock(id=node_id, cluster_id='FAKE_CLUSTER')
        mock_load.return_value = node
        action = node_action.NodeAction(node_id, 'NODE_FLY', self.ctx,
                                        cause=consts.CAUSE_DERIVED)
        action.id = 'ACTION_ID'
        action.owner = 'OWNER'
        mock_exec = self.patchobject(action, '_execute',
                                     return_value=(action.RES_OK, 'Good'))
        mock_nl_acquire.return_value = action.id

        res_code, res_msg = action.execute()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Good', res_msg)
        mock_load.assert_called_once_with(action.context, node_id=node_id)
        self.assertEqual(0, mock_cl_acquire.call_count)
        self.assertEqual(0, mock_cl_release.call_count)
        mock_nl_acquire.assert_called_once_with(self.ctx, node_id,
                                                action.id, action.owner,
                                                False)
        mock_nl_release.assert_called_once_with(node_id, action.id)
        mock_exec.assert_called_once_with()
        self.assertEqual(0, mock_check.call_count)

    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    @mock.patch.object(lock, 'node_lock_acquire')
    @mock.patch.object(lock, 'node_lock_release')
    def test_execute_failed_locking_node(self, mock_release_node,
                                         mock_acquire_node, mock_check,
                                         mock_release, mock_acquire,
                                         mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        node.id = 'NODE_ID'
        mock_load.return_value = node

        action = node_action.NodeAction('NODE_ID', 'NODE_FLY', self.ctx,
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        action.data = {
            'status': policy_mod.CHECK_OK,
            'reason': 'Policy checking passed'
        }
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = None

        res_code, res_msg = action.execute()

        reason = 'Failed in locking node'
        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                             'ACTION_ID', None,
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')
        mock_acquire_node.assert_called_once_with(self.ctx, 'NODE_ID',
                                                  'ACTION_ID', None, False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')

    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    @mock.patch.object(lock, 'node_lock_acquire')
    @mock.patch.object(lock, 'node_lock_release')
    def test_execute_success(self, mock_release_node, mock_acquire_node,
                             mock_check, mock_release, mock_acquire,
                             mock_load):
        def fake_execute():
            node.cluster_id = ''
            return (action.RES_OK, 'Execution ok')

        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        node.id = 'NODE_ID'
        mock_load.return_value = node

        action = node_action.NodeAction(node.id, 'NODE_FLY', self.ctx,
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        # check result
        action.data = {
            'status': policy_mod.CHECK_OK,
            'reason': 'Policy checking passed'
        }
        self.patchobject(action, '_execute', side_effect=fake_execute)
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = 'ACTION_ID'

        res_code, res_msg = action.execute()

        reason = 'Execution ok'
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                             'ACTION_ID', None,
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_acquire_node.assert_called_once_with(self.ctx, 'NODE_ID',
                                                  'ACTION_ID', None, False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')
        check_calls = [
            mock.call('FAKE_CLUSTER', 'BEFORE'),
            mock.call('FAKE_CLUSTER', 'AFTER')
        ]
        mock_check.assert_has_calls(check_calls)

    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    @mock.patch.object(lock, 'node_lock_acquire')
    @mock.patch.object(lock, 'node_lock_release')
    def test_execute_failed_execute(self, mock_release_node, mock_acquire_node,
                                    mock_check, mock_release, mock_acquire,
                                    mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        node.id = 'NODE_ID'
        mock_load.return_value = node

        action = node_action.NodeAction(node.id, 'NODE_FLY', self.ctx,
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        # check result
        action.data = {
            'status': policy_mod.CHECK_OK,
            'reason': 'Policy checking passed'
        }
        self.patchobject(action, '_execute',
                         return_value=(action.RES_ERROR, 'Execution Failed'))
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = 'ACTION_ID'

        res_code, res_msg = action.execute()

        reason = 'Execution Failed'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                             'ACTION_ID', None,
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_acquire_node.assert_called_once_with(self.ctx, 'NODE_ID',
                                                  'ACTION_ID', None, False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')

    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(lock, 'node_lock_acquire')
    @mock.patch.object(lock, 'node_lock_release')
    def test_execute_failed_post_check(self, mock_release_node,
                                       mock_acquire_node,
                                       mock_release, mock_acquire,
                                       mock_load):

        def fake_check(cluster_id, target):
            if target == 'BEFORE':
                action.data = {
                    'status': policy_mod.CHECK_OK,
                    'reason': 'Policy checking passed'
                }
            else:
                action.data = {
                    'status': policy_mod.CHECK_ERROR,
                    'reason': 'Policy checking failed'
                }

        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        node.id = 'NODE_ID'
        mock_load.return_value = node

        action = node_action.NodeAction('NODE_ID', 'NODE_FLY', self.ctx,
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        mock_check = self.patchobject(action, 'policy_check',
                                      side_effect=fake_check)
        # check result
        self.patchobject(action, '_execute',
                         return_value=(action.RES_OK, 'Ignored'))
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = 'ACTION_ID'

        res_code, res_msg = action.execute()

        reason = 'Policy check: Policy checking failed'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                             'ACTION_ID', None,
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        check_calls = [
            mock.call('FAKE_CLUSTER', 'BEFORE'),
            mock.call('FAKE_CLUSTER', 'AFTER')
        ]
        mock_check.assert_has_calls(check_calls)
        mock_acquire_node.assert_called_once_with(self.ctx, 'NODE_ID',
                                                  'ACTION_ID', None, False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')
