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
from senlin.common import scaleutils as su
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
class ClusterRecoverTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterRecoverTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover(self, mock_wait, mock_start, mock_dep,
                        mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', status='ERROR')

        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING',
                            desired_capacity=2)
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster
        cluster.nodes = [node1, node2]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {}

        mock_action.return_value = 'NODE_RECOVER_ID'
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_recover()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)

        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_2', 'NODE_RECOVER',
            name='node_recover_NODE_2',
            cause=consts.CAUSE_DERIVED,
            inputs={}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover_with_data(self, mock_wait, mock_start,
                                  mock_dep, mock_action, mock_update,
                                  mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ERROR')
        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING',
                            desired_capacity=2)
        cluster.nodes = [node1]
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'health': {
                'recover_action': [{'name': 'REBOOT', 'params': None}],
                'fencing': ['COMPUTE'],
            }
        }

        mock_action.return_value = 'NODE_RECOVER_ID'
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_recover()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)

        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_RECOVER',
            name='node_recover_NODE_1',
            cause=consts.CAUSE_DERIVED,
            inputs={
                'operation': [{'name': 'REBOOT', 'params': None}],
                'params': {'fence_compute': True}
            }
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    @mock.patch.object(ca.ClusterAction, '_check_capacity')
    def test_do_recover_with_input(self, mock_check, mock_wait, mock_start,
                                   mock_dep, mock_action, mock_update,
                                   mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ERROR')
        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING',
                            desired_capacity=2)
        cluster.nodes = [node1]
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {
            'operation': consts.RECOVER_REBOOT,
            'check': False,
            'check_capacity': True
        }

        mock_action.return_value = 'NODE_RECOVER_ID'
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_recover()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)

        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_RECOVER',
            name='node_recover_NODE_1',
            cause=consts.CAUSE_DERIVED,
            inputs={
                'operation': consts.RECOVER_REBOOT
            }
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)
        mock_check.assert_called_once_with()

    def test_do_recover_all_nodes_active(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', desired_capacity=2)
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', status='ACTIVE')
        cluster.nodes = [node1, node2]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)

        # do it
        res_code, res_msg = action.do_recover()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)
        cluster.do_recover.assert_called_once_with(self.ctx)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    @mock.patch.object(ca.ClusterAction, '_check_capacity')
    def test_do_recover_failed_waiting(self, mock_check, mock_wait,
                                       mock_start, mock_dep, mock_action,
                                       mock_update, mock_load):
        node = mock.Mock(id='NODE_1', cluster_id='CID', status='ERROR')
        cluster = mock.Mock(id='CID', desired_capacity=2)
        cluster.do_recover.return_value = True
        cluster.nodes = [node]
        mock_load.return_value = cluster
        mock_action.return_value = 'NODE_ACTION_ID'

        action = ca.ClusterAction('FAKE_CLUSTER', 'CLUSTER_REOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'

        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        res_code, res_msg = action.do_recover()

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)

        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_RECOVER',
            name='node_recover_NODE_1',
            cause=consts.CAUSE_DERIVED,
            inputs={}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)
        self.assertFalse(mock_check.called)

    @mock.patch.object(ca.ClusterAction, '_check_capacity')
    @mock.patch.object(nm.Node, 'load')
    def test_do_recover_with_check_active(self, mock_node, mock_desired,
                                          mock_load):
        cluster = mock.Mock(id='FAKE_ID', desired_capacity=2)
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', status='ERROR')
        cluster.nodes = [node1, node2]

        eng_node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID',
                              status='ACTIVE')
        eng_node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID',
                              status='ERROR')
        mock_node.side_effect = [eng_node1, eng_node2]

        def set_status(*args, **kwargs):
            eng_node2.status = 'ACTIVE'

        mock_check = self.patchobject(nm.Node, 'do_check')
        mock_check.side_effect = set_status
        eng_node2.do_check = mock_check

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.inputs = {'check': True}

        # do it
        res_code, res_msg = action.do_recover()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)
        node_calls = [
            mock.call(self.ctx, node_id='NODE_1'),
            mock.call(self.ctx, node_id='NODE_2')
        ]
        mock_node.assert_has_calls(node_calls)
        eng_node1.do_check.assert_called_once_with(self.ctx)
        eng_node2.do_check.assert_called_once_with(self.ctx)
        cluster.do_recover.assert_called_once_with(self.ctx)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)
        self.assertFalse(mock_desired.called)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    @mock.patch.object(ca.ClusterAction, '_check_capacity')
    @mock.patch.object(nm.Node, 'load')
    def test_do_recover_with_check_error(self, mock_node, mock_desired,
                                         mock_wait, mock_start, mock_dep,
                                         mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', status='ACTIVE')

        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING',
                            desired_capacity=2)
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster
        cluster.nodes = [node1, node2]

        eng_node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID',
                              status='ACTIVE')
        eng_node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID',
                              status='ACTIVE')
        mock_node.side_effect = [eng_node1, eng_node2]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'check': True,
                         'check_capacity': True}

        mock_action.return_value = 'NODE_RECOVER_ID'
        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        def set_status(*args, **kwargs):
            eng_node2.status = 'ERROR'

        mock_check = self.patchobject(nm.Node, 'do_check')
        mock_check.side_effect = set_status
        eng_node2.do_check = mock_check

        # do it
        res_code, res_msg = action.do_recover()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster recovery succeeded.', res_msg)

        cluster.do_recover.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_2', 'NODE_RECOVER',
            name='node_recover_NODE_2',
            cause=consts.CAUSE_DERIVED,
            inputs={}
        )
        node_calls = [
            mock.call(self.ctx, node_id='NODE_1'),
            mock.call(self.ctx, node_id='NODE_2')
        ]
        mock_node.assert_has_calls(node_calls)
        eng_node1.do_check.assert_called_once_with(self.ctx)
        eng_node2.do_check.assert_called_once_with(self.ctx)
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RECOVER)
        mock_desired.assert_called_once_with()

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test__check_capacity_create(self, mock_create, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')

        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING',
                            desired_capacity=2)
        mock_load.return_value = cluster
        cluster.nodes = [node1]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)

        action._check_capacity()

        mock_create.assert_called_once_with(1)

    @mock.patch.object(su, 'nodes_by_random')
    @mock.patch.object(no.Node, 'get_all_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test__check_capacity_delete(self, mock_delete, mock_get,
                                    mock_su, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', status='ERROR')

        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING',
                            desired_capacity=1)
        mock_load.return_value = cluster
        cluster.nodes = [node1, node2]
        mock_get.return_value = [node1, node2]
        mock_su.return_value = [node2.id]

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)

        action._check_capacity()

        mock_get.assert_called_once_with(action.context, cluster.id)
        mock_su.assert_called_once_with([node1, node2], 1)
        mock_delete.assert_called_once_with(['NODE_2'])
