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
import time

import mock
from oslo_config import cfg
from oslo_utils import timeutils as tu

from senlin.common import consts
from senlin.common import context
from senlin.common import messaging
from senlin.engine import health_manager as hm
from senlin import objects
from senlin.objects import cluster as obj_cluster
from senlin.objects import health_registry as hr
from senlin.objects import node as obj_node
from senlin.objects import profile as obj_profile
from senlin.rpc import client as rpc_client
from senlin.tests.unit.common import base


class TestChaseUp(base.SenlinTestCase):

    def test_less_than_one_interval(self):
        start = tu.utcnow(True)
        # we assume that the delay before next line is < 5 seconds
        res = hm._chase_up(start, 5)

        self.assertTrue(res <= 5)

    def test_more_than_one_interval(self):
        start = tu.utcnow(True)
        time.sleep(2)

        # we assume that the delay before next line is < 5 seconds
        res = hm._chase_up(start, 1)

        self.assertTrue(res <= 1)


@mock.patch('oslo_messaging.NotificationFilter')
class TestNovaNotificationEndpoint(base.SenlinTestCase):

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_init(self, mock_rpc, mock_filter):
        x_filter = mock_filter.return_value
        event_map = {
            'compute.instance.pause.end': 'PAUSE',
            'compute.instance.power_off.end': 'POWER_OFF',
            'compute.instance.rebuild.error': 'REBUILD',
            'compute.instance.shutdown.end': 'SHUTDOWN',
            'compute.instance.soft_delete.end': 'SOFT_DELETE',
        }
        recover_action = {'operation': 'REBUILD'}
        obj = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER', recover_action)

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
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.shutdown.end',
                            payload, metadata)

        self.assertIsNone(res)
        x_rpc.call.assert_called_once_with(call_ctx, 'node_recover', mock.ANY)
        req = x_rpc.call.call_args[0][2]
        self.assertIsInstance(req, objects.NodeRecoverRequest)
        self.assertEqual('FAKE_NODE', req.identity)
        expected_params = {
            'event': 'SHUTDOWN',
            'state': 'shutoff',
            'instance_id': 'PHYSICAL_ID',
            'timestamp': 'TIMESTAMP',
            'publisher': 'PUBLISHER',
            'operation': 'REBUILD'
        }
        self.assertEqual(expected_params, req.params)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_metadata(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.NovaNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
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

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.shutdown.end',
                            payload, metadata)

        self.assertIsNone(res)
        x_rpc.call.assert_called_once_with(call_ctx, 'node_recover', mock.ANY)
        req = x_rpc.call.call_args[0][2]
        self.assertIsInstance(req, objects.NodeRecoverRequest)
        self.assertEqual('NODE_ID', req.identity)
        expected_params = {
            'event': 'SHUTDOWN',
            'state': 'Unknown',
            'instance_id': 'Unknown',
            'timestamp': 'TIMESTAMP',
            'publisher': 'PUBLISHER',
            'operation': 'REBUILD',
        }
        self.assertEqual(expected_params, req.params)


