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
from senlin.objects import cluster as co
from senlin.objects import dependency as dobj
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterCreateTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterCreateTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(co.Cluster, 'get_next_index')
    @mock.patch.object(nm, 'Node')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__create_nodes_single(self, mock_wait, mock_start, mock_dep,
                                  mock_node, mock_index, mock_action,
                                  mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', profile_id='FAKE_PROFILE',
                            user='FAKE_USER', project='FAKE_PROJECT',
                            domain='FAKE_DOMAIN',
                            config={"node.name.format": "node-$3I"})
        mock_index.return_value = 123
        node = mock.Mock(id='NODE_ID')
        mock_node.return_value = node

        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # node_action is faked
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._create_nodes(1)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_index.assert_called_once_with(action.context, 'CLUSTER_ID')
        mock_node.assert_called_once_with('node-123',
                                          'FAKE_PROFILE',
                                          'CLUSTER_ID',
                                          context=action.context,
                                          user='FAKE_USER',
                                          project='FAKE_PROJECT',
                                          domain='FAKE_DOMAIN',
                                          index=123, metadata={})
        node.store.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(action.context, 'NODE_ID',
                                            'NODE_CREATE',
                                            name='node_create_NODE_ID',
                                            cause='Derived Action')
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(
            action.context, 'NODE_ACTION_ID',
            {'status': ab.Action.READY})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        self.assertEqual({'nodes_added': ['NODE_ID']}, action.outputs)

    @mock.patch.object(co.Cluster, 'get')
    def test_create_nodes_zero(self, mock_get, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_get.return_value = mock.Mock()
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)

        res_code, res_msg = action._create_nodes(0)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('', res_msg)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(co.Cluster, 'get_next_index')
    @mock.patch.object(nm, 'Node')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__create_nodes_multiple(self, mock_wait, mock_start, mock_dep,
                                    mock_node, mock_index, mock_action,
                                    mock_update, mock_load):
        cluster = mock.Mock(id='01234567-123434',
                            config={"node.name.format": "node-$3I"})
        node1 = mock.Mock(id='01234567-abcdef',
                          data={'placement': {'region': 'regionOne'}})
        node2 = mock.Mock(id='abcdefab-123456',
                          data={'placement': {'region': 'regionTwo'}})
        mock_node.side_effect = [node1, node2]
        mock_index.side_effect = [123, 124]

        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'placement': {
                'count': 2,
                'placements': [
                    {'region': 'regionOne'},
                    {'region': 'regionTwo'}
                ]
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # node_action is faked
        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']

        # do it
        res_code, res_msg = action._create_nodes(2)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(2, mock_index.call_count)
        self.assertEqual(2, mock_node.call_count)
        node1.store.assert_called_once_with(action.context)
        node2.store.assert_called_once_with(action.context)
        self.assertEqual(2, mock_action.call_count)
        self.assertEqual(1, mock_dep.call_count)

        update_calls = [
            mock.call(action.context, 'NODE_ACTION_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_ACTION_2', {'status': 'READY'})
        ]
        mock_update.assert_has_calls(update_calls)
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        self.assertEqual({'nodes_added': [node1.id, node2.id]}, action.outputs)
        self.assertEqual({'region': 'regionOne'}, node1.data['placement'])
        self.assertEqual({'region': 'regionTwo'}, node2.data['placement'])
        mock_node_calls = [
            mock.call('node-123', mock.ANY, '01234567-123434',
                      user=mock.ANY, project=mock.ANY, domain=mock.ANY,
                      index=123, context=mock.ANY, metadata={},
                      data={'placement': {'region': 'regionOne'}}),
            mock.call('node-124', mock.ANY, '01234567-123434',
                      user=mock.ANY, project=mock.ANY, domain=mock.ANY,
                      index=124, context=mock.ANY, metadata={},
                      data={'placement': {'region': 'regionTwo'}})
        ]

        mock_node.assert_has_calls(mock_node_calls)
        cluster.add_node.assert_has_calls([
            mock.call(node1), mock.call(node2)])

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(co.Cluster, 'get')
    @mock.patch.object(nm, 'Node')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__create_nodes_multiple_failed_wait(self, mock_wait, mock_start,
                                                mock_dep, mock_node, mock_get,
                                                mock_update, mock_load):
        cluster = mock.Mock(id='01234567-123434', config={})
        db_cluster = mock.Mock(next_index=1)
        mock_get.return_value = db_cluster
        node1 = mock.Mock(id='01234567-abcdef', data={})
        node2 = mock.Mock(id='abcdefab-123456', data={})
        mock_node.side_effect = [node1, node2]

        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'placement': {
                'count': 2,
                'placements': [
                    {'region': 'regionOne'},
                    {'region': 'regionTwo'}
                ]
            }
        }
        mock_wait.return_value = (action.RES_ERROR, 'Waiting timed out')

        # node_action is faked
        n_action_1 = mock.Mock()
        n_action_2 = mock.Mock()
        self.patchobject(ab, 'Action', side_effect=[n_action_1, n_action_2])

        # do it
        res_code, res_msg = action._create_nodes(2)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failed in creating nodes.', res_msg)

    def test_do_create_success(self, mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER', ACTIVE='ACTIVE')
        cluster.do_create.return_value = True
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)

        x_create_nodes = self.patchobject(action, '_create_nodes',
                                          return_value=(action.RES_OK, 'OK'))
        # do it
        res_code, res_msg = action.do_create()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster creation succeeded.', res_msg)
        x_create_nodes.assert_called_once_with(cluster.desired_capacity)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_CREATE, created_at=mock.ANY)

    def test_do_create_failed_create_cluster(self, mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER')
        cluster.do_create.return_value = False
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)

        # do it
        res_code, res_msg = action.do_create()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Cluster creation failed.', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'ERROR', 'Cluster creation failed.')

    def test_do_create_failed_create_nodes(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID',)
        cluster.do_create.return_value = True
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)

        # do it
        for code in [action.RES_CANCEL, action.RES_TIMEOUT, action.RES_ERROR]:
            self.patchobject(action, '_create_nodes',
                             return_value=(code, 'Really Bad'))

            res_code, res_msg = action.do_create()

            self.assertEqual(code, res_code)
            self.assertEqual('Really Bad', res_msg)
            cluster.eval_status.assert_called_once_with(
                action.context, consts.CLUSTER_CREATE)
            cluster.eval_status.reset_mock()

    def test_do_create_failed_for_retry(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', INIT='INIT')
        cluster.do_create.return_value = True
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        self.patchobject(action, '_create_nodes',
                         return_value=(action.RES_RETRY, 'retry'))

        # do it
        res_code, res_msg = action.do_create()

        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual('retry', res_msg)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_CREATE)
