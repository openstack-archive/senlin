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

import eventlet
import mock
from oslo_config import cfg
from oslo_context import context as oslo_context
from oslo_service import threadgroup

from senlin.db import api as db_api
from senlin.engine.actions import base as actionm
from senlin.engine import scheduler
from senlin.tests.unit.common import base


class DummyThread(object):

    def __init__(self, function, *args, **kwargs):
        self.function = function

    def link(self, callback, *args):
        callback(self, *args)


class DummyThreadGroup(object):

    def __init__(self):
        self.threads = []

    def add_timer(self, interval, callback, initial_delay=None,
                  *args, **kwargs):
        self.threads.append(callback)

    def stop_timers(self):
        pass

    def add_thread(self, callback, cnxt, trace, func, *args, **kwargs):
        # callback here is _start_with_trace, func is the 'real' callback
        self.threads.append(func)
        return DummyThread()

    def stop(self, graceful=False):
        pass

    def wait(self):
        pass


class SchedulerTest(base.SenlinTestCase):

    def setUp(self):
        super(SchedulerTest, self).setUp()
        self.fake_tg = DummyThreadGroup()

        self.mock_tg = self.patchobject(threadgroup, 'ThreadGroup')
        self.mock_tg.return_value = self.fake_tg

    def test_create(self):
        tgm = scheduler.ThreadGroupManager()
        self.assertEqual({}, tgm.workers)

        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group
        tgm = scheduler.ThreadGroupManager()
        mock_group.add_timer.assert_called_once_with(
            cfg.CONF.periodic_interval,
            tgm._service_task)

    def test_start(self):
        def f():
            pass

        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group

        tgm = scheduler.ThreadGroupManager()
        tgm.start(f)

        mock_group.add_thread.assert_called_once_with(
            tgm._start_with_trace,
            oslo_context.get_current(),
            None, f)

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    @mock.patch.object(db_api, 'action_acquire')
    def test_start_action(self, mock_action_acquire,
                          mock_action_acquire_1st):
        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group
        action = mock.Mock()
        action.id = '0123'
        mock_action_acquire.return_value = action
        mock_action_acquire_1st.return_value = None

        tgm = scheduler.ThreadGroupManager()
        tgm.start_action('4567', '0123')

        mock_group.add_thread.assert_called_once_with(
            tgm._start_with_trace,
            oslo_context.get_current(),
            None, actionm.ActionProc,
            tgm.db_session, '0123')
        mock_thread = mock_group.add_thread.return_value
        self.assertEqual(mock_thread, tgm.workers['0123'])
        mock_thread.link.assert_called_once_with(mock.ANY, '0123')

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    def test_start_action_no_action_id(self, mock_acquire_action):
        mock_action = mock.Mock()
        mock_action.id = '0123'
        mock_action.action = 'CLUSTER_CREATE'
        mock_acquire_action.side_effect = [mock_action, None]
        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group

        tgm = scheduler.ThreadGroupManager()
        tgm.start_action('4567')

        mock_group.add_thread.assert_called_once_with(
            tgm._start_with_trace,
            oslo_context.get_current(),
            None, actionm.ActionProc,
            tgm.db_session, '0123')
        mock_thread = mock_group.add_thread.return_value
        self.assertEqual(mock_thread, tgm.workers['0123'])
        mock_thread.link.assert_called_once_with(mock.ANY, '0123')

    @mock.patch.object(scheduler, 'sleep')
    @mock.patch.object(db_api, 'action_acquire_first_ready')
    def test_start_action_batch_control(self, mock_acquire_action, mock_sleep):
        mock_action1 = mock.Mock()
        mock_action1.id = 'ID1'
        mock_action1.action = 'NODE_CREATE'
        mock_action2 = mock.Mock()
        mock_action2.id = 'ID2'
        mock_action2.action = 'CLUSTER_CREATE'
        mock_action3 = mock.Mock()
        mock_action3.id = 'ID3'
        mock_action3.action = 'NODE_DELETE'
        mock_acquire_action.side_effect = [mock_action1, mock_action2,
                                           mock_action3, None]
        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group
        cfg.CONF.set_override('max_actions_per_batch', 1)
        cfg.CONF.set_override('batch_interval', 3)

        tgm = scheduler.ThreadGroupManager()
        tgm.start_action('4567')

        mock_sleep.assert_called_once_with(3)

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    @mock.patch.object(db_api, 'action_acquire')
    def test_start_action_failed_locking_action(self, mock_acquire_action,
                                                mock_acquire_action_1st):
        mock_acquire_action.return_value = None
        mock_acquire_action_1st.return_value = None
        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group

        tgm = scheduler.ThreadGroupManager()
        res = tgm.start_action('4567', '0123')
        self.assertIsNone(res)

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    def test_start_action_no_action_ready(self, mock_acquire_action):
        mock_acquire_action.return_value = None
        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group

        tgm = scheduler.ThreadGroupManager()
        res = tgm.start_action('4567')
        self.assertIsNone(res)

    def test_cancel_action(self):
        mock_action = mock.Mock()
        mock_load = self.patchobject(actionm.Action, 'load',
                                     return_value=mock_action)
        tgm = scheduler.ThreadGroupManager()
        tgm.cancel_action('action0123')

        mock_load.assert_called_once_with(tgm.db_session, 'action0123',
                                          project_safe=False)
        mock_action.signal.assert_called_once_with(mock_action.SIG_CANCEL)

    def test_suspend_action(self):
        mock_action = mock.Mock()
        mock_load = self.patchobject(actionm.Action, 'load',
                                     return_value=mock_action)
        tgm = scheduler.ThreadGroupManager()
        tgm.suspend_action('action0123')

        mock_load.assert_called_once_with(tgm.db_session, 'action0123',
                                          project_safe=False)
        mock_action.signal.assert_called_once_with(mock_action.SIG_SUSPEND)

    def test_resume_action(self):
        mock_action = mock.Mock()
        mock_load = self.patchobject(actionm.Action, 'load',
                                     return_value=mock_action)
        tgm = scheduler.ThreadGroupManager()
        tgm.resume_action('action0123')

        mock_load.assert_called_once_with(tgm.db_session, 'action0123',
                                          project_safe=False)
        mock_action.signal.assert_called_once_with(mock_action.SIG_RESUME)

    def test_add_timer(self):
        def f():
            pass

        tgm = scheduler.ThreadGroupManager()
        tgm.add_timer(10, f)

        # The first element is the '_service_task'
        self.assertEqual(2, len(self.fake_tg.threads))
        self.assertEqual(f, self.fake_tg.threads[1])

    def test_stop_timer(self):
        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group

        tgm = scheduler.ThreadGroupManager()
        tgm.stop_timers()
        mock_group.stop_timers.assert_called_once_with()

    def test_stop(self):
        def f():
            pass

        mock_group = mock.Mock()
        self.mock_tg.return_value = mock_group
        tgm = scheduler.ThreadGroupManager()
        mock_group.threads = [
            DummyThread(tgm._service_task),
            DummyThread(f)
        ]
        tgm.start(f)

        tgm.stop()

        mock_group.stop.assert_called_once_with(False)
        mock_group.wait.assert_called_once_with()

    def test_reschedule(self):
        action = mock.Mock()
        action.id = '0123'
        mock_sleep = self.patchobject(eventlet, 'sleep')

        scheduler.reschedule(action.id)
        mock_sleep.assert_called_once_with(1)
        mock_sleep.reset_mock()

        scheduler.reschedule(action.id, None)
        self.assertEqual(0, mock_sleep.call_count)

    def test_sleep(self):
        mock_sleep = self.patchobject(eventlet, 'sleep')
        scheduler.sleep(1)
        mock_sleep.assert_called_once_with(1)
