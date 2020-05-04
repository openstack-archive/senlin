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
from unittest import mock

from oslo_config import cfg
from oslo_context import context as oslo_context
import oslo_messaging
from oslo_service import threadgroup
from oslo_utils import uuidutils
from osprofiler import profiler

from senlin.common import consts
from senlin.common import messaging
from senlin.db import api as db_api
from senlin.engine.actions import base as actionm
from senlin.engine import dispatcher
from senlin.engine import service
from senlin.objects import service as service_obj
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class DummyThread(object):
    def __init__(self, function, *args, **kwargs):
        self.function = function


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
        return DummyThread(func)

    def stop(self, graceful=False):
        pass

    def wait(self):
        pass


class TestEngine(base.SenlinTestCase):
    def setUp(self):
        super(TestEngine, self).setUp()
        self.context = utils.dummy_context()

        self.service_id = '4db0a14c-dc10-4131-8ed6-7573987ce9b0'
        self.tg = mock.Mock()
        self.topic = consts.ENGINE_TOPIC

        self.tg = mock.Mock()
        self.svc = service.EngineService('HOST', self.topic)
        self.svc.service_id = self.service_id
        self.svc.tg = self.tg

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers(self, mock_service_init):
        service.EngineService('HOST', self.topic)

        mock_service_init.assert_called_once_with(1000)

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers_override(self, mock_service_init):
        cfg.CONF.set_override('threads', 100, group='engine')

        service.EngineService('HOST', self.topic)

        mock_service_init.assert_called_once_with(100)

    @mock.patch('oslo_service.service.Service.__init__')
    def test_service_thread_numbers_override_legacy(self, mock_service_init):
        cfg.CONF.set_override('scheduler_thread_pool_size', 101)

        service.EngineService('HOST', self.topic)

        mock_service_init.assert_called_once_with(101)

    def test_init(self):
        self.assertEqual(self.service_id, self.svc.service_id)
        self.assertEqual(self.tg, self.svc.tg)
        self.assertEqual(self.topic, self.svc.topic)

    @mock.patch.object(uuidutils, 'generate_uuid')
    @mock.patch.object(oslo_messaging, 'get_rpc_server')
    @mock.patch.object(service_obj.Service, 'create')
    def test_service_start(self, mock_service_create, mock_rpc_server,
                           mock_uuid):
        service_uuid = '4db0a14c-dc10-4131-8ed6-7573987ce9b1'
        mock_uuid.return_value = service_uuid

        self.svc.start()

        mock_uuid.assert_called_once()
        mock_service_create.assert_called_once()
        self.svc.server.start.assert_called_once()

        self.assertEqual(service_uuid, self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'delete')
    def test_service_stop(self, mock_delete):
        self.svc.server = mock.Mock()

        self.svc.stop()

        self.svc.server.stop.assert_called_once()
        self.svc.server.wait.assert_called_once()

        mock_delete.assert_called_once_with(self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'delete')
    def test_service_stop_not_yet_started(self, mock_delete):
        self.svc.server = None

        self.svc.stop()

        mock_delete.assert_called_once_with(self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'update')
    def test_service_manage_report_update(self, mock_update):
        mock_update.return_value = mock.Mock()
        self.svc.service_manage_report()
        mock_update.assert_called_once_with(mock.ANY,
                                            self.svc.service_id)

    @mock.patch.object(service_obj.Service, 'update')
    def test_service_manage_report_with_exception(self, mock_update):
        mock_update.side_effect = Exception('blah')
        self.svc.service_manage_report()
        self.assertEqual(mock_update.call_count, 1)

    def test_listening(self):
        self.assertTrue(self.svc.listening(self.context))

    @mock.patch.object(oslo_context, 'get_current')
    @mock.patch.object(messaging, 'get_rpc_client')
    def test_notify_broadcast(self, mock_rpc, mock_get_current):
        cfg.CONF.set_override('host', 'HOSTNAME')
        fake_ctx = mock.Mock()
        mock_get_current.return_value = fake_ctx
        mock_rpc.return_value = mock.Mock()

        dispatcher.notify('METHOD')

        mock_rpc.assert_called_once_with(consts.ENGINE_TOPIC, 'HOSTNAME')
        mock_client = mock_rpc.return_value
        mock_client.prepare.assert_called_once_with(fanout=True)

        mock_context = mock_client.prepare.return_value
        mock_context.cast.assert_called_once_with(fake_ctx, 'METHOD')

    @mock.patch.object(oslo_context, 'get_current')
    @mock.patch.object(messaging, 'get_rpc_client')
    def test_notify_single_server(self, mock_rpc, mock_get_current):
        cfg.CONF.set_override('host', 'HOSTNAME')
        fake_ctx = mock.Mock()
        mock_get_current.return_value = fake_ctx
        mock_rpc.return_value = mock.Mock()

        result = dispatcher.notify('METHOD', 'FAKE_ENGINE')

        self.assertTrue(result)
        mock_rpc.assert_called_once_with(consts.ENGINE_TOPIC, 'HOSTNAME')
        mock_client = mock_rpc.return_value
        mock_client.prepare.assert_called_once_with(server='FAKE_ENGINE')

        mock_context = mock_client.prepare.return_value
        mock_context.cast.assert_called_once_with(fake_ctx, 'METHOD')

    @mock.patch.object(messaging, 'get_rpc_client')
    def test_notify_timeout(self, mock_rpc):
        cfg.CONF.set_override('host', 'HOSTNAME')
        mock_rpc.return_value = mock.Mock()
        mock_client = mock_rpc.return_value
        mock_context = mock_client.prepare.return_value
        mock_context.cast.side_effect = oslo_messaging.MessagingTimeout

        result = dispatcher.notify('METHOD')

        self.assertFalse(result)
        mock_rpc.assert_called_once_with(consts.ENGINE_TOPIC, 'HOSTNAME')
        mock_client.prepare.assert_called_once_with(fanout=True)

        mock_context.cast.assert_called_once_with(mock.ANY, 'METHOD')

    @mock.patch.object(profiler, 'get')
    def test_serialize_profile_info(self, mock_profiler_get):
        mock_profiler_get.return_value = None

        self.assertIsNone(self.svc._serialize_profile_info())

    @mock.patch.object(profiler, 'get')
    def test_serialize_profile_info_with_profile(self, mock_profiler_get):
        mock_result = mock.Mock()
        mock_result.hmac_key = 'hmac_key'
        mock_result.get_base_id.return_value = 'get_base_id'
        mock_result.get_id.return_value = 'get_id'

        mock_profiler_get.return_value = mock_result
        result = self.svc._serialize_profile_info()

        self.assertEqual(
            {
                'base_id': 'get_base_id',
                'hmac_key': 'hmac_key',
                'parent_id': 'get_id'
            },
            result
        )

    @mock.patch.object(profiler, 'init')
    def test_start_with_trace(self, mock_profiler_init):
        self.assertIsNotNone(
            self.svc._start_with_trace(
                self.context, {'hmac_key': mock.Mock()}, mock.Mock()
            )
        )


