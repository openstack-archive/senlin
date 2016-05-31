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

import datetime
import mock
from oslo_config import cfg
from oslo_utils import timeutils

from senlin.engine import scheduler
from senlin.engine import senlin_lock as lockm
from senlin.objects import action as ao
from senlin.objects import cluster_lock as clo
from senlin.objects import node_lock as nlo
from senlin.objects import service as service_obj
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

    @mock.patch.object(lockm, 'is_engine_dead')
    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(ao.Action, 'mark_failed')
    @mock.patch.object(clo.ClusterLock, "acquire")
    @mock.patch.object(clo.ClusterLock, "steal")
    def test_cluster_lock_acquire_dead_owner(self, mock_steal, mock_acquire,
                                             mock_action_fail, mock_sleep,
                                             mock_dead):
        mock_dead.return_value = True
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC',
                                    'ACTION_ABC', 'ACTION_ABC']
        mock_steal.side_effect = ['ACTION_XYZ']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A', 'ACTION_XYZ',
                                         'NEW_ENGINE')

        self.assertTrue(res)
        self.assertEqual(4, mock_acquire.call_count)
        self.assertEqual(3, mock_sleep.call_count)
        mock_steal.assert_called_once_with('CLUSTER_A', 'ACTION_XYZ')
        mock_action_fail.assert_called_once_with(
            self.ctx, 'ACTION_ABC', mock.ANY,
            'Engine died when executing this action.')

    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(clo.ClusterLock, "acquire")
    def test_cluster_lock_acquire_with_retry(self, mock_acquire, mock_sleep):
        cfg.CONF.set_override('lock_retry_times', 5, enforce_type=True)
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_XYZ']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A', 'ACTION_XYZ')

        self.assertTrue(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        acquire_calls = [
            mock.call('CLUSTER_A', 'ACTION_XYZ', lockm.CLUSTER_SCOPE)
        ]
        mock_acquire.assert_has_calls(acquire_calls * 3)

    @mock.patch.object(lockm, 'is_engine_dead')
    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(clo.ClusterLock, "acquire")
    def test_cluster_lock_acquire_max_retries(self, mock_acquire, mock_sleep,
                                              mock_dead):
        cfg.CONF.set_override('lock_retry_times', 2, enforce_type=True)
        mock_dead.return_value = False
        mock_acquire.side_effect = [
            'ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC', 'ACTION_XYZ'
        ]

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A', 'ACTION_XYZ')

        self.assertFalse(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        self.assertEqual(2, mock_sleep.call_count)
        acquire_calls = [
            mock.call('CLUSTER_A', 'ACTION_XYZ', lockm.CLUSTER_SCOPE)
        ]
        mock_acquire.assert_has_calls(acquire_calls * 3)

    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(clo.ClusterLock, "acquire")
    @mock.patch.object(clo.ClusterLock, "steal")
    def test_cluster_lock_acquire_forced(self, mock_steal, mock_acquire,
                                         mock_sleep):
        cfg.CONF.set_override('lock_retry_times', 2, enforce_type=True)
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC']
        mock_steal.return_value = ['ACTION_XY']

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A',
                                         'ACTION_XY', forced=True)

        self.assertTrue(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        self.assertEqual(2, mock_sleep.call_count)
        acquire_calls = [
            mock.call('CLUSTER_A', 'ACTION_XY', lockm.CLUSTER_SCOPE)
        ]
        mock_acquire.assert_has_calls(acquire_calls * 3)
        mock_steal.assert_called_once_with('CLUSTER_A', 'ACTION_XY')

    @mock.patch.object(lockm, 'is_engine_dead')
    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(clo.ClusterLock, "acquire")
    @mock.patch.object(clo.ClusterLock, "steal")
    def test_cluster_lock_acquire_steal_failed(self, mock_steal, mock_acquire,
                                               mock_sleep, mock_dead):
        cfg.CONF.set_override('lock_retry_times', 2, enforce_type=True)
        mock_dead.return_value = False
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC']
        mock_steal.return_value = []

        res = lockm.cluster_lock_acquire(self.ctx, 'CLUSTER_A',
                                         'ACTION_XY', forced=True)

        self.assertFalse(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        self.assertEqual(2, mock_sleep.call_count)
        acquire_calls = [
            mock.call('CLUSTER_A', 'ACTION_XY', lockm.CLUSTER_SCOPE)
        ]
        mock_acquire.assert_has_calls(acquire_calls * 3)
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

    @mock.patch.object(lockm, 'is_engine_dead')
    @mock.patch.object(ao.Action, 'mark_failed')
    @mock.patch.object(nlo.NodeLock, "acquire")
    @mock.patch.object(nlo.NodeLock, "steal")
    def test_node_lock_acquire_dead_owner(self, mock_steal, mock_acquire,
                                          mock_action_fail, mock_dead):
        mock_dead.return_value = True
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC',
                                    'ACTION_ABC', 'ACTION_ABC']
        mock_steal.return_value = 'ACTION_XYZ'

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A', 'ACTION_XYZ',
                                      'NEW_ENGINE')

        self.assertTrue(res)
        self.assertEqual(4, mock_acquire.call_count)
        mock_steal.assert_called_once_with('NODE_A', 'ACTION_XYZ')
        mock_action_fail.assert_called_once_with(
            self.ctx, 'ACTION_ABC', mock.ANY,
            'Engine died when executing this action.')

    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(nlo.NodeLock, "acquire")
    def test_node_lock_acquire_with_retry(self, mock_acquire, mock_sleep):
        cfg.CONF.set_override('lock_retry_times', 5, enforce_type=True)
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_XYZ']

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A', 'ACTION_XYZ')
        self.assertTrue(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        acquire_calls = [mock.call('NODE_A', 'ACTION_XYZ')]
        mock_acquire.assert_has_calls(acquire_calls * 3)

    @mock.patch.object(lockm, 'is_engine_dead')
    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(nlo.NodeLock, "acquire")
    def test_node_lock_acquire_max_retries(self, mock_acquire, mock_sleep,
                                           mock_dead):
        cfg.CONF.set_override('lock_retry_times', 2, enforce_type=True)
        mock_dead.return_value = False
        mock_acquire.side_effect = [
            'ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC', 'ACTION_XYZ'
        ]

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A', 'ACTION_XYZ')

        self.assertFalse(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        self.assertEqual(2, mock_sleep.call_count)
        acquire_calls = [mock.call('NODE_A', 'ACTION_XYZ')]
        mock_acquire.assert_has_calls(acquire_calls * 3)

    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(nlo.NodeLock, "acquire")
    @mock.patch.object(nlo.NodeLock, "steal")
    def test_node_lock_acquire_forced(self, mock_steal, mock_acquire,
                                      mock_sleep):
        cfg.CONF.set_override('lock_retry_times', 2, enforce_type=True)
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC']
        mock_steal.return_value = 'ACTION_XY'

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A',
                                      'ACTION_XY', forced=True)

        self.assertTrue(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        self.assertEqual(2, mock_sleep.call_count)
        acquire_calls = [mock.call('NODE_A', 'ACTION_XY')]
        mock_acquire.assert_has_calls(acquire_calls * 3)
        mock_steal.assert_called_once_with('NODE_A', 'ACTION_XY')

    @mock.patch.object(ao.Action, 'get')
    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(nlo.NodeLock, "acquire")
    @mock.patch.object(nlo.NodeLock, "steal")
    def test_node_lock_acquire_steal_failed(self, mock_steal, mock_acquire,
                                            mock_sleep, mock_get):
        cfg.CONF.set_override('lock_retry_times', 2, enforce_type=True)
        mock_get.return_value = mock.Mock(owner='ENGINE')
        mock_acquire.side_effect = ['ACTION_ABC', 'ACTION_ABC', 'ACTION_ABC']
        mock_steal.return_value = None

        res = lockm.node_lock_acquire(self.ctx, 'NODE_A',
                                      'ACTION_XY', forced=True)

        self.assertFalse(res)
        sleep_calls = [mock.call(cfg.CONF.lock_retry_interval)]
        mock_sleep.assert_has_calls(sleep_calls * 2)
        self.assertEqual(2, mock_sleep.call_count)
        acquire_calls = [mock.call('NODE_A', 'ACTION_XY')]
        mock_acquire.assert_has_calls(acquire_calls * 3)
        mock_steal.assert_called_once_with('NODE_A', 'ACTION_XY')

    @mock.patch.object(nlo.NodeLock, "release")
    def test_node_lock_release(self, mock_release):
        actual = lockm.node_lock_release('C', 'A')
        self.assertEqual(mock_release.return_value, actual)
        mock_release.assert_called_once_with('C', 'A')


class SenlinLockEnginCheckTest(base.SenlinTestCase):

    def setUp(self):
        super(SenlinLockEnginCheckTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(service_obj.Service, 'get')
    def test_engine_is_none(self, mock_service):
        mock_service.return_value = None
        self.assertTrue(lockm.is_engine_dead(self.ctx, 'fake_engine_id'))
        mock_service.assert_called_once_with(self.ctx, 'fake_engine_id')

    @mock.patch.object(service_obj.Service, 'get')
    def test_engine_is_dead(self, mock_service):
        delta = datetime.timedelta(seconds=3 * cfg.CONF.periodic_interval)
        update_time = timeutils.utcnow(True) - delta
        mock_service.return_value = mock.Mock(updated_at=update_time)
        self.assertTrue(lockm.is_engine_dead(self.ctx, 'fake_engine_id'))
        mock_service.assert_called_once_with(self.ctx, 'fake_engine_id')

    @mock.patch.object(service_obj.Service, 'get')
    def test_engine_is_alive(self, mock_svc):
        mock_svc.return_value = mock.Mock(updated_at=timeutils.utcnow(True))
        self.assertFalse(lockm.is_engine_dead(self.ctx, 'fake_engine_id'))
        mock_svc.assert_called_once_with(self.ctx, 'fake_engine_id')
