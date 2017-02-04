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

import copy

import mock
from oslo_config import cfg

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging
from senlin.engine import health_manager as hm
from senlin.objects import cluster as obj_cluster
from senlin.objects import health_registry as hr
from senlin.objects import node as obj_node
from senlin.objects import profile as obj_profile
from senlin.objects.requests import nodes as vorn
from senlin.rpc import client as rpc_client
from senlin.tests.unit.common import base


@mock.patch('oslo_messaging.NotificationFilter')
class TestNovaNotificationEndpoint(base.SenlinTestCase):

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_init(self, mock_rpc, mock_filter):
        x_filter = mock_filter.return_value
        event_map = {
            'compute.instance.delete.end': 'DELETE',
            'compute.instance.pause.end': 'PAUSE',
            'compute.instance.power_off.end': 'POWER_OFF',
            'compute.instance.rebuild.error': 'REBUILD',
            'compute.instance.shutdown.end': 'SHUTDOWN',
            'compute.instance.soft_delete.end': 'SOFT_DELETE',
        }

        obj = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER')

        mock_filter.assert_called_once_with(
            publisher_id='^compute.*',
            event_type='^compute\.instance\..*',
            context={'project_id': '^PROJECT$'})
        mock_rpc.assert_called_once_with()
        self.assertEqual(x_filter, obj.filter_rule)
        self.assertEqual(mock_rpc.return_value, obj.rpc)
        for e in event_map:
            self.assertIn(e, obj.VM_FAILURE_EVENTS)
            self.assertEqual(event_map[e], obj.VM_FAILURE_EVENTS[e])
        self.assertEqual('PROJECT', obj.project_id)
        self.assertEqual('CLUSTER', obj.cluster_id)

    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info(self, mock_rpc, mock_context, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {
            'metadata': {
                'cluster_id': 'CLUSTER_ID',
                'cluster_node_id': 'FAKE_NODE',
                'cluster_node_index': '123',
            },
            'instance_id': 'PHYSICAL_ID',
            'user_id': 'USER',
            'state': 'shutoff',
        }
        metadata = {'timestamp': 'TIMESTAMP'}
        call_ctx = mock.Mock()
        mock_context.return_value = call_ctx

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        x_rpc.call.assert_called_once_with(call_ctx, 'node_recover', mock.ANY)
        req = x_rpc.call.call_args[0][2]
        self.assertIsInstance(req, vorn.NodeRecoverRequest)
        self.assertEqual('FAKE_NODE', req.identity)
        expected_params = {
            'event': 'DELETE',
            'state': 'shutoff',
            'instance_id': 'PHYSICAL_ID',
            'timestamp': 'TIMESTAMP',
            'publisher': 'PUBLISHER',
        }
        self.assertEqual(expected_params, req.params)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_metadata(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {'metadata': {}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_cluster_in_metadata(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {'metadata': {'foo': 'bar'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_cluster_id_not_match(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {'metadata': {'cluster_id': 'FOOBAR'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_event_type_not_interested(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {'metadata': {'cluster_id': 'CLUSTER_ID'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.start',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_node_id(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {'metadata': {'cluster_id': 'CLUSTER_ID'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_default_values(self, mock_rpc, mock_context, mock_filter):
        x_rpc = mock_rpc.return_value
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID')
        ctx = mock.Mock()
        payload = {
            'metadata': {
                'cluster_id': 'CLUSTER_ID',
                'cluster_node_id': 'NODE_ID'
            },
            'user_id': 'USER',
        }
        metadata = {'timestamp': 'TIMESTAMP'}
        call_ctx = mock.Mock()
        mock_context.return_value = call_ctx

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        x_rpc.call.assert_called_once_with(call_ctx, 'node_recover', mock.ANY)
        req = x_rpc.call.call_args[0][2]
        self.assertIsInstance(req, vorn.NodeRecoverRequest)
        self.assertEqual('NODE_ID', req.identity)
        expected_params = {
            'event': 'DELETE',
            'state': 'Unknown',
            'instance_id': 'Unknown',
            'timestamp': 'TIMESTAMP',
            'publisher': 'PUBLISHER',
        }
        self.assertEqual(expected_params, req.params)


@mock.patch('senlin.engine.health_manager.NovaNotificationEndpoint')
@mock.patch('oslo_messaging.Target')
@mock.patch('oslo_messaging.get_notification_transport')
@mock.patch('oslo_messaging.get_notification_listener')
class TestListenerProc(base.SenlinTestCase):

    def test_listener_proc_nova(self, mock_listener, mock_transport,
                                mock_target, mock_endpoint):
        cfg.CONF.set_override('nova_control_exchange', 'FAKE_EXCHANGE',
                              group='health_manager', enforce_type=True)

        x_listener = mock.Mock()
        mock_listener.return_value = x_listener
        x_transport = mock.Mock()
        mock_transport.return_value = x_transport
        x_target = mock.Mock()
        mock_target.return_value = x_target
        x_endpoint = mock.Mock()
        mock_endpoint.return_value = x_endpoint

        res = hm.ListenerProc('FAKE_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID')

        self.assertIsNone(res)
        mock_transport.assert_called_once_with(cfg.CONF)
        mock_target.assert_called_once_with(topic="versioned_notifications",
                                            exchange='FAKE_EXCHANGE')
        mock_endpoint.assert_called_once_with('PROJECT_ID', 'CLUSTER_ID')
        mock_listener.assert_called_once_with(
            x_transport, [x_target], [x_endpoint],
            executor='threading', pool="senlin-listeners")
        x_listener.start.assert_called_once_with()

    def test_listener_proc_others(self, mock_listener, mock_transport,
                                  mock_target, mock_endpoint):
        x_transport = mock.Mock()
        mock_transport.return_value = x_transport

        res = hm.ListenerProc('BOGUS', 'PROJECT_ID', 'CLUSTER_ID')

        self.assertIsNone(res)

        mock_transport.assert_called_once_with(cfg.CONF)
        self.assertFalse(mock_listener.called)
        self.assertFalse(mock_target.called)
        self.assertFalse(mock_endpoint.called)


class TestHealthManager(base.SenlinTestCase):

    def setUp(self):
        super(TestHealthManager, self).setUp()

        mock_eng = mock.Mock()
        mock_eng.engine_id = 'ENGINE_ID'
        topic = consts.HEALTH_MANAGER_TOPIC
        version = consts.RPC_API_VERSION
        self.hm = hm.HealthManager(mock_eng, topic, version)

    def test_init(self):
        self.assertEqual('ENGINE_ID', self.hm.engine_id)
        self.assertIsNotNone(self.hm.TG)
        self.assertIsNotNone(self.hm.rpc_client)
        self.assertEqual(consts.HEALTH_MANAGER_TOPIC, self.hm.topic)
        self.assertEqual(consts.RPC_API_VERSION, self.hm.version)
        self.assertEqual(0, len(self.hm.rt['registries']))

    @mock.patch.object(hr.HealthRegistry, 'claim')
    def test__load_runtime_registry(self, mock_claim):
        mock_claim.return_value = [
            mock.Mock(cluster_id='CID1',
                      check_type=consts.NODE_STATUS_POLLING,
                      interval=12,
                      params={'k1': 'v1'},
                      enabled=True),
            mock.Mock(cluster_id='CID2',
                      check_type=consts.NODE_STATUS_POLLING,
                      interval=34,
                      params={'k2': 'v2'},
                      enabled=False),
            mock.Mock(cluster_id='CID3',
                      check_type='UNKNOWN_CHECK_TYPE',
                      interval=56,
                      params={'k3': 'v3'}),
        ]

        timer1 = mock.Mock()
        timer2 = mock.Mock()
        mock_add_timer = self.patchobject(self.hm.TG, 'add_timer',
                                          side_effect=[timer1, timer2])

        # do it
        self.hm._load_runtime_registry()

        # assertions
        mock_claim.assert_called_once_with(self.hm.ctx, self.hm.engine_id)
        mock_calls = [
            mock.call(12, self.hm._poll_cluster, None, 'CID1', 12),
            mock.call(34, self.hm._poll_cluster, None, 'CID2', 34)
        ]
        mock_add_timer.assert_has_calls(mock_calls)
        self.assertEqual(2, len(self.hm.registries))
        self.assertEqual(
            {
                'cluster_id': 'CID1',
                'check_type': consts.NODE_STATUS_POLLING,
                'interval': 12,
                'params': {'k1': 'v1'},
                'timer': timer1,
                'enabled': True,
            },
            self.hm.registries[0])
        self.assertEqual(
            {
                'cluster_id': 'CID2',
                'check_type': consts.NODE_STATUS_POLLING,
                'interval': 34,
                'params': {'k2': 'v2'},
                'timer': timer2,
                'enabled': False,
            },
            self.hm.registries[1])

    @mock.patch.object(obj_node.Node, 'get_all')
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster(self, mock_rpc, mock_ctx, mock_sctx, mock_get,
                           mock_wait, mock_nodes):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster
        mock_sctx.return_value = {'user': 'USER_ID',
                                  'project': 'PROJECT_ID', }
        service_ctx = mock_sctx.return_value
        ctx = mock.Mock(user=service_ctx['user'],
                        project=service_ctx['project'])
        mock_ctx.return_value = ctx
        mock_wait.return_value = (True, "")
        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        mock_nodes.return_value = [x_node]
        x_action_check = {'action': 'CHECK_ID'}
        x_action_recover = {'action': 'RECOVER_ID'}
        mock_rpc.side_effect = [x_action_check, x_action_recover]

        # do it
        self.hm._poll_cluster('CLUSTER_ID', 456)

        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        mock_sctx.assert_called_once_with(user=x_cluster.user,
                                          project=x_cluster.project)
        mock_ctx.assert_called_once_with(service_ctx)
        self.assertEqual('USER_ID', ctx.user)
        self.assertEqual('PROJECT_ID', ctx.project)
        mock_rpc.assert_has_calls([
            mock.call(ctx, 'cluster_check', mock.ANY),
            mock.call(ctx, 'node_recover', mock.ANY)
        ])
        mock_wait.assert_called_once_with(ctx, "CHECK_ID", 456)

    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster_not_found(self, mock_check, mock_get):
        mock_get.return_value = None

        # do it
        self.hm._poll_cluster('CLUSTER_ID', 123)

        self.assertEqual(0, mock_check.call_count)

    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster_failed_check_rpc(self, mock_check, mock_get,
                                            mock_ctx, mock_sctx):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster
        mock_sctx.return_value = {'user': 'USER_ID',
                                  'project': 'PROJECT_ID', }
        service_ctx = mock_sctx.return_value
        ctx = mock.Mock(user=service_ctx['user'],
                        project=service_ctx['project'])
        mock_ctx.return_value = ctx
        mock_check.side_effect = Exception("boom")

        # do it
        self.hm._poll_cluster('CLUSTER_ID', 123)

        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        mock_sctx.assert_called_once_with(user=x_cluster.user,
                                          project=x_cluster.project)
        mock_ctx.assert_called_once_with(service_ctx)
        self.assertEqual('USER_ID', ctx.user)
        self.assertEqual('PROJECT_ID', ctx.project)
        mock_check.assert_called_once_with(ctx, 'cluster_check', mock.ANY)

    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster_failed_wait(self, mock_rpc, mock_ctx, mock_sctx,
                                       mock_get, mock_wait):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster
        mock_sctx.return_value = {'user': 'USER_ID',
                                  'project': 'PROJECT_ID', }
        service_ctx = mock_sctx.return_value
        ctx = mock.Mock(user=service_ctx['user'],
                        project=service_ctx['project'])
        mock_ctx.return_value = ctx
        mock_wait.return_value = (False, "bad")
        x_action_check = {'action': 'CHECK_ID'}
        mock_rpc.return_value = x_action_check

        # do it
        self.hm._poll_cluster('CLUSTER_ID', 456)

        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        mock_sctx.assert_called_once_with(user=x_cluster.user,
                                          project=x_cluster.project)
        mock_ctx.assert_called_once_with(service_ctx)
        self.assertEqual('USER_ID', ctx.user)
        self.assertEqual('PROJECT_ID', ctx.project)
        mock_rpc.assert_called_once_with(ctx, 'cluster_check', mock.ANY)
        mock_wait.assert_called_once_with(ctx, "CHECK_ID", 456)

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_nova(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('nova_control_exchange', 'FAKE_NOVA_EXCHANGE',
                              group='health_manager', enforce_type=True)
        x_listener = mock.Mock()
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread',
                                           return_value=x_listener)
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type_name='os.nova.server-1.0')
        mock_profile.return_value = x_profile

        # do it
        res = self.hm._add_listener('CLUSTER_ID')

        # assertions
        self.assertEqual(x_listener, res)
        mock_cluster.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.hm.ctx, 'PROFILE_ID',
                                             project_safe=False)
        mock_add_thread.assert_called_once_with(
            hm.ListenerProc, 'FAKE_NOVA_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID')

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_heat(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('heat_control_exchange', 'FAKE_HEAT_EXCHANGE',
                              group='health_manager', enforce_type=True)
        x_listener = mock.Mock()
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread',
                                           return_value=x_listener)
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type_name='os.heat.stack-1.0')
        mock_profile.return_value = x_profile

        # do it
        res = self.hm._add_listener('CLUSTER_ID')

        # assertions
        self.assertEqual(x_listener, res)
        mock_cluster.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.hm.ctx, 'PROFILE_ID',
                                             project_safe=False)
        mock_add_thread.assert_called_once_with(
            hm.ListenerProc, 'FAKE_HEAT_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID')

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_other_types(self, mock_cluster, mock_profile):
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread')
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type_name='other.types-1.0')
        mock_profile.return_value = x_profile

        # do it
        res = self.hm._add_listener('CLUSTER_ID')

        # assertions
        self.assertIsNone(res)
        mock_cluster.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.hm.ctx, 'PROFILE_ID',
                                             project_safe=False)
        self.assertFalse(mock_add_thread.called)

    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_cluster_not_found(self, mock_get):
        mock_get.return_value = None
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread')

        # do it
        res = self.hm._add_listener('CLUSTER_ID')

        # assertions
        self.assertIsNone(res)
        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        self.assertEqual(0, mock_add_thread.call_count)

    def test__start_check_for_polling(self):
        x_timer = mock.Mock()
        mock_add_timer = self.patchobject(self.hm.TG, 'add_timer',
                                          return_value=x_timer)

        entry = {
            'cluster_id': 'CCID',
            'interval': 12,
            'check_type': consts.NODE_STATUS_POLLING,
        }
        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['timer'] = x_timer
        self.assertEqual(expected, res)
        mock_add_timer.assert_called_once_with(12, self.hm._poll_cluster, None,
                                               'CCID', 12)

    def test__start_check_for_listening(self):
        x_listener = mock.Mock()
        mock_add_listener = self.patchobject(self.hm, '_add_listener',
                                             return_value=x_listener)

        entry = {
            'cluster_id': 'CCID',
            'check_type': consts.LIFECYCLE_EVENTS,
        }
        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['listener'] = x_listener
        self.assertEqual(expected, res)
        mock_add_listener.assert_called_once_with('CCID')

    def test__start_check_for_listening_failed(self):
        mock_add_listener = self.patchobject(self.hm, '_add_listener',
                                             return_value=None)

        entry = {
            'cluster_id': 'CCID',
            'check_type': consts.LIFECYCLE_EVENTS,
        }
        res = self.hm._start_check(entry)

        self.assertIsNone(res)
        mock_add_listener.assert_called_once_with('CCID')

    def test__start_check_other_types(self):
        entry = {
            'cluster_id': 'CCID',
            'check_type': 'BOGUS TYPE',
        }
        res = self.hm._start_check(entry)

        self.assertIsNone(res)

    def test__stop_check_with_timer(self):
        x_timer = mock.Mock()
        entry = {'timer': x_timer}
        mock_timer_done = self.patchobject(self.hm.TG, 'timer_done')

        # do it
        res = self.hm._stop_check(entry)

        self.assertIsNone(res)
        x_timer.stop.assert_called_once_with()
        mock_timer_done.assert_called_once_with(x_timer)

    def test__stop_check_with_listener(self):
        x_thread = mock.Mock()
        entry = {'listener': x_thread}
        mock_thread_done = self.patchobject(self.hm.TG, 'thread_done')

        # do it
        res = self.hm._stop_check(entry)

        self.assertIsNone(res)
        x_thread.stop.assert_called_once_with()
        mock_thread_done.assert_called_once_with(x_thread)

    @mock.patch('oslo_messaging.Target')
    def test_start(self, mock_target):
        self.hm.TG = mock.Mock()
        target = mock.Mock()
        mock_target.return_value = target
        x_rpc_server = mock.Mock()
        mock_get_rpc = self.patchobject(messaging, 'get_rpc_server',
                                        return_value=x_rpc_server)
        x_timer = mock.Mock()
        mock_add_timer = self.patchobject(self.hm.TG, 'add_timer',
                                          return_value=x_timer)
        mock_load = self.patchobject(self.hm, '_load_runtime_registry')

        # do it
        self.hm.start()

        # assert
        mock_target.assert_called_once_with(server='ENGINE_ID',
                                            topic='engine-health-mgr',
                                            version=consts.RPC_API_VERSION)
        mock_get_rpc.assert_called_once_with(target, self.hm)
        x_rpc_server.start.assert_called_once_with()
        mock_add_timer.assert_called_once_with(cfg.CONF.periodic_interval,
                                               self.hm._dummy_task)
        mock_load.assert_called_once_with()

    @mock.patch.object(hr.HealthRegistry, 'create')
    def test_register_cluster(self, mock_reg_create):
        ctx = mock.Mock()
        timer = mock.Mock()
        mock_add_tm = self.patchobject(self.hm.TG, 'add_timer',
                                       return_value=timer)
        mock_poll = self.patchobject(self.hm, '_poll_cluster',
                                     return_value=mock.Mock())
        x_reg = mock.Mock(cluster_id='CLUSTER_ID',
                          check_type=consts.NODE_STATUS_POLLING,
                          interval=50, params={})
        mock_reg_create.return_value = x_reg

        self.hm.register_cluster(ctx,
                                 cluster_id='CLUSTER_ID',
                                 check_type=consts.NODE_STATUS_POLLING,
                                 interval=50, enabled=True)

        mock_reg_create.assert_called_once_with(
            ctx, 'CLUSTER_ID', consts.NODE_STATUS_POLLING, 50, {}, 'ENGINE_ID',
            enabled=True)
        mock_add_tm.assert_called_with(50, mock_poll, None, 'CLUSTER_ID', 50)
        self.assertEqual(1, len(self.hm.registries))

    @mock.patch.object(hm.HealthManager, '_stop_check')
    @mock.patch.object(hr.HealthRegistry, 'delete')
    def test_unregister_cluster(self, mock_delete, mock_stop):
        ctx = mock.Mock()
        timer = mock.Mock()
        registry = {
            'cluster_id': 'CLUSTER_ID',
            'check_type': 'NODE_STATUS_POLLING',
            'interval': 50,
            'params': {},
            'timer': timer,
            'enabled': True,
        }
        self.hm.rt['registries'] = [registry]

        self.hm.unregister_cluster(ctx, cluster_id='CLUSTER_ID')

        self.assertEqual(0, len(self.hm.registries))
        mock_stop.assert_called_once_with(registry)
        mock_delete.assert_called_once_with(ctx, 'CLUSTER_ID')

    @mock.patch.object(hr.HealthRegistry, 'update')
    @mock.patch.object(hm.HealthManager, '_start_check')
    def test_enable_cluster(self, mock_start, mock_update):
        ctx = mock.Mock()
        entry1 = {'cluster_id': 'FAKE_ID', 'enabled': False}
        entry2 = {'cluster_id': 'ANOTHER_CLUSTER', 'enabled': False}
        self.hm.rt['registries'] = [entry1, entry2]

        self.hm.enable_cluster(ctx, 'FAKE_ID')

        mock_start.assert_called_once_with(entry1)
        self.assertIn({'cluster_id': 'FAKE_ID', 'enabled': True},
                      self.hm.rt['registries'])
        mock_update.assert_called_once_with(ctx, 'FAKE_ID', {'enabled': True})

    @mock.patch.object(hr.HealthRegistry, 'update')
    @mock.patch.object(hm.HealthManager, '_stop_check')
    def test_disable_cluster(self, mock_stop, mock_update):
        ctx = mock.Mock()
        entry1 = {'cluster_id': 'FAKE_ID', 'enabled': True}
        entry2 = {'cluster_id': 'ANOTHER_CLUSTER', 'enabled': True}
        self.hm.rt['registries'] = [entry1, entry2]

        self.hm.disable_cluster(ctx, 'FAKE_ID')

        mock_stop.assert_called_once_with(entry1)
        self.assertIn({'cluster_id': 'FAKE_ID', 'enabled': False},
                      self.hm.rt['registries'])
        mock_update.assert_called_once_with(ctx, 'FAKE_ID', {'enabled': False})
