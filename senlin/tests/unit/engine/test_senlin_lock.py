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

from senlin.common import utils as common_utils
from senlin.engine import senlin_lock as lockm
from senlin.objects import action as ao
from senlin.objects import cluster_lock as clo
from senlin.objects import node_lock as nlo
from senlin.objects import service as svco
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class SenlinLockTest(base.SenlinTestCase):

    def setUp(self):
        super(SenlinLockTest, self).setUp()

        self.ctx = utils.dummy_context()

        ret = mock.Mock(owner='ENGINE', id='ACTION_ABC')
        self.stub_get = self.patchobject(ao.Action, 'get', return_value=ret)

    @mock.patch.object(clo.ClusterLock, "acquire")
    def test_cluster_lock_acquire_already_owner(self, mock_acquire):
        mock_acquire.return_value = ['ACTION_XYZ']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A', 'ACTION_XYZ')

        self.assertTrue(res)
        mock_acquire.assert_called_once_with('CLUSTER_A', 'ACTION_XYZ',
                                             lockm.CLUSTER_SCOPE)

    @mock.patch.object(common_utils, 'is_engine_dead')
    @mock.patch.object(svco.Service, 'gc_by_engine')
    @mock.patch.object(clo.ClusterLock, "acquire")
    @mock.patch.object(clo.ClusterLock, "steal")
    def test_cluster_lock_acquire_dead_owner(self, mock_steal, mock_acquire,
                                             mock_gc, mock_dead):
        mock_dead.return_value = True
        mock_acquire.return_value = ['ACTION_ABC']
        mock_steal.return_value = ['ACTION_XYZ']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A', 'ACTION_XYZ',
                                         'NEW_ENGINE')

        self.assertTrue(res)
        mock_acquire.assert_called_with("CLUSTER_A", "ACTION_XYZ",
                                        lockm.CLUSTER_SCOPE)
        self.assertEqual(3, mock_acquire.call_count)
        mock_steal.assert_called_once_with('CLUSTER_A', 'ACTION_XYZ')
        mock_gc.assert_called_once_with(mock.ANY)

    @mock.patch.object(common_utils, 'is_engine_dead')
    @mock.patch.object(clo.ClusterLock, "acquire")
    def test_cluster_lock_acquire_failed(self, mock_acquire, mock_dead):
        mock_dead.return_value = False
        mock_acquire.return_value = ['ACTION_ABC']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A', 'ACTION_XYZ')

        self.assertFalse(res)
        mock_acquire.assert_called_with('CLUSTER_A', 'ACTION_XYZ',
                                        lockm.CLUSTER_SCOPE)
        self.assertEqual(3, mock_acquire.call_count)

    @mock.patch.object(clo.ClusterLock, "acquire")
    @mock.patch.object(clo.ClusterLock, "steal")
    def test_cluster_lock_acquire_forced(self, mock_steal, mock_acquire):
        mock_acquire.return_value = ['ACTION_ABC']
        mock_steal.return_value = ['ACTION_XY']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A',
                                         'ACTION_XY', forced=True)

        self.assertTrue(res)
        mock_acquire.assert_called_with('CLUSTER_A', 'ACTION_XY',
                                        lockm.CLUSTER_SCOPE)
        self.assertEqual(3, mock_acquire.call_count)
        mock_steal.assert_called_once_with('CLUSTER_A', 'ACTION_XY')

    @mock.patch.object(common_utils, 'is_engine_dead')
    @mock.patch.object(clo.ClusterLock, "acquire")
    @mock.patch.object(clo.ClusterLock, "steal")
    def test_cluster_lock_acquire_steal_failed(self, mock_steal, mock_acquire,
                                               mock_dead):
        mock_dead.return_value = False
        mock_acquire.return_value = ['ACTION_ABC']
        mock_steal.return_value = []

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A',
                                         'ACTION_XY', forced=True)

        self.assertFalse(res)
        mock_acquire.assert_called_with('CLUSTER_A', 'ACTION_XY',
                                        lockm.CLUSTER_SCOPE)
        self.assertEqual(3, mock_acquire.call_count)
        mock_steal.assert_called_once_with('CLUSTER_A', 'ACTION_XY')

    @mock.patch.object(clo.ClusterLock, "release")
    def test_cluster_lock_release(self, mock_release):
        actual = lockm.cluster_lock_release('C', 'A', 'S')

        self.assertEqual(mock_release.return_value, actual)
        mock_release.assert_called_once_with('C', 'A', 'S')

    @mock.patch.object(nlo.NodeLock, "acquire")
    def test_node_lock_acquire_already_owner(self, mock_acquire):
        mock_acquire.return_value = 'ACTION_XYZ'

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A', 'ACTION_XYZ')

        self.assertTrue(res)
        mock_acquire.assert_called_once_with('NODE_A', 'ACTION_XYZ')

    @mock.patch.object(common_utils, 'is_engine_dead')
    @mock.patch.object(ao.Action, 'mark_failed')
    @mock.patch.object(nlo.NodeLock, "acquire")
    @mock.patch.object(nlo.NodeLock, "steal")
    def test_node_lock_acquire_dead_owner(self, mock_steal, mock_acquire,
                                          mock_action_fail, mock_dead):
        mock_dead.return_value = True
        mock_acquire.side_effect = ['ACTION_ABC']
        mock_steal.return_value = 'ACTION_XYZ'

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A', 'ACTION_XYZ',
                                      'NEW_ENGINE')

        self.assertTrue(res)
        mock_acquire.assert_called_once_with('NODE_A', 'ACTION_XYZ')
        mock_steal.assert_called_once_with('NODE_A', 'ACTION_XYZ')
        mock_action_fail.assert_called_once_with(
            self.ctx, 'ACTION_ABC', mock.ANY,
            'Engine died when executing this action.')

    @mock.patch.object(common_utils, 'is_engine_dead')
    @mock.patch.object(nlo.NodeLock, "acquire")
    def test_node_lock_acquire_failed(self, mock_acquire, mock_dead):
        mock_dead.return_value = False
        mock_acquire.side_effect = ['ACTION_ABC']

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A', 'ACTION_XYZ')

        self.assertFalse(res)
        mock_acquire.assert_called_once_with('NODE_A', 'ACTION_XYZ')

    @mock.patch.object(nlo.NodeLock, "acquire")
    @mock.patch.object(nlo.NodeLock, "steal")
    def test_node_lock_acquire_forced(self, mock_steal, mock_acquire):
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC']
        mock_steal.return_value = 'ACTION_XY'

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A',
                                      'ACTION_XY', forced=True)

        self.assertTrue(res)
        mock_acquire.assert_called_once_with('NODE_A', 'ACTION_XY')
        mock_steal.assert_called_once_with('NODE_A', 'ACTION_XY')

    @mock.patch.object(ao.Action, 'get')
    @mock.patch.object(nlo.NodeLock, "acquire")
    @mock.patch.object(nlo.NodeLock, "steal")
    def test_node_lock_acquire_steal_failed(self, mock_steal, mock_acquire,
                                            mock_get):
        mock_acquire.side_effect = ['ACTION_ABC']
        mock_steal.return_value = None

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A',
                                      'ACTION_XY', forced=True)

        self.assertFalse(res)
        mock_acquire.assert_called_once_with('NODE_A', 'ACTION_XY')
        mock_steal.assert_called_once_with('NODE_A', 'ACTION_XY')

    @mock.patch.object(nlo.NodeLock, "release")
    def test_node_lock_release(self, mock_release):
        actual = lockm.node_lock_release('C', 'A')
        self.assertEqual(mock_release.return_value, actual)
        mock_release.assert_called_once_with('C', 'A')
