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

from senlin.common import exception
from senlin.common import scaleutils
from senlin.engine.actions import base as base_action
from senlin.engine.actions import node_action
from senlin.engine import cluster as cluster_mod
from senlin.engine import event as event_mod
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock as lock
from senlin.policies import base as policy_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class NodeActionTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_do_create(self):
        node = mock.Mock()
        node.do_create = mock.Mock(return_value=None)
        action = node_action.NodeAction(self.ctx, 'ID', 'ACTION')

        # Test node creation failure path
        res_code, res_msg = action.do_create(node)
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node creation failed', res_msg)
        node.do_create.assert_called_once_with(action.context)
        node.reset_mock()

        # Test node creation success path
        node.do_create = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_create(node)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node created successfully', res_msg)
        node.do_create.assert_called_once_with(action.context)

    def test_do_delete(self):
        node = mock.Mock()
        node.do_delete = mock.Mock(return_value=None)
        action = node_action.NodeAction(self.ctx, 'ID', 'ACTION')

        # Test failed node deletion path
        res_code, res_msg = action.do_delete(node)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node deletion failed', res_msg)
        node.do_delete.assert_called_once_with(action.context)
        node.reset_mock()

        # Test node deletion success path
        node.do_delete = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_delete(node)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully', res_msg)
        node.do_delete.assert_called_once_with(action.context)

    def test_do_update(self):
        node = mock.Mock()
        inputs = {"new_profile_id": "FAKE_PROFILE_ID"}
        action = node_action.NodeAction(self.ctx, 'ID', 'ACT', inputs=inputs)

        # Test failed node update path
        node.do_update = mock.Mock(return_value=None)
        res_code, res_msg = action.do_update(node)
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node update failed', res_msg)
        node.do_update.assert_called_once_with(action.context, inputs)
        node.reset_mock()

        # Test node update success path
        node.do_update = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_update(node)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node updated successfully', res_msg)
        node.do_update.assert_called_once_with(action.context, inputs)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_join_success(self, mock_check, mock_load):
        node = mock.Mock()
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_JOIN',
                                        inputs=inputs)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_load.return_value = cluster
        mock_check.return_value = ''
        node.do_join = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_join(node)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node successfully joined cluster', res_msg)
        node.do_join.assert_called_once_with(action.context, 'FAKE_ID')
        mock_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 101, None, None, True)
        self.assertEqual(101, cluster.desired_capacity)
        cluster.store.assert_called_once_with(action.context)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_join_fail_size_check(self, mock_check, mock_load):
        node = mock.Mock()
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_JOIN',
                                        inputs=inputs)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_load.return_value = cluster
        mock_check.return_value = 'Size limits'
        node.do_join = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_join(node)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Size limits', res_msg)
        mock_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 101, None, None, True)
        self.assertEqual(0, node.do_join.call_count)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_join_failed_do_join(self, mock_check, mock_load):
        node = mock.Mock()
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_JOIN',
                                        inputs=inputs)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_load.return_value = cluster
        mock_check.return_value = ''
        node.do_join = mock.Mock(return_value=False)

        # Test failed node join path
        res_code, res_msg = action.do_join(node)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node failed in joining cluster', res_msg)
        mock_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 101, None, None, True)
        node.do_join.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_leave_success(self, mock_check, mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_ID'
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_LEAVE')
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_load.return_value = cluster
        mock_check.return_value = ''
        node.do_leave = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_leave(node)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node successfully left cluster', res_msg)
        node.do_leave.assert_called_once_with(action.context)
        mock_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 99, None, None, True)
        self.assertEqual(99, cluster.desired_capacity)
        cluster.store.assert_called_once_with(action.context)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_leave_failed_check(self, mock_check, mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_ID'
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_LEAVE')
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_load.return_value = cluster
        mock_check.return_value = 'Size limits'
        node.do_leave = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_leave(node)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Size limits', res_msg)
        mock_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 99, None, None, True)
        self.assertEqual(0, node.do_leave.call_count)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_leave_failed_do_leave(self, mock_check, mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_ID'
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_LEAVE')
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_load.return_value = cluster
        mock_check.return_value = ''
        node.do_leave = mock.Mock(return_value=False)

        # Test failed node join path
        res_code, res_msg = action.do_leave(node)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node failed in leaving cluster', res_msg)
        node.do_leave.assert_called_once_with(action.context)
        mock_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 99, None, None, True)

    def test__execute(self):
        node = mock.Mock()
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_SING')
        action.do_sing = mock.Mock(return_value=(action.RES_OK, 'GOOD'))

        res_code, res_msg = action._execute(node)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('GOOD', res_msg)
        action.do_sing.assert_called_once_with(node)

    @mock.patch.object(event_mod, 'error')
    def test__execute_bad_action(self, mock_error):
        node = mock.Mock()
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_DANCE')

        res_code, res_msg = action._execute(node)

        self.assertEqual(action.RES_ERROR, res_code)
        reason = 'Unsupported action: NODE_DANCE'
        self.assertEqual(reason, res_msg)
        mock_error.assert_called_once_with(node.id, action.action, 'Failed',
                                           reason)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(event_mod, 'error')
    def test_execute_node_not_found(self, mock_error, mock_load):
        action = node_action.NodeAction(self.ctx, 'ID', 'NODE_FLY')
        mock_load.side_effect = exception.NodeNotFound(node='ID')

        res_code, res_msg = action.execute()

        reason = 'Node with id (ID) is not found'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='ID')
        mock_error.assert_called_once_with('ID', action.action, 'Failed',
                                           reason)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lock, 'cluster_lock_acquire')
    def test_execute_failed_lock_cluster(self, mock_acquire, mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        action = node_action.NodeAction(self.ctx, 'NODE_ID', 'NODE_FLY',
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        mock_load.return_value = node
        mock_acquire.return_value = None

        res_code, res_msg = action.execute()

        reason = 'Failed in locking cluster'
        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE, False)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    def test_execute_failed_policy_check(self, mock_check, mock_release,
                                         mock_acquire, mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        action = node_action.NodeAction(self.ctx, 'NODE_ID', 'NODE_FLY',
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        action.data = {
            'status': policy_mod.CHECK_ERROR,
            'reason': 'Failed policy checking'
        }
        mock_load.return_value = node
        mock_acquire.return_value = action.id

        res_code, res_msg = action.execute()

        reason = 'Policy check: Failed policy checking'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')

    @mock.patch.object(node_mod.Node, 'load')
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
        action = node_action.NodeAction(self.ctx, 'NODE_ID', 'NODE_FLY',
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        action.data = {
            'status': policy_mod.CHECK_OK,
            'reason': 'Policy checking passed'
        }
        mock_load.return_value = node
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = None

        res_code, res_msg = action.execute()

        reason = 'Failed in locking node'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')
        mock_acquire_node.assert_called_once_with('NODE_ID', 'ACTION_ID',
                                                  False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lock, 'cluster_lock_acquire')
    @mock.patch.object(lock, 'cluster_lock_release')
    @mock.patch.object(base_action.Action, 'policy_check')
    @mock.patch.object(lock, 'node_lock_acquire')
    @mock.patch.object(lock, 'node_lock_release')
    def test_execute_success(self, mock_release_node, mock_acquire_node,
                             mock_check, mock_release, mock_acquire,
                             mock_load):
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        node.id = 'NODE_ID'
        action = node_action.NodeAction(self.ctx, 'NODE_ID', 'NODE_FLY',
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        # check result
        action.data = {
            'status': policy_mod.CHECK_OK,
            'reason': 'Policy checking passed'
        }
        self.patchobject(action, '_execute',
                         return_value=(action.RES_OK, 'Execution ok'))
        mock_load.return_value = node
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = 'ACTION_ID'

        res_code, res_msg = action.execute()

        reason = 'Execution ok'
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_acquire_node.assert_called_once_with('NODE_ID', 'ACTION_ID',
                                                  False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')
        check_calls = [
            mock.call('FAKE_CLUSTER', 'BEFORE'),
            mock.call('FAKE_CLUSTER', 'AFTER')
        ]
        mock_check.assert_has_calls(check_calls)

    @mock.patch.object(node_mod.Node, 'load')
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
        action = node_action.NodeAction(self.ctx, 'NODE_ID', 'NODE_FLY',
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        # check result
        action.data = {
            'status': policy_mod.CHECK_OK,
            'reason': 'Policy checking passed'
        }
        self.patchobject(action, '_execute',
                         return_value=(action.RES_ERROR, 'Execution Failed'))
        mock_load.return_value = node
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = 'ACTION_ID'

        res_code, res_msg = action.execute()

        reason = 'Execution Failed'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        mock_acquire_node.assert_called_once_with('NODE_ID', 'ACTION_ID',
                                                  False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')

    @mock.patch.object(node_mod.Node, 'load')
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
        action = node_action.NodeAction(self.ctx, 'NODE_ID', 'NODE_FLY',
                                        cause='RPC Request')
        action.id = 'ACTION_ID'
        mock_check = self.patchobject(action, 'policy_check',
                                      side_effect=fake_check)
        # check result
        self.patchobject(action, '_execute',
                         return_value=(action.RES_OK, 'Ignored'))
        mock_load.return_value = node
        mock_acquire.return_value = 'ACTION_ID'
        mock_acquire_node.return_value = 'ACTION_ID'

        res_code, res_msg = action.execute()

        reason = 'Policy check: Policy checking failed'
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_load.assert_called_once_with(action.context, node_id='NODE_ID')
        mock_acquire.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE, False)
        mock_release.assert_called_once_with('FAKE_CLUSTER', 'ACTION_ID',
                                             lock.NODE_SCOPE)
        check_calls = [
            mock.call('FAKE_CLUSTER', 'BEFORE'),
            mock.call('FAKE_CLUSTER', 'AFTER')
        ]
        mock_check.assert_has_calls(check_calls)
        mock_acquire_node.assert_called_once_with('NODE_ID', 'ACTION_ID',
                                                  False)
        mock_release_node.assert_called_once_with('NODE_ID', 'ACTION_ID')
