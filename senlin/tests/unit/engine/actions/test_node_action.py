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

from senlin.common import scaleutils
from senlin.engine.actions import base as base_action
from senlin.engine.actions import node_action
from senlin.engine import cluster as cluster_mod
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.engine import senlin_lock as lock
from senlin.policies import base as policy_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(node_mod.Node, 'load')
class NodeActionTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_do_create(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        node.do_create = mock.Mock(return_value=None)
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)

        # Test node creation failure path
        res_code, res_msg = action.do_create()
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node creation failed.', res_msg)
        node.do_create.assert_called_once_with(action.context)
        node.reset_mock()

        # Test node creation success path
        node.do_create = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_create()
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node created successfully.', res_msg)
        node.do_create.assert_called_once_with(action.context)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_create_with_cluster_id_specified(self, mock_c_load,
                                                 mock_check, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CID'
        cluster.desired_capacity = 0
        mock_c_load.return_value = cluster
        node = mock.Mock()
        node.id = 'NID'
        node.do_create = mock.Mock(return_value=None)
        node.cluster_id = cluster.id
        mock_load.return_value = node
        mock_check.return_value = None
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=base_action.CAUSE_RPC)

        node.do_create = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_create()
        self.assertEqual(action.RES_OK, res_code)
        mock_check.assert_called_once_with(cluster, 1, None, None, True)
        mock_c_load.assert_called_once_with(action.context, 'CID')
        cluster.store.assert_called_once_with(action.context)
        self.assertEqual(1, cluster.desired_capacity)
        cluster.add_node.assert_called_once_with(node)

    def test_do_check(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)

        # Test node check failure path
        node.do_check = mock.Mock(return_value=False)
        res_code, res_msg = action.do_check()
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node status is not ACTIVE.', res_msg)
        node.do_check.assert_called_once_with(action.context)
        node.reset_mock()

        # Test node check success path
        node.do_check = mock.Mock(return_value=True)
        res_code, res_msg = action.do_check()
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node status is ACTIVE.', res_msg)
        node.do_check.assert_called_once_with(action.context)

    def test_do_delete(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        node.do_delete = mock.Mock(return_value=None)
        mock_load.return_value = node
        action = node_action.NodeAction('ID', 'ACTION', self.ctx)

        # Test failed node deletion path
        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node deletion failed.', res_msg)
        node.do_delete.assert_called_once_with(action.context)
        node.reset_mock()

        # Test node deletion success path
        node.do_delete = mock.Mock(return_value=mock.Mock())
        res_code, res_msg = action.do_delete()
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node deleted successfully.', res_msg)
        node.do_delete.assert_called_once_with(action.context)

    @mock.patch.object(scaleutils, 'check_size_params')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_do_delete_with_cluster_id_specified(self, mock_c_load,
                                                 mock_check, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CID'
        cluster.desired_capacity = 1
        mock_c_load.return_value = cluster
        node = mock.Mock()
        node.id = 'NID'
        node.do_delete = mock.Mock(return_value=None)
        node.cluster_id = cluster.id
        mock_load.return_value = node
        mock_check.return_value = None
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx,
                                        cause=base_action.CAUSE_RPC)

        node.do_delete = mock.Mock(return_value=mock.Mock())

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_OK, res_code)
        mock_check.assert_called_once_with(cluster, 0, None, None, True)
        mock_c_load.assert_called_once_with(action.context, 'CID')
        cluster.store.assert_called_once_with(action.context)
        self.assertEqual(0, cluster.desired_capacity)
        cluster.remove_node.assert_called_once_with(node.id)

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

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_join_success(self, mock_check, mock_c_load, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(node.id, 'NODE_JOIN', self.ctx,
                                        inputs=inputs)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_c_load.return_value = cluster
        mock_check.return_value = None
        node.do_join = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_join()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node successfully joined cluster.', res_msg)
        node.do_join.assert_called_once_with(action.context, 'FAKE_ID')
        mock_c_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 101, None, None, True)
        cluster.add_node.assert_called_once_with(node)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_join_fail_size_check(self, mock_check, mock_c_load, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(node.id, 'NODE_JOIN', self.ctx,
                                        inputs=inputs)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_c_load.return_value = cluster
        mock_check.return_value = 'Size limits'
        node.do_join = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_join()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Size limits', res_msg)
        mock_c_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 101, None, None, True)
        self.assertEqual(0, node.do_join.call_count)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_join_failed_do_join(self, mock_check, mock_c_load, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        inputs = {"cluster_id": "FAKE_ID"}
        action = node_action.NodeAction(node.id, 'NODE_JOIN', self.ctx,
                                        inputs=inputs)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_c_load.return_value = cluster
        mock_check.return_value = None
        node.do_join = mock.Mock(return_value=False)

        # Test failed node join path
        res_code, res_msg = action.do_join()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node failed in joining cluster.', res_msg)
        mock_c_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 101, None, None, True)
        node.do_join.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_leave_success(self, mock_check, mock_c_load, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        node.cluster_id = 'FAKE_ID'
        action = node_action.NodeAction(node.id, 'NODE_LEAVE', self.ctx)
        cluster = mock.Mock()
        cluster.id = 'FAKE_ID'
        cluster.desired_capacity = 100
        mock_c_load.return_value = cluster
        mock_check.return_value = None
        node.do_leave = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_leave()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node successfully left cluster.', res_msg)
        node.do_leave.assert_called_once_with(action.context)
        mock_c_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 99, None, None, True)
        cluster.remove_node.assert_called_once_with('NID')

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_leave_failed_check(self, mock_check, mock_c_load, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        node.cluster_id = 'FAKE_ID'
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'NODE_LEAVE', self.ctx)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_c_load.return_value = cluster
        mock_check.return_value = 'Size limits'
        node.do_leave = mock.Mock(return_value=True)

        # Test failed node join path
        res_code, res_msg = action.do_leave()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Size limits', res_msg)
        mock_c_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 99, None, None, True)
        self.assertEqual(0, node.do_leave.call_count)

    def test_do_recover(self, mock_load):
        node = mock.Mock()
        node.id = 'NID'
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'ACTION', self.ctx)

        # Test node recover failure path
        node.do_recover = mock.Mock(return_value=False)
        res_code, res_msg = action.do_recover()
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node recover failed.', res_msg)
        node.do_recover.assert_called_once_with(action.context)
        node.reset_mock()

        # Test node recover success path
        node.do_recover = mock.Mock(return_value=True)
        res_code, res_msg = action.do_recover()
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Node recovered successfully.', res_msg)
        node.do_recover.assert_called_once_with(action.context)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    @mock.patch.object(scaleutils, 'check_size_params')
    def test_do_leave_failed_do_leave(self, mock_check, mock_c_load,
                                      mock_load):
        node = mock.Mock()
        node.id = 'NID'
        node.cluster_id = 'FAKE_ID'
        mock_load.return_value = node
        action = node_action.NodeAction(node.id, 'NODE_LEAVE', self.ctx)
        cluster = mock.Mock()
        cluster.desired_capacity = 100
        mock_c_load.return_value = cluster
        mock_check.return_value = None
        node.do_leave = mock.Mock(return_value=False)

        # Test failed node join path
        res_code, res_msg = action.do_leave()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Node failed in leaving cluster.', res_msg)
        node.do_leave.assert_called_once_with(action.context)
        mock_c_load.assert_called_once_with(action.context, 'FAKE_ID')
        mock_check.assert_called_once_with(cluster, 99, None, None, True)

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
        mock_error.assert_called_once_with(action.context, node,
                                           action.action, 'Failed',
                                           reason)

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
        self.assertEqual(action.RES_ERROR, res_code)
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
            node.cluster_id = None
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
