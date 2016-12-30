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

from senlin.engine.actions import base as ab
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.engine import event as EVENT
from senlin.engine import senlin_lock
from senlin.policies import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


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
            action, 'error', 'Policy check failure: Something is wrong.')

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
            action, 'error', 'Unsupported action: CLUSTER_DANCE.')

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
            action, 'error', 'Policy check failure: Policy checking failed.')

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
