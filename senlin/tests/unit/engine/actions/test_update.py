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
class ClusterUpdateTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterUpdateTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ca.ClusterAction, '_update_nodes')
    def test_do_update_multi(self, mock_update, mock_load):
        node1 = mock.Mock(id='fake id 1')
        node2 = mock.Mock(id='fake id 2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'name': 'FAKE_NAME',
                         'metadata': {'foo': 'bar'},
                         'timeout': 3600,
                         'new_profile_id': 'FAKE_PROFILE'}
        reason = 'Cluster update completed.'
        mock_update.return_value = (action.RES_OK, reason)
        # do it
        res_code, res_msg = action.do_update()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual(reason, res_msg)
        mock_update.assert_called_once_with('FAKE_PROFILE',
                                            [node1, node2])

    @mock.patch.object(ca.ClusterAction, '_update_nodes')
    def test_do_update_set_status_failed(self, mock_update, mock_load):
        node1 = mock.Mock(id='fake id 1')
        node2 = mock.Mock(id='fake id 2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)

        cluster.do_update.return_value = False
        reason = 'Cluster update failed.'
        # do it
        res_code, res_msg = action.do_update()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        self.assertEqual(0, mock_update.call_count)

    @mock.patch.object(ca.ClusterAction, '_update_nodes')
    def test_do_update_multi_failed(self, mock_update, mock_load):
        node1 = mock.Mock(id='fake id 1')
        node2 = mock.Mock(id='fake id 2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}
        reason = 'Failed in updating nodes.'
        mock_update.return_value = (action.RES_ERROR, reason)
        # do it
        res_code, res_msg = action.do_update()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual(reason, res_msg)
        mock_update.assert_called_once_with('FAKE_PROFILE',
                                            [node1, node2])

    def test_do_update_not_profile(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', nodes=[], ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {}
        res_code, res_msg = action.do_update()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_UPDATE, updated_at=mock.ANY)

    def test_do_update_profile_only(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', nodes=[], ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'name': 'FAKE_NAME',
                         'metadata': {'foo': 'bar'},
                         'timeout': 3600,
                         'new_profile_id': 'FAKE_PROFILE',
                         'profile_only': True}
        res_code, res_msg = action.do_update()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_UPDATE, profile_id='FAKE_PROFILE',
            updated_at=mock.ANY)

    def test_do_update_empty_cluster(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', nodes=[], ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}

        # do it
        res_code, res_msg = action.do_update()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)
        self.assertEqual('FAKE_PROFILE', cluster.profile_id)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_UPDATE, profile_id='FAKE_PROFILE',
            updated_at=mock.ANY)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__update_nodes_no_policy(self, mock_wait, mock_start, mock_dep,
                                     mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='node_id1')
        node2 = mock.Mock(id='node_id2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.side_effect = ['NODE_ACTION1', 'NODE_ACTION2']

        res_code, reason = action._update_nodes('FAKE_PROFILE',
                                                [node1, node2])
        self.assertEqual(res_code, action.RES_OK)
        self.assertEqual(reason, 'Cluster update completed.')
        self.assertEqual(2, mock_action.call_count)
        self.assertEqual(1, mock_dep.call_count)
        self.assertEqual(2, mock_update.call_count)
        mock_start.assert_called_once_with()

        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_UPDATE, profile_id='FAKE_PROFILE',
            updated_at=mock.ANY)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__update_nodes_batch_policy(self, mock_wait, mock_start, mock_dep,
                                        mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='node_id1')
        node2 = mock.Mock(id='node_id2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'update': {
                'pause_time': 0.1,
                'min_in_service': 1,
                'plan': [{node1.id}, {node2.id}],
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.side_effect = ['NODE_ACTION1', 'NODE_ACTION2']

        res_code, reason = action._update_nodes('FAKE_PROFILE',
                                                [node1, node2])
        self.assertEqual(res_code, action.RES_OK)
        self.assertEqual(reason, 'Cluster update completed.')
        self.assertEqual(2, mock_action.call_count)
        self.assertEqual(2, mock_dep.call_count)
        self.assertEqual(2, mock_update.call_count)
        self.assertEqual(2, mock_start.call_count)

        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_UPDATE, profile_id='FAKE_PROFILE',
            updated_at=mock.ANY)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__update_nodes_fail_wait(self, mock_wait, mock_start, mock_dep,
                                     mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='node_id1')
        node2 = mock.Mock(id='node_id2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_ERROR, 'Oops!')
        mock_action.side_effect = ['NODE_ACTION1', 'NODE_ACTION2']

        res_code, reason = action._update_nodes('FAKE_PROFILE',
                                                [node1, node2])
        self.assertEqual(res_code, action.RES_ERROR)
        self.assertEqual(reason, 'Failed in updating nodes.')
        self.assertEqual(2, mock_action.call_count)
        self.assertEqual(1, mock_dep.call_count)
        self.assertEqual(2, mock_update.call_count)
        mock_start.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_UPDATE)
