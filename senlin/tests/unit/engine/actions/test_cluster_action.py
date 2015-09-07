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
from senlin.db.sqlalchemy import api as db_api
from senlin.engine.actions import base as base_action
from senlin.engine.actions import cluster_action
from senlin.engine import dispatcher
from senlin.engine import node as node_mod
from senlin.engine import scheduler
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterActionWaitTest(base.SenlinTestCase):
    scenarios = [
        ('wait_ready', dict(
            statuses=[
                base_action.Action.WAITING,
                base_action.Action.READY
            ],
            cancelled=[False, False],
            timeout=[False, False],
            failed=[False, False],
            code=base_action.Action.RES_OK,
            rescheduled_times=1,
            message='All dependents ended with success')
         ),
        ('wait_fail', dict(
            statuses=[
                base_action.Action.WAITING,
                base_action.Action.FAILED
            ],
            cancelled=[False, False],
            timeout=[False, False],
            code=base_action.Action.RES_ERROR,
            rescheduled_times=1,
            message='ACTION [FAKE_ID] failed')
         ),
        ('wait_wait_cancel', dict(
            statuses=[
                base_action.Action.WAITING,
                base_action.Action.WAITING,
                base_action.Action.WAITING,
            ],
            cancelled=[False, False, True],
            timeout=[False, False, False],
            code=base_action.Action.RES_CANCEL,
            rescheduled_times=2,
            message='ACTION [FAKE_ID] cancelled')
         ),
        ('wait_wait_timeout', dict(
            statuses=[
                base_action.Action.WAITING,
                base_action.Action.WAITING,
                base_action.Action.WAITING,
            ],
            cancelled=[False, False, False],
            timeout=[False, False, True],
            code=base_action.Action.RES_TIMEOUT,
            rescheduled_times=2,
            message='ACTION [FAKE_ID] timeout')
         ),

    ]

    def setUp(self):
        super(ClusterActionWaitTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(scheduler, 'reschedule')
    def test_wait_dependents(self, mock_reschedule):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'ACTION')
        action.id = 'FAKE_ID'
        self.patchobject(action, 'get_status', side_effect=self.statuses)
        self.patchobject(action, 'is_cancelled', side_effect=self.cancelled)
        self.patchobject(action, 'is_timeout', side_effect=self.timeout)

        res_code, res_msg = action._wait_for_dependents()
        self.assertEqual(self.code, res_code)
        self.assertEqual(self.message, res_msg)
        self.assertEqual(self.rescheduled_times, mock_reschedule.call_count)


class ClusterActionTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(db_api, 'cluster_get')
    @mock.patch.object(node_mod, 'Node')
    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__create_nodes_single(self, mock_wait, mock_start, mock_dep,
                                  mock_node, mock_get):
        # prepare mocks
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        cluster.profile_id = 'FAKE_PROFILE'
        cluster.user = 'FAKE_USER'
        cluster.project = 'FAKE_PROJECT'
        cluster.domain = 'FAKE_DOMAIN'
        db_cluster = mock.Mock()
        db_cluster.next_index = 1
        mock_get.return_value = db_cluster
        node = mock.Mock()
        node.id = 'NODE_ID'
        mock_node.return_value = node

        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # node_action is faked
        n_action = mock.Mock()
        n_action.id = 'NODE_ACTION_ID'
        mock_action = self.patchobject(base_action, 'Action',
                                       return_value=n_action)
        mock_status = self.patchobject(n_action, 'set_status')

        # do it
        res_code, res_msg = action._create_nodes(cluster, 1)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_get.assert_called_once_with(action.context, 'CLUSTER_ID',
                                         project_safe=True, show_deleted=False)
        mock_node.assert_called_once_with('node-CLUSTER_-001',
                                          'FAKE_PROFILE',
                                          'CLUSTER_ID',
                                          context=action.context,
                                          user='FAKE_USER',
                                          project='FAKE_PROJECT',
                                          domain='FAKE_DOMAIN',
                                          index=1, metadata={})
        node.store.assert_called_once_with(action.context)
        mock_action.assert_called_once_with(action.context, 'NODE_ID',
                                            'NODE_CREATE',
                                            name='node_create_NODE_ID',
                                            cause='Derived Action')
        mock_dep.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                         'CLUSTER_ACTION_ID')
        mock_status.assert_called_once_with(action.READY)
        mock_start.assert_called_once_with(action.context,
                                           action_id='NODE_ACTION_ID')
        mock_wait.assert_called_once_with()
        self.assertEqual(['NODE_ID'], action.data['nodes'])

    @mock.patch.object(db_api, 'cluster_get')
    def test__create_nodes_zero(self, mock_get):
        cluster = mock.Mock()
        mock_get.return_value = mock.Mock()
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')

        res_code, res_msg = action._create_nodes(cluster, 0)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('', res_msg)

    @mock.patch.object(db_api, 'cluster_get')
    @mock.patch.object(node_mod, 'Node')
    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__create_nodes_multiple(self, mock_wait, mock_start, mock_dep,
                                    mock_node, mock_get):
        cluster = mock.Mock()
        cluster.id = '01234567-123434'
        db_cluster = mock.Mock()
        db_cluster.next_index = 1
        mock_get.return_value = db_cluster
        node1 = mock.Mock()
        node1.id = '01234567-abcdef'
        node1.data = {}
        node2 = mock.Mock()
        node2.id = 'abcdefab-123456'
        node2.data = {}
        mock_node.side_effect = [node1, node2]

        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'placement': [
                {'region': 'regionOne'},
                {'region': 'regionTwo'}
            ]
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # node_action is faked
        node_action_1 = mock.Mock()
        node_action_2 = mock.Mock()
        mock_action = self.patchobject(
            base_action, 'Action', side_effect=[node_action_1, node_action_2])
        mock_status_1 = self.patchobject(node_action_1, 'set_status')
        mock_status_2 = self.patchobject(node_action_2, 'set_status')

        # do it
        res_code, res_msg = action._create_nodes(cluster, 2)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(1, mock_get.call_count)
        self.assertEqual(2, mock_node.call_count)
        node1.store.assert_called_once_with(action.context)
        node2.store.assert_called_once_with(action.context)
        self.assertEqual(2, mock_action.call_count)
        self.assertEqual(2, mock_dep.call_count)
        mock_status_1.assert_called_once_with(action.READY)
        mock_status_2.assert_called_once_with(action.READY)
        self.assertEqual(2, mock_start.call_count)
        mock_wait.assert_called_once_with()
        self.assertEqual([node1.id, node2.id], action.data['nodes'])
        self.assertEqual({'region': 'regionOne'}, node1.data['placement'])
        self.assertEqual({'region': 'regionTwo'}, node2.data['placement'])

    @mock.patch.object(db_api, 'cluster_get')
    @mock.patch.object(node_mod, 'Node')
    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__create_nodes_multiple_failed_wait(self, mock_wait, mock_start,
                                                mock_dep, mock_node, mock_get):
        cluster = mock.Mock()
        cluster.id = '01234567-123434'
        db_cluster = mock.Mock()
        db_cluster.next_index = 1
        mock_get.return_value = db_cluster
        node1 = mock.Mock()
        node1.id = '01234567-abcdef'
        node1.data = {}
        node2 = mock.Mock()
        node2.id = 'abcdefab-123456'
        node2.data = {}
        mock_node.side_effect = [node1, node2]

        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'placement': [
                {'region': 'regionOne'},
                {'region': 'regionTwo'}
            ]
        }
        mock_wait.return_value = (action.RES_ERROR, 'Waiting timed out')

        # node_action is faked
        n_action_1 = mock.Mock()
        n_action_2 = mock.Mock()
        self.patchobject(base_action, 'Action',
                         side_effect=[n_action_1, n_action_2])
        self.patchobject(n_action_1, 'set_status')
        self.patchobject(n_action_2, 'set_status')

        # do it
        res_code, res_msg = action._create_nodes(cluster, 2)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Waiting timed out', res_msg)

    def test_do_create_success(self):
        cluster = mock.Mock()
        cluster.do_create.return_value = True
        cluster.set_status = mock.Mock()
        cluster.ACTIVE = 'ACTIVE'

        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')

        x_create_nodes = self.patchobject(action, '_create_nodes',
                                          return_value=(action.RES_OK, 'OK'))
        # do it
        res_code, res_msg = action.do_create(cluster)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster creation succeeded.', res_msg)
        x_create_nodes.assert_called_once_with(cluster,
                                               cluster.desired_capacity)
        cluster.set_status.assert_called_once_with(
            action.context, 'ACTIVE', 'Cluster creation succeeded.')

    def test_do_create_failed_create_cluster(self):
        cluster = mock.Mock()
        cluster.do_create.return_value = False
        cluster.set_status = mock.Mock()
        cluster.ERROR = 'ERROR'
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')

        # do it
        res_code, res_msg = action.do_create(cluster)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Cluster creation failed.', res_msg)
        cluster.set_status.assert_called_once_with(
            action.context, 'ERROR', 'Cluster creation failed.')

    def test_do_create_failed_create_nodes(self):
        cluster = mock.Mock()
        cluster.do_create.return_value = True
        cluster.set_status = mock.Mock()
        cluster.ERROR = 'ERROR'
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')

        # do it
        for code in [action.RES_CANCEL, action.RES_TIMEOUT, action.RES_ERROR]:
            self.patchobject(action, '_create_nodes',
                             return_value=(code, 'Really Bad'))

            res_code, res_msg = action.do_create(cluster)

            self.assertEqual(code, res_code)
            self.assertEqual('Really Bad', res_msg)
            cluster.set_status.assert_called_once_with(
                action.context, 'ERROR', 'Really Bad')
            cluster.set_status.reset_mock()

    def test_do_create_failed_for_retry(self):
        cluster = mock.Mock()
        cluster.do_create.return_value = True
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        self.patchobject(action, '_create_nodes',
                         return_value=(action.RES_RETRY, 'retry'))

        # do it
        res_code, res_msg = action.do_create(cluster)

        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual('retry', res_msg)

    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test_do_update_multi(self, mock_wait, mock_start, mock_dep):
        node1 = mock.Mock()
        node1.id = 'fake id 1'
        node2 = mock.Mock()
        node2.id = 'fake id 2'
        cluster = mock.Mock()
        cluster.nodes = [node1, node2]
        cluster.ACTIVE = 'ACTIVE'

        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}

        n_action_1 = mock.Mock()
        n_action_2 = mock.Mock()
        mock_action = self.patchobject(base_action, 'Action',
                                       side_effect=[n_action_1, n_action_2])
        mock_wait.return_value = (action.RES_OK, 'OK')

        # do it
        res_code, res_msg = action.do_update(cluster)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)
        self.assertEqual(2,  mock_action.call_count)
        n_action_1.store.assert_called_once_with(action.context)
        n_action_2.store.assert_called_once_with(action.context)
        self.assertEqual(2, mock_dep.call_count)
        self.assertEqual(1, n_action_1.set_status.call_count)
        self.assertEqual(1, n_action_2.set_status.call_count)
        self.assertEqual(2, mock_start.call_count)
        self.assertEqual('FAKE_PROFILE', cluster.profile_id)
        cluster.store.assert_called_once_with(action.context)
        cluster.set_status.assert_called_once_with(
            action.context, 'ACTIVE', 'Cluster update completed.')

    def test_do_update_empty_cluster(self):
        cluster = mock.Mock()
        cluster.nodes = []
        cluster.ACTIVE = 'ACTIVE'
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}

        # do it
        res_code, res_msg = action.do_update(cluster)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster update completed.', res_msg)

        self.assertEqual('FAKE_PROFILE', cluster.profile_id)
        cluster.store.assert_called_once_with(action.context)
        cluster.set_status.assert_called_once_with(
            action.context, 'ACTIVE', 'Cluster update completed.')

    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test_do_update_failed_wait(self, mock_wait, mock_start, mock_dep):
        node = mock.Mock()
        node.id = 'fake node id'
        cluster = mock.Mock()
        cluster.nodes = [node]
        cluster.ACTIVE = 'ACTIVE'

        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'new_profile_id': 'FAKE_PROFILE'}

        n_action = mock.Mock()
        mock_action = self.patchobject(base_action, 'Action',
                                       return_value=n_action)
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout')

        # do it
        res_code, res_msg = action.do_update(cluster)

        # assertions
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout', res_msg)
        self.assertEqual(1,  mock_action.call_count)
        n_action.store.assert_called_once_with(action.context)
        self.assertEqual(1, mock_dep.call_count)
        self.assertEqual(1, n_action.set_status.call_count)
        self.assertEqual(1, mock_start.call_count)
        mock_wait.assert_called_once_with()

    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_single(self, mock_wait, mock_start, mock_dep):
        # prepare mocks
        cluster = mock.Mock()
        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # n_action is faked
        n_action = mock.Mock()
        n_action.id = 'NODE_ACTION_ID'
        mock_action = self.patchobject(base_action, 'Action',
                                       return_value=n_action)
        # do it
        res_code, res_msg = action._delete_nodes(cluster, ['NODE_ID'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID', cause='Derived Action')
        n_action.store.assert_called_once_with(action.context)
        mock_dep.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                         'CLUSTER_ACTION_ID')
        n_action.set_status.assert_called_once_with(action.READY)
        mock_start.assert_called_once_with(action.context,
                                           action_id='NODE_ACTION_ID')
        mock_wait.assert_called_once_with()
        self.assertEqual(['NODE_ID'], action.data['nodes'])

    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_multi(self, mock_wait, mock_start, mock_dep):
        # prepare mocks
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'

        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # node_action is faked
        n_action_1 = mock.Mock()
        n_action_1.id = 'NODE_ACTION_1'
        n_action_2 = mock.Mock()
        n_action_2.id = 'NODE_ACTION_1'
        mock_action = self.patchobject(base_action, 'Action',
                                       side_effect=[n_action_1, n_action_2])
        # do it
        res_code, res_msg = action._delete_nodes(cluster, ['NODE_1', 'NODE_2'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(2, mock_action.call_count)
        n_action_1.store.assert_called_once_with(action.context)
        n_action_2.store.assert_called_once_with(action.context)
        n_action_1.set_status.assert_called_once_with(action.READY)
        n_action_2.set_status.assert_called_once_with(action.READY)
        self.assertEqual(2, mock_dep.call_count)
        self.assertEqual(2, mock_start.call_count)
        mock_wait.assert_called_once_with()
        self.assertEqual(['NODE_1', 'NODE_2'], action.data['nodes'])

    def test__delete_empty(self):
        # prepare mocks
        cluster = mock.Mock()
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_DELETE')

        # do it
        res_code, res_msg = action._delete_nodes(cluster, [])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('', res_msg)

    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_pd(self, mock_wait, mock_start, mock_dep):
        # prepare mocks
        cluster = mock.Mock()
        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_DELETE')
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'deletion': {
                'destroy_after_delete': False
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')

        # n_action is faked
        n_action = mock.Mock()
        n_action.id = 'NODE_ACTION_ID'
        mock_action = self.patchobject(base_action, 'Action',
                                       return_value=n_action)
        # do it
        res_code, res_msg = action._delete_nodes(cluster, ['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_LEAVE',
            name='node_delete_NODE_ID', cause='Derived Action')

    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_failed_wait(self, mock_wait, mock_start, mock_dep):
        # prepare mocks
        cluster = mock.Mock()
        # cluster action is real
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_DELETE')
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {}
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        # n_action is faked
        n_action = mock.Mock()
        n_action.id = 'NODE_ACTION_ID'
        self.patchobject(base_action, 'Action', return_value=n_action)

        # do it
        res_code, res_msg = action._delete_nodes(cluster, ['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)
        self.assertEqual({}, action.data)

    def test_do_delete_success(self):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_DELETE')
        action.data = {}

        node1 = mock.Mock()
        node1.id = 'NODE_1'
        node2 = mock.Mock()
        node2.id = 'NODE_2'

        cluster = mock.Mock()
        cluster.nodes = [node1, node2]
        cluster.DELETING = 'DELETING'
        cluster.do_delete.return_value = True
        mock_delete = self.patchobject(action, '_delete_nodes',
                                       return_value=(action.RES_OK, 'Good'))

        # do it
        res_code, res_msg = action.do_delete(cluster)

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Good', res_msg)
        self.assertEqual({'deletion': {'destroy_after_delete': True}},
                         action.data)
        cluster.set_status.assert_called_once_with(action.context, 'DELETING',
                                                   'Deletion in progress.')
        mock_delete.assert_called_once_with(cluster, ['NODE_1', 'NODE_2'])
        cluster.do_delete.assert_called_once_with(action.context)

    def test_do_delete_failed_delete_nodes(self):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_DELETE')
        action.data = {}

        node = mock.Mock()
        node.id = 'NODE_1'
        cluster = mock.Mock()
        cluster.nodes = [node]
        cluster.ACTIVE = 'ACTIVE'
        cluster.DELETING = 'DELETING'
        cluster.WARNING = 'WARNING'

        # timeout
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_TIMEOUT, 'Timeout!'))
        res_code, res_msg = action.do_delete(cluster)

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)
        cluster.set_status.assert_has_calls([
            mock.call(action.context, 'DELETING', 'Deletion in progress.'),
            mock.call(action.context, 'WARNING', 'Timeout!')])
        cluster.set_status.reset_mock()

        # error
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_ERROR, 'Error!'))
        res_code, res_msg = action.do_delete(cluster)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Error!', res_msg)
        cluster.set_status.assert_has_calls([
            mock.call(action.context, 'DELETING', 'Deletion in progress.'),
            mock.call(action.context, 'WARNING', 'Error!')])
        cluster.set_status.reset_mock()

        # cancel
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_CANCEL, 'Cancelled!'))
        res_code, res_msg = action.do_delete(cluster)

        self.assertEqual(action.RES_CANCEL, res_code)
        self.assertEqual('Cancelled!', res_msg)
        cluster.set_status.assert_has_calls([
            mock.call(action.context, 'DELETING', 'Deletion in progress.'),
            mock.call(action.context, 'ACTIVE', 'Cancelled!')])

        # retry
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_RETRY, 'Busy!'))
        res_code, res_msg = action.do_delete(cluster)

        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual('Busy!', res_msg)

    def test_do_delete_failed_delete_cluster(self):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_DELETE')
        action.data = {}

        node = mock.Mock()
        node.id = 'NODE_1'
        cluster = mock.Mock()
        cluster.nodes = [node]
        cluster.DELETING = 'DELETING'
        cluster.do_delete.return_value = False
        self.patchobject(action, '_delete_nodes',
                         return_value=(action.RES_OK, 'Good'))
        # do it
        res_code, res_msg = action.do_delete(cluster)

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Cannot delete cluster object.', res_msg)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test_do_add_nodes_single(self, mock_wait, mock_start, mock_dep,
                                 mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'nodes': ['NODE_1']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        node = mock.Mock()
        node.id = 'NODE_1'
        node.cluster_id = None
        node.status = node.ACTIVE
        mock_load.return_value = node

        node_action = mock.Mock()
        node_action.id = 'NODE_ACTION_ID'
        mock_action = self.patchobject(base_action, 'Action',
                                       return_value=node_action)
        mock_wait.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed adding nodes.', res_msg)
        self.assertEqual({'nodes': ['NODE_1']}, action.data)

        mock_load.assert_called_once_with(action.context, 'NODE_1')
        mock_action.assert_called_once_with(
            action.context, 'NODE_1', 'NODE_JOIN',
            name='node_join_NODE_1', cause='Derived Action',
            inputs={'cluster_id': 'CLUSTER_ID'})
        node_action.store.assert_called_once_with(action.context)
        mock_dep.assert_called_once_with(action.context, 'NODE_ACTION_ID',
                                         'CLUSTER_ACTION_ID')
        node_action.set_status.assert_called_once_with(action.READY)
        mock_start.assert_called_once_with(action.context,
                                           action_id='NODE_ACTION_ID')
        mock_wait.assert_called_once_with()

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test_do_add_nodes_multiple(self, mock_wait, mock_start, mock_dep,
                                   mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'nodes': ['NODE_1', 'NODE_2']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node1.id = 'NODE_1'
        node1.cluster_id = None
        node1.status = node1.ACTIVE
        node2 = mock.Mock()
        node2.id = 'NODE_2'
        node2.cluster_id = None
        node2.status = node2.ACTIVE
        mock_load.side_effect = [node1, node2]

        node_action_1 = mock.Mock()
        node_action_1.id = 'NODE_ACTION_ID_1'
        node_action_2 = mock.Mock()
        node_action_2.id = 'NODE_ACTION_ID_2'

        mock_action = self.patchobject(
            base_action, 'Action', side_effect=[node_action_1, node_action_2])
        mock_wait.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed adding nodes.', res_msg)
        self.assertEqual({'nodes': ['NODE_1', 'NODE_2']}, action.data)

        mock_load.assert_has_calls([
            mock.call(action.context, 'NODE_1'),
            mock.call(action.context, 'NODE_2')])
        mock_action.assert_has_calls([
            mock.call(action.context, 'NODE_1', 'NODE_JOIN',
                      name='node_join_NODE_1', cause='Derived Action',
                      inputs={'cluster_id': 'CLUSTER_ID'}),
            mock.call(action.context, 'NODE_2', 'NODE_JOIN',
                      name='node_join_NODE_2', cause='Derived Action',
                      inputs={'cluster_id': 'CLUSTER_ID'})])

        node_action_1.store.assert_called_once_with(action.context)
        node_action_2.store.assert_called_once_with(action.context)
        mock_dep.assert_has_calls([
            mock.call(action.context, 'NODE_ACTION_ID_1',
                      'CLUSTER_ACTION_ID'),
            mock.call(action.context, 'NODE_ACTION_ID_2',
                      'CLUSTER_ACTION_ID')])
        node_action_1.set_status.assert_called_once_with(action.READY)
        node_action_2.set_status.assert_called_once_with(action.READY)
        mock_start.assert_has_calls([
            mock.call(action.context, action_id='NODE_ACTION_ID_1'),
            mock.call(action.context, action_id='NODE_ACTION_ID_2')])

        mock_wait.assert_called_once_with()

    @mock.patch.object(node_mod.Node, 'load')
    def test_do_add_nodes_node_not_found(self, mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1']}
        mock_load.side_effect = exception.NodeNotFound(node='NODE_1')
        cluster = mock.Mock()

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node [NODE_1] is not found.", res_msg)

    @mock.patch.object(node_mod.Node, 'load')
    def test_do_add_nodes_node_already_member(self, mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        node = mock.Mock()
        node.cluster_id = 'FAKE_CLUSTER'
        mock_load.return_value = node

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual("Completed adding nodes.", res_msg)
        self.assertEqual({}, action.data)

    @mock.patch.object(node_mod.Node, 'load')
    def test_do_add_nodes_node_in_other_cluster(self, mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        node = mock.Mock()
        node.cluster_id = 'ANOTHER_CLUSTER'
        mock_load.return_value = node

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node [NODE_1] is already owned by cluster "
                         "[ANOTHER_CLUSTER].", res_msg)

    @mock.patch.object(node_mod.Node, 'load')
    def test_do_add_nodes_node_not_active(self, mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        node = mock.Mock()
        node.cluster_id = None
        node.status = node.ERROR
        mock_load.return_value = node

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node [NODE_1] is not in ACTIVE status.", res_msg)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(db_api, 'action_add_dependency')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(cluster_action.ClusterAction, '_wait_for_dependents')
    def test_do_add_nodes_failed_waiting(self, mock_wait, mock_start, mock_dep,
                                         mock_load):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'nodes': ['NODE_1']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        node = mock.Mock()
        node.id = 'NODE_1'
        node.cluster_id = None
        node.status = node.ACTIVE
        mock_load.return_value = node

        node_action = mock.Mock()
        node_action.id = 'NODE_ACTION_ID'
        self.patchobject(base_action, 'Action', return_value=node_action)
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')

        # do it
        res_code, res_msg = action.do_add_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)
        self.assertEqual({}, action.data)

    @mock.patch.object(db_api, 'node_get')
    @mock.patch.object(cluster_action.ClusterAction, '_delete_nodes')
    def test_do_del_nodes(self, mock_delete, mock_get):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'nodes': ['NODE_1', 'NODE_2']}
        action.data = {}

        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        node1 = mock.Mock()
        node1.id = 'NODE_1'
        node1.cluster_id = 'FAKE_CLUSTER'
        node2 = mock.Mock()
        node2.id = 'NODE_2'
        node2.cluster_id = 'FAKE_CLUSTER'
        mock_get.side_effect = [node1, node2]
        mock_delete.return_value = (action.RES_OK, 'Good to go!')

        # do it
        res_code, res_msg = action.do_del_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Completed deleting nodes.', res_msg)
        self.assertEqual({'deletion': {'destroy_after_delete': False}},
                         action.data)

        mock_get.assert_has_calls([
            mock.call(action.context, 'NODE_1', show_deleted=False),
            mock.call(action.context, 'NODE_2', show_deleted=False)])
        mock_delete.assert_called_once_with(cluster, ['NODE_1', 'NODE_2'])

    @mock.patch.object(db_api, 'node_get')
    def test_do_del_nodes_node_not_found(self, mock_get):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1']}
        cluster = mock.Mock()
        mock_get.side_effect = exception.NodeNotFound(node='NODE_1')

        # do it
        res_code, res_msg = action.do_del_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Node [NODE_1] is not found.", res_msg)
        self.assertEqual({}, action.data)

    @mock.patch.object(db_api, 'node_get')
    def test_do_del_nodes_node_not_member(self, mock_get):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1', 'NODE_2']}
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        node1 = mock.Mock()
        node1.cluster_id = None
        node2 = mock.Mock()
        node2.cluster_id = 'ANOTHER_CLUSTER'
        mock_get.side_effect = [node1, node2]

        # do it
        res_code, res_msg = action.do_del_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual("Completed deleting nodes.", res_msg)
        self.assertEqual({}, action.data)

    @mock.patch.object(db_api, 'node_get')
    @mock.patch.object(cluster_action.ClusterAction, '_delete_nodes')
    def test_do_del_nodes_failed_delete(self, mock_delete, mock_get):
        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')
        action.inputs = {'nodes': ['NODE_1']}
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        node1 = mock.Mock()
        node1.cluster_id = 'FAKE_CLUSTER'
        mock_get.side_effect = [node1]
        mock_delete.return_value = (action.RES_ERROR, 'Things went bad.')

        # do it
        res_code, res_msg = action.do_del_nodes(cluster)

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Things went bad.", res_msg)

    def test__update_cluster_properties_no_store_needed(self):
        cluster = mock.Mock()
        cluster.min_size = 10
        cluster.max_size = 20
        cluster.desired_capacity = 15

        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')

        res, msg = action._update_cluster_properties(cluster, None, None, None)
        self.assertEqual(action.RES_OK, res)
        self.assertEqual('', msg)

        res, msg = action._update_cluster_properties(cluster, 15, 10, 20)
        self.assertEqual(action.RES_OK, res)
        self.assertEqual('', msg)

    def test__update_cluster_properties_with_store(self):
        def new_cluster():
            cluster = mock.Mock()
            cluster.min_size = 10
            cluster.max_size = 20
            cluster.desired_capacity = 15
            return cluster

        action = cluster_action.ClusterAction(self.ctx, 'ID', 'CLUSTER_ACTION')

        args = [
            (16, None, None),
            (None, 11, None),
            (None, None, 21),
            (16, 11, None),
            (None, 11, 21),
            (16, None, 21)
        ]

        for pargs in args:
            cluster = new_cluster()
            res, msg = action._update_cluster_properties(cluster, *pargs)
            self.assertEqual(action.RES_OK, res)
            self.assertEqual('', msg)
            self.assertEqual('Cluster properties updated.',
                             cluster.status_reason)
            cluster.store.assert_called_once_with(action.context)
            cluster.store.reset_mock()
