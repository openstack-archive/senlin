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
from senlin.common import exception as exc
from senlin.engine.actions import base as ab
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.engine import dispatcher
from senlin.engine import senlin_lock
from senlin.policies import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

CLUSTER_ID = 'e1cfd82b-dc95-46ad-86e8-37864d7be1cd'
OBJID = '571fffb8-f41c-4cbc-945c-cb2937d76f19'
ACTION_ID = '4c2cead2-fd74-418a-9d12-bd2d9bd7a812'


@mock.patch.object(cm.Cluster, 'load')
class ClusterActionTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterActionTest, self).setUp()
        self.ctx = utils.dummy_context()

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

    @mock.patch.object(ab.Action, 'policy_check')
    def test_execute_failed_policy_check(self, mock_check, mock_load):
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

    @mock.patch.object(ab.Action, 'policy_check')
    def test_execute_unsupported_action(self, mock_check, mock_load):
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

    def test_execute_post_check_failed(self, mock_load):
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

        self.assertEqual(action.RES_RETRY, res_code)
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


class CompleteLifecycleProcTest(base.SenlinTestCase):

    def setUp(self):
        super(CompleteLifecycleProcTest, self).setUp()

        self.ctx = utils.dummy_context()

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ab.Action, 'load')
    def test_complete_lifecycle_proc_successful(self, mock_load,
                                                mock_dispatcher_start):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
        mock_obj = mock.Mock()
        action.entity = mock_obj
        mock_get_status = self.patchobject(action, 'get_status')
        mock_get_status.return_value = \
            consts.ACTION_WAITING_LIFECYCLE_COMPLETION
        mock_set_status = self.patchobject(action, 'set_status')
        mock_load.return_value = action

        res = ca.CompleteLifecycleProc(self.ctx, 'ACTION_ID')

        self.assertTrue(res)
        mock_load.assert_called_once_with(self.ctx, action_id='ACTION_ID',
                                          project_safe=False)
        mock_get_status.assert_called_once_with()
        mock_set_status.assert_called_once_with(action.RES_LIFECYCLE_COMPLETE)
        mock_dispatcher_start.assert_called_once_with()

    @mock.patch.object(ab.Action, 'load')
    def test_complete_lifecycle_proc_failed_action_not_found(self, mock_load):
        mock_load.return_value = None

        self.assertRaises(exc.ResourceNotFound,
                          ca.CompleteLifecycleProc,
                          self.ctx, 'ACTION')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(ab.Action, 'load')
    def test_complete_lifecycle_proc_warning(self, mock_load,
                                             mock_dispatcher_start):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
        mock_obj = mock.Mock()
        action.entity = mock_obj
        mock_get_status = self.patchobject(action, 'get_status')
        mock_get_status.return_value = consts.ACTION_SUCCEEDED
        mock_set_status = self.patchobject(action, 'set_status')
        mock_load.return_value = action

        res = ca.CompleteLifecycleProc(self.ctx, 'ACTION_ID')

        self.assertFalse(res)
        mock_load.assert_called_once_with(self.ctx, action_id='ACTION_ID',
                                          project_safe=False)
        mock_get_status.assert_called_once_with()
        mock_set_status.assert_not_called()
        mock_dispatcher_start.assert_not_called()