class DispatcherActionTest(base.SenlinTestCase):
    def setUp(self):
        super(DispatcherActionTest, self).setUp()
        self.context = utils.dummy_context()
        self.fake_tg = DummyThreadGroup()

        self.mock_tg = self.patchobject(threadgroup, 'ThreadGroup')
        self.mock_tg.return_value = self.fake_tg

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    @mock.patch.object(db_api, 'action_acquire')
    def test_start_action(self, mock_action_acquire,
                          mock_action_acquire_1st):
        action = mock.Mock()
        action.id = '0123'
        mock_action_acquire.return_value = action
        mock_action_acquire_1st.return_value = None

        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.start_action('4567', '0123')

        self.mock_tg.add_thread.assert_called_once_with(
            svc._start_with_trace,
            oslo_context.get_current(),
            None, actionm.ActionProc,
            svc.db_session, '0123'
        )

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    def test_start_action_no_action_id(self, mock_acquire_action):
        mock_action = mock.Mock()
        mock_action.id = '0123'
        mock_action.action = 'CLUSTER_CREATE'
        mock_acquire_action.side_effect = [mock_action, None]

        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.start_action('4567')

        self.mock_tg.add_thread.assert_called_once_with(
            svc._start_with_trace,
            oslo_context.get_current(),
            None, actionm.ActionProc,
            svc.db_session, '0123'
        )

    @mock.patch.object(service, 'sleep')
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
        cfg.CONF.set_override('max_actions_per_batch', 1)
        cfg.CONF.set_override('batch_interval', 2)

        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.start_action('4567')

        mock_sleep.assert_called_once_with(2)
        self.assertEqual(self.mock_tg.add_thread.call_count, 3)

    @mock.patch.object(service, 'sleep')
    @mock.patch.object(db_api, 'action_acquire_first_ready')
    def test_start_action_multiple_batches(self, mock_acquire_action,
                                           mock_sleep):
        action_types = ['NODE_CREATE', 'NODE_DELETE']
        actions = []
        for index in range(10):
            mock_action = mock.Mock()
            mock_action.id = 'ID%d' % (index + 1)
            mock_action.action = action_types[index % 2]
            actions.append(mock_action)

        # Add a None at the end to end the process.
        actions.insert(len(actions), None)

        mock_acquire_action.side_effect = actions
        cfg.CONF.set_override('max_actions_per_batch', 3)
        cfg.CONF.set_override('batch_interval', 5)

        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.start_action(self.context)

        self.assertEqual(mock_sleep.call_count, 3)
        self.assertEqual(self.mock_tg.add_thread.call_count, 10)

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    @mock.patch.object(db_api, 'action_acquire')
    def test_start_action_failed_locking_action(self, mock_acquire_action,
                                                mock_acquire_action_1st):
        mock_acquire_action.return_value = None
        mock_acquire_action_1st.return_value = None

        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        res = svc.start_action(self.context, '0123')
        self.assertIsNone(res)

    @mock.patch.object(db_api, 'action_acquire_first_ready')
    def test_start_action_no_action_ready(self, mock_acquire_action):
        mock_acquire_action.return_value = None

        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        res = svc.start_action('4567')
        self.assertIsNone(res)

    def test_cancel_action(self):
        mock_action = mock.Mock()
        mock_load = self.patchobject(actionm.Action, 'load',
                                     return_value=mock_action)
        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.cancel_action(self.context, 'action0123')

        mock_load.assert_called_once_with(svc.db_session, 'action0123',
                                          project_safe=False)
        mock_action.signal.assert_called_once_with(mock_action.SIG_CANCEL)

    def test_suspend_action(self):
        mock_action = mock.Mock()
        mock_load = self.patchobject(actionm.Action, 'load',
                                     return_value=mock_action)
        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.suspend_action(self.context, 'action0123')

        mock_load.assert_called_once_with(svc.db_session, 'action0123',
                                          project_safe=False)
        mock_action.signal.assert_called_once_with(mock_action.SIG_SUSPEND)

    def test_resume_action(self):
        mock_action = mock.Mock()
        mock_load = self.patchobject(actionm.Action, 'load',
                                     return_value=mock_action)
        svc = service.EngineService('HOST', 'TOPIC')
        svc.tg = self.mock_tg
        svc.resume_action(self.context, 'action0123')

        mock_load.assert_called_once_with(svc.db_session, 'action0123',
                                          project_safe=False)
        mock_action.signal.assert_called_once_with(mock_action.SIG_RESUME)

    def test_sleep(self):
        mock_sleep = self.patchobject(eventlet, 'sleep')
        service.sleep(1)
        mock_sleep.assert_called_once_with(1)
