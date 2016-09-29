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
from senlin.engine.actions import base as ab
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.engine import dispatcher
from senlin.engine import event as EVENT
from senlin.engine import node as nm
from senlin.engine import scheduler
from senlin.engine import senlin_lock
from senlin.objects import action as ao
from senlin.objects import cluster as co
from senlin.objects import dependency as dobj
from senlin.objects import node as no
from senlin.policies import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterActionWaitTest(base.SenlinTestCase):
    scenarios = [
        ('wait_ready', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.READY
            ],
            cancelled=[False, False],
            timeout=[False, False],
            failed=[False, False],
            code=ab.Action.RES_OK,
            rescheduled_times=1,
            message='All dependents ended with success')
         ),
        ('wait_fail', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.FAILED
            ],
            cancelled=[False, False],
            timeout=[False, False],
            code=ab.Action.RES_ERROR,
            rescheduled_times=1,
            message='ACTION [FAKE_ID] failed')
         ),
        ('wait_wait_cancel', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.WAITING,
                ab.Action.WAITING,
            ],
            cancelled=[False, False, True],
            timeout=[False, False, False],
            code=ab.Action.RES_CANCEL,
            rescheduled_times=2,
            message='ACTION [FAKE_ID] cancelled')
         ),
        ('wait_wait_timeout', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.WAITING,
                ab.Action.WAITING,
            ],
            cancelled=[False, False, False],
            timeout=[False, False, True],
            code=ab.Action.RES_TIMEOUT,
            rescheduled_times=2,
            message='ACTION [FAKE_ID] timeout')
         ),

    ]

    def setUp(self):
        super(ClusterActionWaitTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(scheduler, 'reschedule')
    def test_wait_dependents(self, mock_reschedule, mock_load):
        action = ca.ClusterAction('ID', 'ACTION', self.ctx)
        action.id = 'FAKE_ID'
        self.patchobject(action, 'get_status', side_effect=self.statuses)
        self.patchobject(action, 'is_cancelled', side_effect=self.cancelled)
        self.patchobject(action, 'is_timeout', side_effect=self.timeout)

        res_code, res_msg = action._wait_for_dependents()
        self.assertEqual(self.code, res_code)
        self.assertEqual(self.message, res_msg)
        self.assertEqual(self.rescheduled_times, mock_reschedule.call_count)


@mock.patch.object(cm.Cluster, 'load')
class ClusterActionTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterActionTest, self).setUp()
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
                            domain='FAKE_DOMAIN')
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
        mock_node.assert_called_once_with('node-CLUSTER_-123',
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
        cluster = mock.Mock(id='01234567-123434')
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
            mock.call('node-01234567-123', mock.ANY, '01234567-123434',
                      user=mock.ANY, project=mock.ANY, domain=mock.ANY,
                      index=123, context=mock.ANY, metadata={},
                      data={'placement': {'region': 'regionOne'}}),
            mock.call('node-01234567-124', mock.ANY, '01234567-123434',
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
        cluster = mock.Mock(id='01234567-123434')
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
            action.context, action.CLUSTER_CREATE, created_at=mock.ANY)

    def test_do_create_failed_create_cluster(self, mock_load):
        cluster = mock.Mock(id='FAKE_CLUSTER', ERROR='ERROR')
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
        cluster = mock.Mock(id='FAKE_ID', ERROR='ERROR')
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
                action.context, action.CLUSTER_CREATE)
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
            action.context, action.CLUSTER_CREATE)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_update_multi(self, mock_wait, mock_start, mock_dep,
                             mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='fake id 1')
        node2 = mock.Mock(id='fake id 2')
        cluster = mock.Mock(id='FAKE_ID', nodes=[node1, node2],
                            ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}

        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']
        mock_wait.return_value = (action.RES_OK, 'OK')

        # do it
        res_code, res_msg = action.do_update()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)
        self.assertEqual(2, mock_action.call_count)
        self.assertEqual(1, mock_dep.call_count)
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_ACTION_2', {'status': 'READY'})
        ]
        mock_update.assert_has_calls(update_calls)

        mock_start.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_UPDATE, profile_id='FAKE_PROFILE',
            updated_at=mock.ANY)

    def test_do_update_not_profile(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', nodes=[], ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {}
        res_code, res_msg = action.do_update()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_UPDATE, updated_at=mock.ANY)

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
            action.context, action.CLUSTER_UPDATE, profile_id='FAKE_PROFILE',
            updated_at=mock.ANY)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_update_failed_wait(self, mock_wait, mock_start, mock_dep,
                                   mock_action, mock_update, mock_load):
        node = mock.Mock(id='fake node id')
        cluster = mock.Mock(id='FAKE_CLUSTER', nodes=[node], ACTIVE='ACTIVE')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}

        mock_action.return_value = 'NODE_ACTION'
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout')

        # do it
        res_code, res_msg = action.do_update()

        # assertions
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Failed in updating nodes.', res_msg)
        self.assertEqual(1, mock_action.call_count)
        self.assertEqual(1, mock_dep.call_count)
        mock_update.assert_called_once_with(action.context, 'NODE_ACTION',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_UPDATE)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_single(self, mock_wait, mock_start, mock_dep,
                                  mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='FAKE_CLUSTER', desired_capacity=100)

        # cluster action is real
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID', cause='Derived Action')
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        self.assertEqual(['NODE_ID'], action.outputs['nodes_removed'])
        cluster.remove_node.assert_called_once_with('NODE_ID')

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_multi(self, mock_wait, mock_start, mock_dep,
                                 mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100)
        mock_load.return_value = cluster

        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_1', 'NODE_2'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(2, mock_action.call_count)
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_ACTION_2', {'status': 'READY'})
        ]
        mock_update.assert_has_calls(update_calls)
        self.assertEqual(1, mock_dep.call_count)
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        self.assertEqual({'nodes_removed': ['NODE_1', 'NODE_2']},
                         action.outputs)
        cluster.remove_node.assert_has_calls([
            mock.call('NODE_1'), mock.call('NODE_2')])

    def test__delete_empty(self, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)

        # do it
        res_code, res_msg = action._delete_nodes([])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('', res_msg)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_pd(self, mock_wait, mock_start, mock_dep,
                                   mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100)
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'deletion': {
                'destroy_after_deletion': False
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'
        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_LEAVE',
            name='node_delete_NODE_ID', cause='Derived Action')

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_failed_wait(self, mock_wait, mock_start, mock_dep,
                                       mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='ID')
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {}
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Failed in deleting nodes.', res_msg)
        self.assertEqual({}, action.data)

    def test_do_delete_success(self, mock_load):
        node1 = mock.Mock(id='NODE_1')
        node2 = mock.Mock(id='NODE_2')
        cluster = mock.Mock(id='FAKE_CLUSTER', nodes=[node1, node2],
                            DELETING='DELETING')
        cluster.do_delete.return_value = True
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}

        mock_delete = self.patchobject(action, '_delete_nodes',
                                       return_value=(action.RES_OK, 'Good'))

        # do it
        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Good', res_msg)
        self.assertEqual({'deletion': {'destroy_after_deletion': True}},
                         action.data)
        cluster.set_status.assert_called_once_with(action.context, 'DELETING',
                                                   'Deletion in progress.')
        mock_delete.assert_called_once_with(['NODE_1', 'NODE_2'])
        cluster.do_delete.assert_called_once_with(action.context)

    def test_do_delete_failed_delete_nodes_timeout(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], ACTIVE='ACTIVE',
                            DELETING='DELETING', WARNING='WARNING')
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_TIMEOUT, 'Timeout!'))

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'DELETING', 'Deletion in progress.')
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_DELETE)

    def test_do_delete_failed_delete_nodes_with_error(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], ACTIVE='ACTIVE',
                            DELETING='DELETING', WARNING='WARNING')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_ERROR, 'Error!'))

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Error!', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'DELETING', 'Deletion in progress.')
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_DELETE)

    def test_do_delete_failed_delete_nodes_with_cancel(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], ACTIVE='ACTIVE',
                            DELETING='DELETING', WARNING='WARNING')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_CANCEL, 'Cancelled!'))

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_CANCEL, res_code)
        self.assertEqual('Cancelled!', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'DELETING', 'Deletion in progress.')
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_DELETE)

    def test_do_delete_failed_delete_nodes_with_retry(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], ACTIVE='ACTIVE',
                            DELETING='DELETING', WARNING='WARNING')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_RETRY, 'Busy!'))

        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual('Busy!', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'DELETING', 'Deletion in progress.')
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_DELETE)

    def test_do_delete_failed_delete_cluster(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}

        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_OK, 'Good'))
        # do it
        res_code, res_msg = action.do_delete()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Cannot delete cluster object.', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'DELETING', 'Deletion in progress.')
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_DELETE)

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
        cluster = mock.Mock(id='CLUSTER_ID')
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
            action.context, action.CLUSTER_ADD_NODES, desired_capacity=3)
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

        cluster = mock.Mock(id='CLUSTER_ID')
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
            action.context, action.CLUSTER_ADD_NODES, desired_capacity=4)
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
        cluster = mock.Mock(id='CLUSTER_ID')
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
            action.context, action.CLUSTER_REPLACE_NODES)

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

    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_del_nodes(self, mock_count, mock_delete, mock_get, mock_sleep,
                          mock_load):

        cluster = mock.Mock(id='FAKE_CLUSTER')
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
            action.context, action.CLUSTER_DEL_NODES, desired_capacity=0)

    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_del_nodes_with_deletion_policy(self, mock_count, mock_delete,
                                               mock_get, mock_sleep,
                                               mock_load):
        cid = 'FAKE_CLUSTER'
        cluster = mock.Mock(id=cid, desired_capacity=4)
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
            action.context, action.CLUSTER_DEL_NODES)

    @mock.patch.object(no.Node, 'get')
    def test_do_del_nodes_node_not_found(self, mock_get, mock_load):
        cluster = mock.Mock()
        mock_load.return_value = cluster
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  inputs={'candidates': ['NODE_1']})
        mock_get.return_value = None

        # do it
        res_code, res_msg = action.do_del_nodes()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node NODE_1 is not found.", res_msg)
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

        cluster = mock.Mock(id='FAKE_CLUSTER')
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
            action.context, action.CLUSTER_DEL_NODES, desired_capacity=2)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_check(self, mock_wait, mock_start, mock_dep, mock_action,
                      mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1')
        node2 = mock.Mock(id='NODE_2')
        cluster = mock.Mock(id='FAKE_ID', status='old status',
                            status_reason='old reason')
        cluster.nodes = [node1, node2]
        cluster.do_check.return_value = True
        mock_load.return_value = cluster
        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']

        action = ca.ClusterAction('FAKE_CLUSTER', 'CLUSTER_CHECK', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'

        mock_wait.return_value = (action.RES_OK, 'Everything is Okay')

        # do it
        res_code, res_msg = action.do_check()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster checking completed.', res_msg)

        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        cluster.do_check.assert_called_once_with(action.context)
        mock_action.assert_has_calls([
            mock.call(action.context, 'NODE_1', 'NODE_CHECK',
                      name='node_check_NODE_1',
                      cause=ab.CAUSE_DERIVED),
            mock.call(action.context, 'NODE_2', 'NODE_CHECK',
                      name='node_check_NODE_2',
                      cause=ab.CAUSE_DERIVED)
        ])
        mock_dep.assert_called_once_with(action.context,
                                         ['NODE_ACTION_1', 'NODE_ACTION_2'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_has_calls([
            mock.call(action.context, 'NODE_ACTION_1', {'status': 'READY'}),
            mock.call(action.context, 'NODE_ACTION_2', {'status': 'READY'}),
        ])
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_CHECK)

    def test_do_check_cluster_empty(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID', nodes=[], status='old status',
                            status_reason='old reason')
        cluster.do_check.return_value = True
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_CHECK', self.ctx)

        # do it
        res_code, res_msg = action.do_check()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster checking completed.', res_msg)
        cluster.do_check.assert_called_once_with(self.ctx)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_CHECK)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_check_failed_waiting(self, mock_wait, mock_start, mock_dep,
                                     mock_action, mock_update, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CLUSTER_ID', status='old status',
                            status_reason='old reason')
        cluster.do_recover.return_value = True
        cluster.nodes = [node]
        mock_load.return_value = cluster
        mock_action.return_value = 'NODE_ACTION_ID'

        action = ca.ClusterAction('FAKE_CLUSTER', 'CLUSTER_CHECK', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'

        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        res_code, res_msg = action.do_check()

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)

        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        cluster.do_check.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_CHECK',
            name='node_check_NODE_1',
            cause=ab.CAUSE_DERIVED,
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_CHECK)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover(self, mock_wait, mock_start, mock_dep, mock_action,
                        mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ACTIVE')
        node2 = mock.Mock(id='NODE_2', cluster_id='FAKE_ID', statu='ERROR')

        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING')
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
            cause=ab.CAUSE_DERIVED,
            inputs={}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover_with_data(self, mock_wait, mock_start, mock_dep,
                                  mock_action, mock_update, mock_load):
        node1 = mock.Mock(id='NODE_1', cluster_id='FAKE_ID', status='ERROR')
        cluster = mock.Mock(id='FAKE_ID', RECOVERING='RECOVERING')
        cluster.nodes = [node1]
        cluster.do_recover.return_value = True
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_RECOVER', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'health': {
                'recover_action': ['REBOOT'],
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
            cause=ab.CAUSE_DERIVED,
            inputs={'operation': ['REBOOT']}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_RECOVER_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_RECOVER_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RECOVER)

    def test_do_recover_all_nodes_active(self, mock_load):
        cluster = mock.Mock(id='FAKE_ID')
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
            action.context, action.CLUSTER_RECOVER)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test_do_recover_failed_waiting(self, mock_wait, mock_start, mock_dep,
                                       mock_action, mock_update, mock_load):
        node = mock.Mock(id='NODE_1', cluster_id='CID', status='ERROR')
        cluster = mock.Mock(id='CID')
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
            cause=ab.CAUSE_DERIVED,
            inputs={}
        )
        mock_dep.assert_called_once_with(action.context, ['NODE_ACTION_ID'],
                                         'CLUSTER_ACTION_ID')
        mock_update.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                            {'status': 'READY'})
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with()
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RECOVER)

    def test__update_cluster_size(self, mock_load):
        cluster = mock.Mock(id='CID', desired_capacity=10, nodes=[])
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_RESIZE', self.ctx,
                                  inputs={'min_size': 1, 'max_size': 20})

        action._update_cluster_size(15)

        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster resize started.',
            desired_capacity=15, min_size=1, max_size=20)

    def test__update_cluster_size_minimum(self, mock_load):
        cluster = mock.Mock(id='CID', desired_capacity=10, nodes=[])
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_RESIZE', self.ctx,
                                  inputs={})

        action._update_cluster_size(15)

        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster resize started.',
            desired_capacity=15)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test_do_resize_shrink(self, mock_delete, mock_sleep, mock_select,
                              mock_size, mock_count, mock_load):
        cluster = mock.Mock(id='CID', nodes=[], RESIZING='RESIZING')
        for n in range(10):
            node = mock.Mock(id='NODE-ID-%s' % (n + 1))
            cluster.nodes.append(node)
        mock_load.return_value = cluster
        mock_count.return_value = 10
        action = ca.ClusterAction(
            cluster.id, 'CLUSTER_RESIZE', self.ctx,
            data={
                'deletion': {
                    'count': 2,
                    'grace_period': 2,
                    'destroy_after_deletion': True
                }
            }
        )
        mock_delete.return_value = (action.RES_OK, 'All dependents completed.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster resize succeeded.', res_msg)

        mock_select.assert_called_once_with(cluster.nodes, 2)
        mock_size.assert_called_once_with(8)
        mock_sleep.assert_called_once_with(2)
        mock_delete.assert_called_once_with(mock_select.return_value)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(scaleutils, 'parse_resize_params')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test_do_resize_shrink_with_parsing(self, mock_delete, mock_parse,
                                           mock_sleep, mock_select, mock_size,
                                           mock_count, mock_load):

        def fake_parse(*args, **kwargs):
            # side effect
            action.data = {'deletion': {'count': 1}}
            return action.RES_OK, ''

        cluster = mock.Mock(id='CID', nodes=[], RESIZING='RESIZING')
        for n in range(10):
            node = mock.Mock(id='NODE-ID-%s' % (n + 1))
            cluster.nodes.append(node)
        mock_count.return_value = 10
        mock_load.return_value = cluster
        mock_parse.side_effect = fake_parse
        action = ca.ClusterAction(cluster.id, 'CLUSTER_RESIZE', self.ctx,
                                  inputs={'blah': 'blah'}, data={})
        mock_delete.return_value = (action.RES_OK, 'All dependents completed.')

        # deletion policy is attached to the action
        res_code, res_msg = action.do_resize()

        self.assertEqual({'deletion': {'count': 1}}, action.data)
        mock_parse.assert_called_once_with(action, cluster, 10)
        mock_select.assert_called_once_with(cluster.nodes, 1)
        mock_size.assert_called_once_with(9)
        mock_sleep.assert_called_once_with(0)
        mock_delete.assert_called_once_with(mock_select.return_value)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test_do_resize_shrink_failed_delete(self, mock_delete, mock_size,
                                            mock_count, mock_load):
        cluster = mock.Mock(id='CLID', nodes=[], RESIZING='RESIZING')
        mock_count.return_value = 3
        mock_load.return_value = cluster
        action = ca.ClusterAction(
            cluster.id, 'CLUSTER_RESIZE', self.ctx,
            data={
                'deletion': {
                    'count': 2,
                    'grace_period': 2,
                    'candidates': ['NODE1', 'NODE2']
                }
            }
        )
        mock_delete.return_value = (action.RES_ERROR, 'Bad things happened.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Bad things happened.', res_msg)

        mock_size.assert_called_once_with(1)
        mock_delete.assert_called_once_with(['NODE1', 'NODE2'])
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test_do_resize_grow(self, mock_create, mock_size, mock_count,
                            mock_load):
        cluster = mock.Mock(id='ID', nodes=[], RESIZING='RESIZING')
        mock_load.return_value = cluster
        mock_count.return_value = 10
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={'creation': {'count': 2}})

        mock_create.return_value = (action.RES_OK, 'All dependents completed.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster resize succeeded.', res_msg)

        mock_size.assert_called_once_with(12)
        mock_create.assert_called_once_with(2)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(scaleutils, 'parse_resize_params')
    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test_do_resize_grow_with_parsing(self, mock_create, mock_parse,
                                         mock_size, mock_count, mock_load):
        def fake_parse(*args, **kwargs):
            action.data = {'creation': {'count': 3}}
            return action.RES_OK, ''

        cluster = mock.Mock(id='ID', nodes=[], RESIZING='RESIZING')
        mock_load.return_value = cluster
        mock_count.return_value = 10
        mock_parse.side_effect = fake_parse
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'blah': 'blah'})
        mock_create.return_value = (action.RES_OK, 'All dependents completed.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster resize succeeded.', res_msg)

        mock_parse.assert_called_once_with(action, cluster, 10)
        mock_size.assert_called_once_with(13)
        mock_create.assert_called_once_with(3)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test_do_resize_grow_failed_create(self, mock_create, mock_size,
                                          mock_count, mock_load):
        cluster = mock.Mock(id='CLID', nodes=[], RESIZING='RESIZING')
        mock_load.return_value = cluster
        mock_count.return_value = 3
        action = ca.ClusterAction(
            cluster.id, 'CLUSTER_RESIZE', self.ctx,
            data={'creation': {'count': 2}})
        mock_create.return_value = (action.RES_ERROR, 'Bad things happened.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Bad things happened.', res_msg)

        mock_size.assert_called_once_with(5)
        mock_create.assert_called_once_with(2)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(scaleutils, 'parse_resize_params')
    def test_do_resize_failed_parsing(self, mock_parse, mock_count, mock_load):
        cluster = mock.Mock(RESIZING='RESIZING', nodes=[])
        mock_load.return_value = cluster
        mock_count.return_value = 8
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'blah': 'blah'})
        mock_parse.return_value = (action.RES_ERROR, 'Failed parsing')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failed parsing', res_msg)
        mock_parse.assert_called_once_with(action, cluster, 8)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_no_pd_no_inputs(self, mock_count, mock_create,
                                          mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={})
        mock_count.return_value = 5
        mock_create.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        mock_count.assert_called_once_with(action.context, 'CID')
        mock_create.assert_called_once_with(1)
        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster scale out started.',
            desired_capacity=6)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_SCALE_OUT)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_with_pd_no_inputs(self, mock_count, mock_create,
                                            mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={'creation': {'count': 3}}, inputs={})
        mock_count.return_value = 7
        mock_create.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # creating 3 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_create.assert_called_once_with(3)
        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster scale out started.',
            desired_capacity=10)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_SCALE_OUT)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_no_pd_with_inputs(self, mock_count, mock_create,
                                            mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 8
        mock_create.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # creating 2 nodes, given that the cluster is empty now
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_create.assert_called_once_with(2)
        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster scale out started.',
            desired_capacity=10)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_SCALE_OUT)

    def test_do_scale_out_count_negative(self, mock_load):
        cluster = mock.Mock(id='CID')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': -2})

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (-2) for scaling out.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    def test_do_scale_out_count_invalid(self, mock_load):
        cluster = mock.Mock(id='CID')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 'tt'})

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (tt) for scaling out.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_failed_checking(self, mock_count, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=4)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 3

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("The target capacity (5) is greater than the "
                         "cluster's max_size (4).", res_msg)
        mock_count.assert_called_once_with(action.context, 'CID')
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_failed_create_nodes(self, mock_count, mock_create,
                                              mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 4

        # Error cases
        for result in (action.RES_ERROR, action.RES_CANCEL,
                       action.RES_TIMEOUT):
            mock_create.return_value = result, 'Too hot to work!'

            # do it
            res_code, res_msg = action.do_scale_out()

            # assertions
            self.assertEqual(result, res_code)
            self.assertEqual('Too hot to work!', res_msg)

            cluster.set_status.assert_called_once_with(
                action.context, cluster.RESIZING, 'Cluster scale out started.',
                desired_capacity=6)
            cluster.set_status.reset_mock()
            cluster.eval_status.assert_called_once_with(
                action.context, action.CLUSTER_SCALE_OUT)
            cluster.eval_status.reset_mock()
            mock_create.assert_called_once_with(2)
            mock_create.reset_mock()

        # Timeout case
        mock_create.return_value = action.RES_RETRY, 'Not good time!'

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual('Not good time!', res_msg)
        self.assertEqual(1, cluster.set_status.call_count)
        self.assertEqual(1, cluster.eval_status.call_count)
        mock_create.assert_called_once_with(2)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_no_pd_no_inputs(self, mock_count, mock_delete,
                                         mock_select, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={})
        mock_count.return_value = 10
        mock_delete.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # deleting 1 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_delete.assert_called_once_with(mock.ANY)
        mock_select.assert_called_once_with(cluster.nodes, 1)
        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster scale in started.',
            desired_capacity=9)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_SCALE_IN)

    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_with_pd_no_input(self, mock_count, mock_delete,
                                          mock_sleep, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.data = {
            'deletion': {
                'count': 2,
                'grace_period': 2,
                'candidates': ['NODE_ID_3', 'NODE_ID_4']
            }
        }
        action.inputs = {}
        mock_count.return_value = 5
        mock_delete.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # deleting 2 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_delete.assert_called_once_with(mock.ANY)
        self.assertEqual(2, len(mock_delete.call_args[0][0]))
        self.assertIn('NODE_ID_3', mock_delete.call_args[0][0])
        self.assertIn('NODE_ID_4', mock_delete.call_args[0][0])
        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster scale in started.',
            desired_capacity=3)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_SCALE_IN)
        mock_sleep.assert_called_once_with(2)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_no_pd_with_input(self, mock_count, mock_delete,
                                          mock_select, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 3})
        mock_count.return_value = 11
        mock_delete.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # deleting 3 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_delete.assert_called_once_with(mock.ANY)
        mock_select.assert_called_once_with(cluster.nodes, 3)
        cluster.set_status.assert_called_once_with(
            action.context, cluster.RESIZING, 'Cluster scale in started.',
            desired_capacity=8)
        cluster.eval_status.assert_called_once_with(
            action.context, action.CLUSTER_SCALE_IN)

    def test_do_scale_in_negative_count(self, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': -3})

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (-3) for scaling in.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    def test_do_scale_in_invalid_count(self, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 'tt'})

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (tt) for scaling in.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_failed_check(self, mock_count, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 3})
        mock_count.return_value = 3

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        mock_count.assert_called_once_with(action.context, 'CID')
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("The target capacity (0) is less than the cluster's "
                         "min_size (1).", res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_failed_delete_nodes(self, mock_count, mock_delete,
                                             mock_select, mock_load):

        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 5

        # Error cases
        for result in (action.RES_ERROR, action.RES_CANCEL,
                       action.RES_TIMEOUT, action.RES_RETRY):
            mock_delete.return_value = result, 'Too cold to work!'
            # do it
            res_code, res_msg = action.do_scale_in()
            # assertions
            self.assertEqual(result, res_code)
            self.assertEqual('Too cold to work!', res_msg)
            cluster.set_status.assert_called_once_with(
                action.context, cluster.RESIZING, 'Cluster scale in started.',
                desired_capacity=3)
            cluster.eval_status.assert_called_once_with(
                action.context, action.CLUSTER_SCALE_IN)
            cluster.set_status.reset_mock()
            cluster.eval_status.reset_mock()
            mock_delete.assert_called_once_with(mock.ANY)
            mock_delete.reset_mock()

    def test_do_attach_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.policies = []
        cluster.attach_policy.return_value = True, 'OK'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {
            'policy_id': 'FAKE_POLICY',
            'FOO': 'BAR'
        }

        # do it
        res_code, res_msg = action.do_attach_policy()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('OK', res_msg)
        cluster.attach_policy.assert_called_once_with(
            action.context, 'FAKE_POLICY', {'FOO': 'BAR'})
        cluster.store.assert_called_once_with(action.context)

    def test_do_attach_policy_missing_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CLID'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {}

        # do it
        res_code, res_msg = action.do_attach_policy()
        # assertion
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy not specified.', res_msg)

    def test_do_detach_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.detach_policy.return_value = True, 'Success'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'policy_id': 'FAKE_POLICY'}

        # do it
        res_code, res_msg = action.do_detach_policy()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Success', res_msg)
        cluster.detach_policy.assert_called_once_with(action.context,
                                                      'FAKE_POLICY')
        cluster.store.assert_called_once_with(action.context)

    def test_do_detach_policy_missing_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CID'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {}

        # do it
        res_code, res_msg = action.do_detach_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy not specified.', res_msg)

    def test_do_detach_policy_failed(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.detach_policy.return_value = False, 'Failure.'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'policy_id': 'FAKE_POLICY'}

        # do it
        res_code, res_msg = action.do_detach_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failure.', res_msg)
        cluster.detach_policy.assert_called_once_with(action.context,
                                                      'FAKE_POLICY')

    def test_do_update_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.update_policy.return_value = True, 'Success.'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {
            'policy_id': 'FAKE_POLICY',
            'foo': 'bar',
        }

        # do it
        res_code, res_msg = action.do_update_policy()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Success.', res_msg)
        cluster.update_policy.assert_called_once_with(
            action.context, 'FAKE_POLICY', foo='bar')

    def test_do_update_policy_failed_update(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.update_policy.return_value = False, 'Something is wrong.'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {
            'policy_id': 'FAKE_POLICY',
            'foo': 'bar',
        }

        # do it
        res_code, res_msg = action.do_update_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Something is wrong.', res_msg)
        cluster.update_policy.assert_called_once_with(
            action.context, 'FAKE_POLICY', foo='bar')

    def test_do_update_policy_missing_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'enabled': True}

        # do it
        res_code, res_msg = action.do_update_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy not specified.', res_msg)

    @mock.patch.object(ab.Action, 'policy_check')
    def test__execute(self, mock_check, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_FLY', self.ctx)
        action.do_fly = mock.Mock(return_value=(action.RES_OK, 'Good!'))
        action.data = {
            'status': pb.CHECK_OK,
            'reason': 'Policy checking passed'
        }

        res_code, res_msg = action._execute()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Good!', res_msg)
        mock_check.assert_has_calls([
            mock.call('FAKE_CLUSTER', 'BEFORE'),
            mock.call('FAKE_CLUSTER', 'AFTER')])

    @mock.patch.object(EVENT, 'error')
    @mock.patch.object(ab.Action, 'policy_check')
    def test_execute_failed_policy_check(self, mock_check, mock_error,
                                         mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_FLY', self.ctx)
        action.do_fly = mock.Mock(return_value=(action.RES_OK, 'Good!'))
        action.data = {
            'status': pb.CHECK_ERROR,
            'reason': 'Something is wrong.'
        }

        res_code, res_msg = action._execute()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy check failure: Something is wrong.', res_msg)
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')
        mock_error.assert_called_once_with(
            action.context, cluster, 'CLUSTER_FLY', 'Failed',
            'Policy check failure: Something is wrong.')

    @mock.patch.object(EVENT, 'error')
    @mock.patch.object(ab.Action, 'policy_check')
    def test_execute_unsupported_action(self, mock_check, mock_error,
                                        mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DANCE', self.ctx)
        action.data = {
            'status': pb.CHECK_OK,
            'reason': 'All is going well.'
        }

        res_code, res_msg = action._execute()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Unsupported action: CLUSTER_DANCE.', res_msg)
        mock_check.assert_called_once_with('FAKE_CLUSTER', 'BEFORE')
        mock_error.assert_called_once_with(
            action.context, cluster, 'CLUSTER_DANCE', 'Failed',
            'Unsupported action: CLUSTER_DANCE.')

    @mock.patch.object(EVENT, 'error')
    def test_execute_post_check_failed(self, mock_error, mock_load):
        def fake_check(cluster_id, target):
            if target == 'BEFORE':
                action.data = {
                    'status': pb.CHECK_OK,
                    'reason': 'Policy checking passed.'
                }
            else:
                action.data = {
                    'status': pb.CHECK_ERROR,
                    'reason': 'Policy checking failed.'
                }

        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_FLY', self.ctx)
        action.do_fly = mock.Mock(return_value=(action.RES_OK, 'Cool!'))
        mock_check = self.patchobject(action, 'policy_check',
                                      side_effect=fake_check)

        res_code, res_msg = action._execute()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy check failure: Policy checking failed.',
                         res_msg)
        mock_check.assert_has_calls([
            mock.call('FAKE_CLUSTER', 'BEFORE'),
            mock.call('FAKE_CLUSTER', 'AFTER')])
        mock_error.assert_called_once_with(
            action.context, cluster, 'CLUSTER_FLY', 'Failed',
            'Policy check failure: Policy checking failed.')

    @mock.patch.object(senlin_lock, 'cluster_lock_acquire')
    @mock.patch.object(senlin_lock, 'cluster_lock_release')
    def test_execute(self, mock_release, mock_acquire, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_FLY', self.ctx)
        action.id = 'ACTION_ID'
        self.patchobject(action, '_execute',
                         return_value=(action.RES_OK, 'success'))
        mock_acquire.return_value = action

        res_code, res_msg = action.execute()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('success', res_msg)
        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        mock_acquire.assert_called_once_with(
            self.ctx, 'FAKE_CLUSTER', 'ACTION_ID', None,
            senlin_lock.CLUSTER_SCOPE, False)
        mock_release.assert_called_once_with(
            'FAKE_CLUSTER', 'ACTION_ID', senlin_lock.CLUSTER_SCOPE)

    @mock.patch.object(senlin_lock, 'cluster_lock_acquire')
    def test_execute_failed_locking(self, mock_acquire, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        mock_acquire.return_value = None

        res_code, res_msg = action.execute()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failed in locking cluster.', res_msg)
        mock_load.assert_called_once_with(action.context, cluster.id)

    @mock.patch.object(senlin_lock, 'cluster_lock_acquire')
    @mock.patch.object(senlin_lock, 'cluster_lock_release')
    def test_execute_failed_execute(self, mock_release, mock_acquire,
                                    mock_load):
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'ACTION_ID'
        mock_acquire.return_value = action
        self.patchobject(action, '_execute',
                         return_value=(action.RES_ERROR, 'Failed execution.'))

        res_code, res_msg = action.execute()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failed execution.', res_msg)
        mock_load.assert_called_once_with(action.context, cluster.id)
        mock_acquire.assert_called_once_with(
            self.ctx, 'CLUSTER_ID', 'ACTION_ID', None,
            senlin_lock.CLUSTER_SCOPE, True)
        mock_release.assert_called_once_with(
            'CLUSTER_ID', 'ACTION_ID', senlin_lock.CLUSTER_SCOPE)

    def test_cancel(self, mock_load):
        action = ca.ClusterAction('ID', 'CLUSTER_DELETE', self.ctx)
        res = action.cancel()
        self.assertEqual(action.RES_OK, res)