@mock.patch('oslo_messaging.NotificationFilter')
class TestHeatNotificationEndpoint(base.SenlinTestCase):

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_init(self, mock_rpc, mock_filter):
        x_filter = mock_filter.return_value
        event_map = {
            'orchestration.stack.delete.end': 'DELETE',
        }
        recover_action = {'operation': 'REBUILD'}
        obj = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER', recover_action)

        mock_filter.assert_called_once_with(
            publisher_id='^orchestration.*',
            event_type='^orchestration\.stack\..*',
            context={'project_id': '^PROJECT$'})
        mock_rpc.assert_called_once_with()
        self.assertEqual(x_filter, obj.filter_rule)
        self.assertEqual(mock_rpc.return_value, obj.rpc)
        for e in event_map:
            self.assertIn(e, obj.STACK_FAILURE_EVENTS)
            self.assertEqual(event_map[e], obj.STACK_FAILURE_EVENTS[e])
        self.assertEqual('PROJECT', obj.project_id)
        self.assertEqual('CLUSTER', obj.cluster_id)

    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info(self, mock_rpc, mock_context, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {
            'tags': {
                'cluster_id=CLUSTER_ID',
                'cluster_node_id=FAKE_NODE',
                'cluster_node_index=123',
            },
            'stack_identity': 'PHYSICAL_ID',
            'user_identity': 'USER',
            'state': 'DELETE_COMPLETE',
        }
        metadata = {'timestamp': 'TIMESTAMP'}
        call_ctx = mock.Mock()
        mock_context.return_value = call_ctx

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        x_rpc.call.assert_called_once_with(call_ctx, 'node_recover', mock.ANY)
        req = x_rpc.call.call_args[0][2]
        self.assertIsInstance(req, objects.NodeRecoverRequest)
        self.assertEqual('FAKE_NODE', req.identity)
        expected_params = {
            'event': 'DELETE',
            'state': 'DELETE_COMPLETE',
            'stack_id': 'PHYSICAL_ID',
            'timestamp': 'TIMESTAMP',
            'publisher': 'PUBLISHER',
            'operation': 'REBUILD',
        }
        self.assertEqual(expected_params, req.params)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_event_type_not_interested(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {'tags': {'cluster_id': 'CLUSTER_ID'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER',
                            'orchestration.stack.create.start',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_tag(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {'tags': None}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_empty_tag(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {'tags': []}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_cluster_in_tag(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {'tags': ['foo', 'bar']}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_no_node_in_tag(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {'tags': ['cluster_id=C1ID']}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_cluster_id_not_match(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {'tags': ['cluster_id=FOOBAR', 'cluster_node_id=N2']}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch('senlin.rpc.client.EngineClient')
    def test_info_default_values(self, mock_rpc, mock_context, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = hm.HeatNotificationEndpoint('PROJECT', 'CLUSTER_ID',
                                               recover_action)
        ctx = mock.Mock()
        payload = {
            'tags': [
                'cluster_id=CLUSTER_ID',
                'cluster_node_id=NODE_ID'
            ],
            'user_identity': 'USER',
        }
        metadata = {'timestamp': 'TIMESTAMP'}
        call_ctx = mock.Mock()
        mock_context.return_value = call_ctx

        res = endpoint.info(ctx, 'PUBLISHER', 'orchestration.stack.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        x_rpc.call.assert_called_once_with(call_ctx, 'node_recover', mock.ANY)
        req = x_rpc.call.call_args[0][2]
        self.assertIsInstance(req, objects.NodeRecoverRequest)
        self.assertEqual('NODE_ID', req.identity)
        expected_params = {
            'event': 'DELETE',
            'state': 'Unknown',
            'stack_id': 'Unknown',
            'timestamp': 'TIMESTAMP',
            'publisher': 'PUBLISHER',
            'operation': 'REBUILD',
        }
        self.assertEqual(expected_params, req.params)


@mock.patch('senlin.engine.health_manager.HeatNotificationEndpoint')
@mock.patch('senlin.engine.health_manager.NovaNotificationEndpoint')
@mock.patch('oslo_messaging.Target')
@mock.patch('oslo_messaging.get_notification_transport')
@mock.patch('oslo_messaging.get_notification_listener')
class TestListenerProc(base.SenlinTestCase):

    def test_listener_proc_nova(self, mock_listener, mock_transport,
                                mock_target, mock_novaendpoint,
                                mock_heatendpoint):
        cfg.CONF.set_override('nova_control_exchange', 'FAKE_EXCHANGE',
                              group='health_manager')

        x_listener = mock.Mock()
        mock_listener.return_value = x_listener
        x_transport = mock.Mock()
        mock_transport.return_value = x_transport
        x_target = mock.Mock()
        mock_target.return_value = x_target
        x_endpoint = mock.Mock()
        mock_novaendpoint.return_value = x_endpoint

        recover_action = {'operation': 'REBUILD'}
        res = hm.ListenerProc('FAKE_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID',
                              recover_action)

        self.assertIsNone(res)
        mock_transport.assert_called_once_with(cfg.CONF)
        mock_target.assert_called_once_with(topic="versioned_notifications",
                                            exchange='FAKE_EXCHANGE')
        mock_novaendpoint.assert_called_once_with('PROJECT_ID', 'CLUSTER_ID',
                                                  recover_action)
        mock_listener.assert_called_once_with(
            x_transport, [x_target], [x_endpoint],
            executor='threading', pool="senlin-listeners")
        x_listener.start.assert_called_once_with()

    def test_listener_proc_heat(self, mock_listener, mock_transport,
                                mock_target, mock_novaendpoint,
                                mock_heatendpoint):
        x_listener = mock.Mock()
        mock_listener.return_value = x_listener
        x_transport = mock.Mock()
        mock_transport.return_value = x_transport
        x_target = mock.Mock()
        mock_target.return_value = x_target
        x_endpoint = mock.Mock()
        mock_heatendpoint.return_value = x_endpoint

        recover_action = {'operation': 'REBUILD'}
        res = hm.ListenerProc('heat', 'PROJECT_ID', 'CLUSTER_ID',
                              recover_action)

        self.assertIsNone(res)
        mock_transport.assert_called_once_with(cfg.CONF)
        mock_target.assert_called_once_with(topic="notifications",
                                            exchange='heat')
        mock_heatendpoint.assert_called_once_with('PROJECT_ID', 'CLUSTER_ID',
                                                  recover_action)
        mock_listener.assert_called_once_with(
            x_transport, [x_target], [x_endpoint],
            executor='threading', pool="senlin-listeners")
        x_listener.start.assert_called_once_with()


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

    @mock.patch.object(hm.HealthManager, "_load_runtime_registry")
    def test__dummy_task(self, mock_load):
        self.hm._dummy_task()
        mock_load.assert_called_once_with()

    @mock.patch.object(hr.HealthRegistry, 'claim')
    @mock.patch.object(objects.HealthRegistry, 'update')
    def test__load_runtime_registry(self, mock_update, mock_claim):
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
        mock_add_timer = self.patchobject(self.hm.TG, 'add_dynamic_timer',
                                          side_effect=[timer1, timer2])
        # do it
        self.hm._load_runtime_registry()

        # assertions
        mock_claim.assert_called_once_with(self.hm.ctx, self.hm.engine_id)
        mock_calls = [
            mock.call(self.hm._poll_cluster, None, None, 'CID1', 12, {})
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
                'enabled': False,
            },
            self.hm.registries[1])

    @mock.patch.object(hm, "_chase_up")
    @mock.patch.object(obj_node.Node, 'get_all_by_cluster')
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster(self, mock_rpc, mock_ctx, mock_get,
                           mock_wait, mock_nodes, mock_chase):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster
        ctx = mock.Mock()
        mock_ctx.return_value = ctx
        mock_wait.return_value = (True, "")
        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        mock_nodes.return_value = [x_node]
        x_action_check = {'action': 'CHECK_ID'}
        x_action_recover = {'action': 'RECOVER_ID'}
        mock_rpc.side_effect = [x_action_check, x_action_recover]

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._poll_cluster('CLUSTER_ID', 456, recover_action)

        self.assertEqual(mock_chase.return_value, res)
        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        mock_ctx.assert_called_once_with(user_id=x_cluster.user,
                                         project_id=x_cluster.project)
        mock_rpc.assert_has_calls([
            mock.call(ctx, 'cluster_check', mock.ANY),
            mock.call(ctx, 'node_recover', mock.ANY)
        ])
        mock_wait.assert_called_once_with(ctx, "CHECK_ID", 456)
        mock_chase.assert_called_once_with(mock.ANY, 456)

    @mock.patch.object(hm, "_chase_up")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster_not_found(self, mock_check, mock_get, mock_chase):
        mock_get.return_value = None

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._poll_cluster('CLUSTER_ID', 123, recover_action)

        self.assertEqual(mock_chase.return_value, res)
        self.assertEqual(0, mock_check.call_count)
        mock_chase.assert_called_once_with(mock.ANY, 123)

    @mock.patch.object(hm, "_chase_up")
    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster_failed_check_rpc(self, mock_check, mock_get,
                                            mock_ctx, mock_chase):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster
        ctx = mock.Mock()
        mock_ctx.return_value = ctx
        mock_check.side_effect = Exception("boom")

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._poll_cluster('CLUSTER_ID', 123, recover_action)

        self.assertEqual(mock_chase.return_value, res)
        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        mock_ctx.assert_called_once_with(user_id='USER_ID',
                                         project_id='PROJECT_ID')
        mock_check.assert_called_once_with(ctx, 'cluster_check', mock.ANY)
        mock_chase.assert_called_once_with(mock.ANY, 123)

    @mock.patch.object(hm, "_chase_up")
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test__poll_cluster_failed_wait(self, mock_rpc, mock_ctx,
                                       mock_get, mock_wait, mock_chase):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster
        ctx = mock.Mock()
        mock_ctx.return_value = ctx
        mock_wait.return_value = (False, "bad")
        x_action_check = {'action': 'CHECK_ID'}
        mock_rpc.return_value = x_action_check

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._poll_cluster('CLUSTER_ID', 456, recover_action)

        self.assertEqual(mock_chase.return_value, res)
        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        mock_ctx.assert_called_once_with(user_id='USER_ID',
                                         project_id='PROJECT_ID')
        mock_rpc.assert_called_once_with(ctx, 'cluster_check', mock.ANY)
        mock_wait.assert_called_once_with(ctx, "CHECK_ID", 456)
        mock_chase.assert_called_once_with(mock.ANY, 456)

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_nova(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('nova_control_exchange', 'FAKE_NOVA_EXCHANGE',
                              group='health_manager')
        x_listener = mock.Mock()
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread',
                                           return_value=x_listener)
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type='os.nova.server-1.0')
        mock_profile.return_value = x_profile

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._add_listener('CLUSTER_ID', recover_action)

        # assertions
        self.assertEqual(x_listener, res)
        mock_cluster.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.hm.ctx, 'PROFILE_ID',
                                             project_safe=False)
        mock_add_thread.assert_called_once_with(
            hm.ListenerProc, 'FAKE_NOVA_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID',
            recover_action)

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_heat(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('heat_control_exchange', 'FAKE_HEAT_EXCHANGE',
                              group='health_manager')
        x_listener = mock.Mock()
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread',
                                           return_value=x_listener)
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type='os.heat.stack-1.0')
        mock_profile.return_value = x_profile

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._add_listener('CLUSTER_ID', recover_action)

        # assertions
        self.assertEqual(x_listener, res)
        mock_cluster.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.hm.ctx, 'PROFILE_ID',
                                             project_safe=False)
        mock_add_thread.assert_called_once_with(
            hm.ListenerProc, 'FAKE_HEAT_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID',
            recover_action)

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test__add_listener_other_types(self, mock_cluster, mock_profile):
        mock_add_thread = self.patchobject(self.hm.TG, 'add_thread')
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type='other.types-1.0')
        mock_profile.return_value = x_profile

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._add_listener('CLUSTER_ID', recover_action)

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

        recover_action = {'operation': 'REBUILD'}
        # do it
        res = self.hm._add_listener('CLUSTER_ID', recover_action)

        # assertions
        self.assertIsNone(res)
        mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                         project_safe=False)
        self.assertEqual(0, mock_add_thread.call_count)

    def test__start_check_for_polling(self):
        x_timer = mock.Mock()
        mock_add_timer = self.patchobject(self.hm.TG, 'add_dynamic_timer',
                                          return_value=x_timer)

        entry = {
            'cluster_id': 'CCID',
            'interval': 12,
            'check_type': consts.NODE_STATUS_POLLING,
            'params': {'recover_action': [{'name': 'REBUILD'}]},
        }
        recover_action = {'operation': 'REBUILD'}
        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['timer'] = x_timer
        self.assertEqual(expected, res)
        mock_add_timer.assert_called_once_with(
            self.hm._poll_cluster, None, None, 'CCID', 12, recover_action)

    def test__start_check_for_listening(self):
        x_listener = mock.Mock()
        mock_add_listener = self.patchobject(self.hm, '_add_listener',
                                             return_value=x_listener)

        entry = {
            'cluster_id': 'CCID',
            'check_type': consts.LIFECYCLE_EVENTS,
            'params': {'recover_action': [{'name': 'REBUILD'}]},
        }
        recover_action = {'operation': 'REBUILD'}
        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['listener'] = x_listener
        self.assertEqual(expected, res)
        mock_add_listener.assert_called_once_with('CCID', recover_action)

    def test__start_check_for_listening_failed(self):
        mock_add_listener = self.patchobject(self.hm, '_add_listener',
                                             return_value=None)

        entry = {
            'cluster_id': 'CCID',
            'check_type': consts.LIFECYCLE_EVENTS,
            'params': {'recover_action': [{'name': 'REBUILD'}]},
        }
        recover_action = {'operation': 'REBUILD'}
        res = self.hm._start_check(entry)

        self.assertIsNone(res)
        mock_add_listener.assert_called_once_with('CCID', recover_action)

    def test__start_check_other_types(self):
        entry = {
            'cluster_id': 'CCID',
            'check_type': 'BOGUS TYPE',
            'params': {'recover_action': [{'name': 'REBUILD'}]},
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

        # do it
        self.hm.start()

        # assert
        mock_target.assert_called_once_with(server='ENGINE_ID',
                                            topic='engine-health-mgr',
                                            version=consts.RPC_API_VERSION)
        mock_get_rpc.assert_called_once_with(target, self.hm)
        x_rpc_server.start.assert_called_once_with()
        mock_add_timer.assert_called_once_with(
            cfg.CONF.periodic_interval, self.hm._dummy_task)

    @mock.patch.object(hr.HealthRegistry, 'create')
    def test_register_cluster(self, mock_reg_create):
        ctx = mock.Mock()
        timer = mock.Mock()
        mock_add_tm = self.patchobject(self.hm.TG, 'add_dynamic_timer',
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
        mock_add_tm.assert_called_with(mock_poll, None, None, 'CLUSTER_ID', 50,
                                       {})
        self.assertEqual(1, len(self.hm.registries))

    @mock.patch.object(hr.HealthRegistry, 'create')
    def test_register_cluster_not_enabled(self, mock_reg_create):
        ctx = mock.Mock()
        timer = mock.Mock()
        mock_add_tm = self.patchobject(self.hm.TG, 'add_dynamic_timer',
                                       return_value=timer)
        mock_poll = self.patchobject(self.hm, '_poll_cluster',
                                     return_value=mock.Mock())
        x_reg = mock.Mock(cluster_id='CLUSTER_ID',
                          check_type=consts.NODE_STATUS_POLLING,
                          interval=50, params={}, enabled=False)
        mock_reg_create.return_value = x_reg

        self.hm.register_cluster(ctx,
                                 cluster_id='CLUSTER_ID',
                                 check_type=consts.NODE_STATUS_POLLING,
                                 interval=50, enabled=x_reg.enabled)

        mock_reg_create.assert_called_once_with(
            ctx, 'CLUSTER_ID', consts.NODE_STATUS_POLLING, 50, {}, 'ENGINE_ID',
            enabled=False)
        mock_add_tm.assert_not_called()
        mock_poll.assert_not_called()
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

    @mock.patch.object(context, 'get_admin_context')
    @mock.patch.object(hr.HealthRegistry, 'get')
    def test_get_manager_engine(self, mock_get, mock_ctx):
        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        registry = mock.Mock(engine_id='fake')
        mock_get.return_value = registry

        result = hm.get_manager_engine('CID')

        self.assertEqual(result, 'fake')

        mock_get.assert_called_once_with(ctx, 'CID')
        self.assertTrue(mock_ctx.called)

    @mock.patch.object(context, 'get_admin_context')
    @mock.patch.object(hr.HealthRegistry, 'get')
    def test_get_manager_engine_none(self, mock_get, mock_ctx):
        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        mock_get.return_value = None

        result = hm.get_manager_engine('CID')

        self.assertIsNone(result)

        mock_get.assert_called_once_with(ctx, 'CID')
        self.assertTrue(mock_ctx.called)
