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
from senlin.engine.notifications import message as msg
from senlin.objects import action as ao
from senlin.objects import dependency as dobj
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterDeleteTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterDeleteTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_single(self, mock_wait, mock_start, mock_dep,
                                  mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='FAKE_CLUSTER', desired_capacity=100, config={})

        # cluster action is real
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID', cause='Derived Action', inputs={})
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
    def test__delete_nodes_single_stop_node(self, mock_wait, mock_start,
                                            mock_dep, mock_action, mock_update,
                                            mock_load):
        # prepare mocks
        cluster = mock.Mock(id='FAKE_CLUSTER', desired_capacity=100,
                            config={'cluster.stop_node_before_delete': True})

        # cluster action is real
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        create_actions = [
            mock.call(action.context, 'NODE_ID', 'NODE_OPERATION',
                      name='node_delete_NODE_ID',
                      cause='Derived Action',
                      inputs={'operation': 'stop'}),
            mock.call(action.context, 'NODE_ID', 'NODE_DELETE',
                      name='node_delete_NODE_ID',
                      cause='Derived Action', inputs={})
        ]
        mock_action.assert_has_calls(create_actions)
        dep_calls = [
            mock.call(action.context, ['NODE_ACTION_ID'], 'CLUSTER_ACTION_ID'),
            mock.call(action.context, ['NODE_ACTION_ID'], 'CLUSTER_ACTION_ID'),
        ]
        mock_dep.assert_has_calls(dep_calls)
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_ID', {'status': 'READY'}),
            mock.call(action.context, 'NODE_ACTION_ID', {'status': 'READY'})
        ]
        mock_update.assert_has_calls(update_calls)
        mock_start.assert_has_calls([mock.call(), mock.call()])
        mock_wait.assert_has_calls([mock.call(), mock.call()])
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
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster

        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
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
        action.inputs = {'destroy_after_deletion': False}

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
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
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
            name='node_delete_NODE_ID', cause='Derived Action', inputs={})

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(msg.Message, 'post_lifecycle_hook_message')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_lifecycle_hook(self, mock_wait, mock_start,
                                               mock_post, mock_dep,
                                               mock_node_get,
                                               mock_action, mock_update,
                                               mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'zaqar',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'
        mock_node_get.return_value = mock.Mock(
            status=consts.NS_ACTIVE, id='NODE_ID', physical_id="nova-server")

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(1, mock_dep.call_count)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID',
            cause='Derived Action with Lifecycle Hook',
            inputs={})
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_ID',
                      {'status': 'WAITING_LIFECYCLE_COMPLETION'}),
        ]
        mock_update.assert_has_calls(update_calls)
        mock_post.assert_called_once_with('NODE_ACTION_ID', 'NODE_ID',
                                          'nova-server',
                                          consts.LIFECYCLE_NODE_TERMINATION)
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with(action.data['hooks']['timeout'])

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(msg.Message, 'post_lifecycle_hook_message')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_lifecycle_hook_failed_node(
            self, mock_wait, mock_start, mock_post, mock_dep, mock_node_get,
            mock_action, mock_update, mock_load):
        self.delete_nodes_with_lifecycle_hook_invalid_node(
            mock.Mock(status=consts.NS_ERROR), mock_wait, mock_start,
            mock_post, mock_dep, mock_node_get, mock_action, mock_update,
            mock_load)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(msg.Message, 'post_lifecycle_hook_message')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_lifecycle_hook_missing_node(
            self, mock_wait, mock_start, mock_post, mock_dep, mock_node_get,
            mock_action, mock_update, mock_load):
        self.delete_nodes_with_lifecycle_hook_invalid_node(
            None, mock_wait, mock_start, mock_post, mock_dep, mock_node_get,
            mock_action, mock_update, mock_load)

    def delete_nodes_with_lifecycle_hook_invalid_node(
            self, mock_node_obj, mock_wait, mock_start, mock_post, mock_dep,
            mock_node_get, mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'zaqar',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'
        mock_node_get.return_value = mock_node_obj
        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(1, mock_dep.call_count)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID',
            cause='Derived Action with Lifecycle Hook', inputs={})
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_ID',
                      {'status': 'READY'}),
        ]
        mock_update.assert_has_calls(update_calls)
        mock_post.assert_not_called()
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with(action.data['hooks']['timeout'])

    @mock.patch.object(ao.Action, 'check_status')
    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(msg.Message, 'post_lifecycle_hook_message')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_lifecycle_hook_timeout(self, mock_wait,
                                                       mock_start,
                                                       mock_post, mock_dep,
                                                       mock_node_get,
                                                       mock_action,
                                                       mock_update,
                                                       mock_check_status,
                                                       mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'zaqar',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_wait.side_effect = [
            (action.RES_LIFECYCLE_HOOK_TIMEOUT, 'Timeout'),
            (action.RES_OK, 'All dependents completed')
        ]
        mock_action.return_value = 'NODE_ACTION_ID'
        mock_node_get.return_value = mock.Mock(
            status=consts.NS_ACTIVE, id='NODE_ID', physical_id="nova-server")
        mock_check_status.return_value = 'WAITING_LIFECYCLE_COMPLETION'
        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(1, mock_dep.call_count)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID',
            cause='Derived Action with Lifecycle Hook', inputs={})
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_ID',
                      {'status': 'WAITING_LIFECYCLE_COMPLETION'}),
            mock.call(action.context, 'NODE_ACTION_ID',
                      {'status': 'READY'}),
        ]
        mock_update.assert_has_calls(update_calls)
        mock_post.assert_called_once_with('NODE_ACTION_ID', 'NODE_ID',
                                          'nova-server',
                                          consts.LIFECYCLE_NODE_TERMINATION)
        mock_start.assert_has_calls([mock.call(), mock.call()])
        wait_calls = [
            mock.call(action.data['hooks']['timeout']),
            mock.call()
        ]
        mock_wait.assert_has_calls(wait_calls)

    @mock.patch.object(ab.Action, 'create')
    def test__delete_nodes_with_lifecycle_hook_invalid_type(self,
                                                            mock_action,
                                                            mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'unknown_type',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_action.return_value = 'NODE_ACTION_ID'
        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Failed in deleting nodes: Lifecycle hook type "
                         "'unknown_type' is not implemented", res_msg)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    def test__delete_nodes_with_lifecycle_hook_unsupported_webhook(self,
                                                                   mock_action,
                                                                   mock_update,
                                                                   mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100, config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'webhook',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_action.return_value = 'NODE_ACTION_ID'
        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("Failed in deleting nodes: Lifecycle hook type "
                         "'webhook' is not implemented", res_msg)

    @mock.patch.object(ca.ClusterAction, '_remove_nodes_normally')
    def test__delete_nodes_failed_remove_stop_node(self, mock_remove,
                                                   mock_load):
        # prepare mocks
        cluster = mock.Mock(id='ID',
                            config={'cluster.stop_node_before_delete': True})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        action.data = {}
        mock_remove.side_effect = [(action.RES_TIMEOUT, 'Timeout!'),
                                   (action.RES_OK, 'OK')]

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual({}, action.data)
        remove_calls = [
            mock.call('NODE_OPERATION', ['NODE_ID'], {'operation': 'stop'}),
            mock.call('NODE_DELETE', ['NODE_ID']),
        ]
        mock_remove.assert_has_calls(remove_calls)

    @mock.patch.object(ca.ClusterAction, '_remove_nodes_with_hook')
    @mock.patch.object(ca.ClusterAction, '_remove_nodes_normally')
    def test__delete_nodes_with_lifecycle_hook_failed_remove_stop_node(
            self, mock_remove_normally, mock_remove_hook, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='ID',
                            config={'cluster.stop_node_before_delete': True})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        lifecycle_hook = {
            'timeout': 10,
            'type': 'zaqar',
            'params': {
                'queue': 'myqueue'
            }
        }
        action.data = {
            'hooks': lifecycle_hook,
        }
        mock_remove_hook.return_value = (action.RES_TIMEOUT, 'Timeout!')
        mock_remove_normally.return_value = (action.RES_OK, '')

        # do it
        res_code, res_msg = action._delete_nodes(['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        mock_remove_hook.assert_called_once_with(
            'NODE_OPERATION', ['NODE_ID'], lifecycle_hook,
            {'operation': 'stop'})
        mock_remove_normally.assert_called_once_with('NODE_DELETE',
                                                     ['NODE_ID'])

    @mock.patch.object(ao.Action, 'delete_by_target')
    def test_do_delete_success(self, mock_action, mock_load):
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
        mock_action.assert_called_once_with(
            action.context, 'FAKE_CLUSTER',
            action_excluded=['CLUSTER_DELETE'],
            status=['SUCCEEDED', 'FAILED'])

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
            action.context, consts.CLUSTER_DELETE)

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
            action.context, consts.CLUSTER_DELETE)

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
            action.context, consts.CLUSTER_DELETE)

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
            action.context, consts.CLUSTER_DELETE)

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
            action.context, consts.CLUSTER_DELETE)

    @mock.patch.object(ao.Action, 'check_status')
    def test_wait_for_dependents(self, mock_check_status, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.data = {}
        mock_check_status.return_value = 'READY'

        # do it
        res_code, res_msg = action._wait_for_dependents()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents ended with success', res_msg)

    @mock.patch.object(ao.Action, 'check_status')
    @mock.patch.object(ab.Action, 'is_cancelled')
    def test_wait_for_dependents_cancelled(self, mock_cancelled,
                                           mock_check_status, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'ID1'
        action.data = {}
        mock_check_status.return_value = 'RUNNING'
        mock_cancelled.return_value = True

        # do it
        res_code, res_msg = action._wait_for_dependents()

        self.assertEqual(action.RES_CANCEL, res_code)
        self.assertEqual('CLUSTER_DELETE [ID1] cancelled', res_msg)

    @mock.patch.object(ao.Action, 'check_status')
    @mock.patch.object(ab.Action, 'is_cancelled')
    @mock.patch.object(ab.Action, 'is_timeout')
    def test_wait_for_dependents_timeout(self, mock_timeout, mock_cancelled,
                                         mock_check_status, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'ID1'
        action.data = {}

        mock_check_status.return_value = 'RUNNING'
        mock_cancelled.return_value = False
        mock_timeout.return_value = True

        # do it
        res_code, res_msg = action._wait_for_dependents()

        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('CLUSTER_DELETE [ID1] timeout', res_msg)

    @mock.patch.object(ao.Action, 'check_status')
    @mock.patch.object(ab.Action, 'is_cancelled')
    @mock.patch.object(ab.Action, 'is_timeout')
    def test_wait_for_dependents_lifecycle_timeout(self,
                                                   mock_timeout,
                                                   mock_cancelled,
                                                   mock_check_status,
                                                   mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'ID1'
        action.data = {}

        mock_check_status.return_value = 'RUNNING'
        mock_cancelled.return_value = False
        mock_timeout.side_effect = [False, True]

        # do it
        res_code, res_msg = action._wait_for_dependents(0)

        self.assertEqual(action.RES_LIFECYCLE_HOOK_TIMEOUT, res_code)
        self.assertEqual('CLUSTER_DELETE [ID1] lifecycle hook timeout',
                         res_msg)

    @mock.patch('senlin.engine.actions.base.wallclock', mock.MagicMock(
        return_value=10))
    def test_is_timeout(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.start_time = 0
        action.timeout = 5

        # do it
        res = action.is_timeout()

        self.assertTrue(res)

    @mock.patch('senlin.engine.actions.base.wallclock', mock.MagicMock(
        return_value=10))
    def test_is_timeout_non_default(self, mock_load):
        node = mock.Mock(id='NODE_1')
        cluster = mock.Mock(id='CID', nodes=[node], DELETING='DELETING')
        cluster.do_delete.return_value = False
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.start_time = 0
        action.timeout = 5

        # do it
        res = action.is_timeout(20)

        self.assertEqual(False, res)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__remove_nodes_normally(self, mock_wait, mock_start, mock_dep,
                                    mock_action, mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100)
        mock_load.return_value = cluster

        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']

        # do it
        res_code, res_msg = action._remove_nodes_normally('NODE_REMOVE',
                                                          ['NODE_1', 'NODE_2'])

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

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(msg.Message, 'post_lifecycle_hook_message')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__remove_nodes_with_hook(self, mock_wait, mock_start, mock_post,
                                     mock_dep, mock_node_get, mock_action,
                                     mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100)
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'zaqar',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        mock_action.return_value = 'NODE_ACTION_ID'
        mock_node_get.return_value = mock.Mock(
            status=consts.NS_ACTIVE, id='NODE_ID', physical_id="nova-server")
        # do it
        res_code, res_msg = action._remove_nodes_with_hook(
            'NODE_DELETE', ['NODE_ID'], action.data['hooks'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        self.assertEqual(1, mock_dep.call_count)
        mock_action.assert_called_once_with(
            action.context, 'NODE_ID', 'NODE_DELETE',
            name='node_delete_NODE_ID',
            cause='Derived Action with Lifecycle Hook', inputs={})
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_ID',
                      {'status': 'WAITING_LIFECYCLE_COMPLETION'}),
        ]
        mock_update.assert_has_calls(update_calls)
        mock_post.assert_called_once_with('NODE_ACTION_ID', 'NODE_ID',
                                          'nova-server',
                                          consts.LIFECYCLE_NODE_TERMINATION)
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with(action.data['hooks']['timeout'])

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__remove_nodes_normally_failed_wait(self, mock_wait, mock_start,
                                                mock_dep, mock_action,
                                                mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='ID', config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        action.data = {}
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._remove_nodes_normally('NODE_REMOVE',
                                                          ['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)
        self.assertEqual({}, action.data)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__remove_nodes_hook_failed_wait(self, mock_wait, mock_start,
                                            mock_dep, mock_action,
                                            mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='ID', config={})
        mock_load.return_value = cluster
        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.inputs = {'destroy_after_deletion': False}
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'zaqar',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_wait.return_value = (action.RES_TIMEOUT, 'Timeout!')
        mock_action.return_value = 'NODE_ACTION_ID'

        # do it
        res_code, res_msg = action._remove_nodes_normally('NODE_REMOVE',
                                                          ['NODE_ID'])

        # assertions (other assertions are skipped)
        self.assertEqual(action.RES_TIMEOUT, res_code)
        self.assertEqual('Timeout!', res_msg)

    @mock.patch.object(ao.Action, 'update')
    @mock.patch.object(ab.Action, 'create')
    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(dobj.Dependency, 'create')
    @mock.patch.object(msg.Message, 'post_lifecycle_hook_message')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ca.ClusterAction, '_wait_for_dependents')
    def test__delete_nodes_with_error_nodes(self, mock_wait, mock_start,
                                            mock_post, mock_dep,
                                            mock_node_get, mock_action,
                                            mock_update, mock_load):
        # prepare mocks
        cluster = mock.Mock(id='CLUSTER_ID', desired_capacity=100)
        mock_load.return_value = cluster

        # cluster action is real
        action = ca.ClusterAction(cluster.id, 'CLUSTER_DELETE', self.ctx)
        action.id = 'CLUSTER_ACTION_ID'
        action.data = {
            'hooks': {
                'timeout': 10,
                'type': 'zaqar',
                'params': {
                    'queue': 'myqueue'
                }
            }
        }
        mock_action.side_effect = ['NODE_ACTION_1', 'NODE_ACTION_2']
        mock_wait.return_value = (action.RES_OK, 'All dependents completed')
        node1 = mock.Mock(status=consts.NS_ACTIVE, id='NODE_1',
                          physical_id="nova-server-1")
        node2 = mock.Mock(status=consts.NS_ACTIVE, id='NODE_2',
                          physical_id=None)
        mock_node_get.side_effect = [node1, node2]
        # do it
        res_code, res_msg = action._remove_nodes_with_hook(
            'NODE_DELETE', ['NODE_1', 'NODE_2'], action.data['hooks'])

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('All dependents completed', res_msg)
        update_calls = [
            mock.call(action.context, 'NODE_ACTION_1',
                      {'status': 'WAITING_LIFECYCLE_COMPLETION'}),
            mock.call(action.context, 'NODE_ACTION_2', {'status': 'READY'})
        ]
        mock_update.assert_has_calls(update_calls)
        create_actions = [
            mock.call(action.context, 'NODE_1', 'NODE_DELETE',
                      name='node_delete_NODE_1',
                      cause='Derived Action with Lifecycle Hook', inputs={}),
            mock.call(action.context, 'NODE_2', 'NODE_DELETE',
                      name='node_delete_NODE_2',
                      cause='Derived Action with Lifecycle Hook', inputs={})
        ]
        mock_action.assert_has_calls(create_actions)

        mock_post.assert_called_once_with('NODE_ACTION_1', 'NODE_1',
                                          node1.physical_id,
                                          consts.LIFECYCLE_NODE_TERMINATION)
        mock_start.assert_called_once_with()
        mock_wait.assert_called_once_with(action.data['hooks']['timeout'])

        self.assertEqual(1, mock_dep.call_count)
