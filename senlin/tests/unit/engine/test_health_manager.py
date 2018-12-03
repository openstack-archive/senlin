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
import re
import time

import mock
from oslo_config import cfg
from oslo_service import threadgroup
from oslo_utils import timeutils as tu

from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common import messaging
from senlin.common import utils
from senlin.engine import health_manager as hm
from senlin.engine import node as node_mod
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


class TestHealthCheckType(base.SenlinTestCase):
    def setUp(self):
        super(TestHealthCheckType, self).setUp()

        self.hc = hm.NodePollStatusHealthCheck(
            cluster_id='CLUSTER_ID', interval=1, node_update_timeout=1,
            params=''
        )

    def test_factory(self):
        cid = 'CLUSTER_ID'
        interval = 1
        params = {
            'detection_modes': [
                {
                    'type': 'NODE_STATUS_POLLING',
                    'poll_url': '',
                    'poll_url_ssl_verify': True,
                    'poll_url_conn_error_as_unhealthy': True,
                    'poll_url_healthy_response': '',
                    'poll_url_retry_limit': '',
                    'poll_url_retry_interval': ''
                },
                {
                    'type': 'NODE_STATUS_POLL_URL',
                    'poll_url': '',
                    'poll_url_ssl_verify': True,
                    'poll_url_conn_error_as_unhealthy': True,
                    'poll_url_healthy_response': '',
                    'poll_url_retry_limit': '',
                    'poll_url_retry_interval': ''
                }
            ],
            'node_update_timeout': 300,
        }

        for d in params['detection_modes']:
            hc = hm.HealthCheckType.factory(d['type'], cid, interval, params)

            self.assertEqual(cid, hc.cluster_id)
            self.assertEqual(interval, hc.interval)
            self.assertEqual(d, hc.params)
            self.assertEqual(
                params['node_update_timeout'], hc.node_update_timeout)

    def test_factory_invalid_type(self):
        cid = 'CLUSTER_ID'
        interval = 1
        params = {
            'detection_modes': [
                {
                    'type': 'blah',
                    'poll_url': '',
                    'poll_url_ssl_verify': True,
                    'poll_url_conn_error_as_unhealthy': True,
                    'poll_url_healthy_response': '',
                    'poll_url_retry_limit': '',
                    'poll_url_retry_interval': ''
                },
            ],
            'node_update_timeout': 300,
        }

        with self.assertRaisesRegex(Exception, 'Invalid detection type: blah'):
            hm.HealthCheckType.factory('blah', cid, interval, params)

    def test_factory_same_type_twice(self):
        cid = 'CLUSTER_ID'
        interval = 1
        params = {
            'detection_modes': [
                {
                    'type': 'NODE_STATUS_POLLING',
                    'poll_url': '',
                    'poll_url_ssl_verify': True,
                    'poll_url_conn_error_as_unhealthy': True,
                    'poll_url_healthy_response': '',
                    'poll_url_retry_limit': '',
                    'poll_url_retry_interval': ''
                },
                {
                    'type': 'NODE_STATUS_POLLING',
                    'poll_url': '',
                    'poll_url_ssl_verify': True,
                    'poll_url_conn_error_as_unhealthy': True,
                    'poll_url_healthy_response': '',
                    'poll_url_retry_limit': '',
                    'poll_url_retry_interval': ''
                }
            ],
            'node_update_timeout': 300,
        }

        with self.assertRaisesRegex(
                Exception,
                '.*Encountered 2 instances of type NODE_STATUS_POLLING'):
            hm.HealthCheckType.factory(
                'NODE_STATUS_POLLING', cid, interval, params)


class TestNodePollStatusHealthCheck(base.SenlinTestCase):
    def setUp(self):
        super(TestNodePollStatusHealthCheck, self).setUp()

        self.hc = hm.NodePollStatusHealthCheck(
            cluster_id='CLUSTER_ID',
            interval=1, node_update_timeout=1, params=''
        )

    @mock.patch.object(node_mod.Node, '_from_object')
    @mock.patch.object(tu, 'is_older_than')
    def test_run_health_check_healthy(self, mock_tu, mock_node_obj):
        x_entity = mock.Mock()
        x_entity.do_healthcheck.return_value = True
        mock_node_obj.return_value = x_entity

        ctx = mock.Mock()
        node = mock.Mock(id='FAKE_NODE1', status="ERROR",
                         updated_at='2018-08-13 18:00:00',
                         init_at='2018-08-13 17:00:00')

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_tu.assert_not_called()

    @mock.patch.object(node_mod.Node, '_from_object')
    @mock.patch.object(tu, 'is_older_than')
    def test_run_health_check_healthy_internal_error(
            self, mock_tu, mock_node_obj):
        x_entity = mock.Mock()
        x_entity.do_healthcheck.side_effect = exc.InternalError(
            message='error')
        mock_node_obj.return_value = x_entity

        ctx = mock.Mock()
        node = mock.Mock(id='FAKE_NODE1', status="ERROR",
                         updated_at='2018-08-13 18:00:00',
                         init_at='2018-08-13 17:00:00')

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_tu.assert_not_called()

    @mock.patch.object(node_mod.Node, '_from_object')
    @mock.patch.object(tu, 'is_older_than')
    def test_run_health_check_unhealthy(self, mock_tu, mock_node_obj):
        x_entity = mock.Mock()
        x_entity.do_healthcheck.return_value = False
        mock_node_obj.return_value = x_entity

        mock_tu.return_value = True

        ctx = mock.Mock()
        node = mock.Mock(id='FAKE_NODE1', status="ERROR",
                         updated_at='2018-08-13 18:00:00',
                         init_at='2018-08-13 17:00:00')

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertFalse(res)
        mock_tu.assert_called_once_with(node.updated_at, 1)

    @mock.patch.object(node_mod.Node, '_from_object')
    @mock.patch.object(tu, 'is_older_than')
    def test_run_health_check_unhealthy_within_timeout(
            self, mock_tu, mock_node_obj):
        x_entity = mock.Mock()
        x_entity.do_healthcheck.return_value = False
        mock_node_obj.return_value = x_entity

        mock_tu.return_value = False

        ctx = mock.Mock()
        node = mock.Mock(id='FAKE_NODE1', status="ERROR",
                         updated_at='2018-08-13 18:00:00',
                         init_at='2018-08-13 17:00:00')

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_tu.assert_called_once_with(node.updated_at, 1)


class TestNodePollUrlHealthCheck(base.SenlinTestCase):
    def setUp(self):
        super(TestNodePollUrlHealthCheck, self).setUp()

        default_params = {
            'poll_url': 'FAKE_POLL_URL',
            'poll_url_ssl_verify': True,
            'poll_url_conn_error_as_unhealthy': True,
            'poll_url_healthy_response': 'FAKE_HEALTHY_PATTERN',
            'poll_url_retry_limit': 2,
            'poll_url_retry_interval': 1,
            'node_update_timeout': 5
        }

        self.hc = hm.NodePollUrlHealthCheck(
            cluster_id='CLUSTER_ID', interval=1, node_update_timeout=1,
            params=default_params
        )

    def test_expand_url_template(self):
        url_template = 'https://abc123/foo/bar'
        node = mock.Mock()

        # do it
        res = self.hc._expand_url_template(url_template, node)

        self.assertEqual(res, url_template)

    def test_expand_url_template_nodename(self):
        node = mock.Mock()
        node.name = 'name'
        url_template = 'https://abc123/{nodename}/bar'
        expanded_url = 'https://abc123/{}/bar'.format(node.name)

        # do it
        res = self.hc._expand_url_template(url_template, node)

        self.assertEqual(res, expanded_url)

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_healthy(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ("Healthy because this return value "
                                       "contains FAKE_HEALTHY_PATTERN")

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_called_once_with('FAKE_EXPANDED_URL', timeout=1,
                                               verify=True)

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_healthy_min_timeout(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ("Healthy because this return value "
                                       "contains FAKE_HEALTHY_PATTERN")

        self.hc.params['poll_url_retry_interval'] = 0

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_called_once_with('FAKE_EXPANDED_URL', timeout=1,
                                               verify=True)

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_healthy_timeout(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ("Healthy because this return value "
                                       "contains FAKE_HEALTHY_PATTERN")

        self.hc.params['poll_url_retry_interval'] = 100

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_called_once_with('FAKE_EXPANDED_URL', timeout=10,
                                               verify=True)

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_unhealthy_inactive(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_RECOVERING
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ""

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_not_called()

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_unhealthy_update_timeout(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.id = 'FAKE_NODE_ID'
        node.updated_at = 'FAKE_UPDATE_TIME'
        node.status = consts.NS_ACTIVE
        mock_time.return_value = False
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ""

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_has_calls(
            [mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True)])

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_unhealthy_init_timeout(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.id = 'FAKE_NODE_ID'
        node.updated_at = None
        node.init_at = 'FAKE_INIT_TIME'
        node.status = consts.NS_ACTIVE
        mock_time.return_value = False
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ""

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_has_calls(
            [mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True)])

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_unhealthy(self, mock_url_fetch, mock_expand_url,
                                        mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        node.id = 'FAKE_ID'
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.return_value = ""

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertFalse(res)
        mock_url_fetch.assert_has_calls(
            [
                mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True),
                mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True)
            ]
        )

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_conn_error(self,
                                         mock_url_fetch,
                                         mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        node.id = 'FAKE_ID'
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.side_effect = utils.URLFetchError("Error")

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertFalse(res)
        mock_url_fetch.assert_has_calls(
            [
                mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True),
                mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True)
            ]
        )

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_conn_other_error(self,
                                               mock_url_fetch,
                                               mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        node.id = 'FAKE_ID'
        mock_time.return_value = True
        mock_expand_url.side_effect = Exception('blah')

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_not_called()

    @mock.patch.object(tu, "is_older_than")
    @mock.patch.object(hm.NodePollUrlHealthCheck, "_expand_url_template")
    @mock.patch.object(utils, 'url_fetch')
    def test_run_health_check_conn_error_noop(
            self, mock_url_fetch, mock_expand_url, mock_time):
        ctx = mock.Mock()
        node = mock.Mock()
        node.status = consts.NS_ACTIVE
        node.id = 'FAKE_ID'
        mock_time.return_value = True
        mock_expand_url.return_value = 'FAKE_EXPANDED_URL'
        mock_url_fetch.side_effect = utils.URLFetchError("Error")

        self.hc.params['poll_url_conn_error_as_unhealthy'] = False

        # do it
        res = self.hc.run_health_check(ctx, node)

        self.assertTrue(res)
        mock_url_fetch.assert_has_calls(
            [
                mock.call('FAKE_EXPANDED_URL', timeout=1, verify=True),
            ]
        )


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
    def test_task(self, mock_load):
        self.hm.task()
        mock_load.assert_called_once_with()

    @mock.patch.object(hm.HealthManager, "_stop_check")
    @mock.patch.object(hm.HealthManager, "_start_check")
    @mock.patch.object(hr.HealthRegistry, 'claim')
    def test_load_runtime_registry(self, mock_claim, mock_check, mock_stop):
        fake_claims = [
            {
                'cluster_id': 'CID1',
                'check_type': consts.NODE_STATUS_POLLING,
                'interval': 12,
                'params': {'k1': 'v1'},
                'enabled': True,
            },
            {
                'cluster_id': 'CID2',
                'check_type': consts.NODE_STATUS_POLLING,
                'interval': 34,
                'params': {'k2': 'v2'},
                'enabled': False,
            },
        ]
        mock_claim.return_value = [
            mock.Mock(**fake_claims[0]),
            mock.Mock(**fake_claims[1]),
        ]
        mock_check.return_value = fake_claims

        # do it
        self.hm._load_runtime_registry()

        # assertions
        mock_claim.assert_called_once_with(self.hm.ctx, self.hm.engine_id)
        mock_check.assert_has_calls(
            [
                mock.call(fake_claims[0])
            ]
        )
        mock_stop.assert_called_once_with(fake_claims[0])

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test_add_listener_nova(self, mock_cluster, mock_profile):
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
    def test_add_listener_heat(self, mock_cluster, mock_profile):
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
    def test_add_listener_other_types(self, mock_cluster, mock_profile):
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
    def test_add_listener_cluster_not_found(self, mock_get):
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

    @mock.patch.object(rpc_client.EngineClient, 'call')
    @mock.patch('senlin.objects.NodeRecoverRequest', autospec=True)
    def test_recover_node(self, mock_req, mock_rpc):
        ctx = mock.Mock()
        node_id = 'FAKE_NODE'
        recover_action = {'operation': 'REBUILD'}

        x_req = mock.Mock
        mock_req.return_value = x_req

        x_action = {'action': 'RECOVER_ID1'}
        mock_rpc.return_value = x_action

        # do it
        res = self.hm._recover_node(node_id, ctx, recover_action)

        self.assertEqual(x_action, res)
        mock_req.assert_called_once_with(
            identity=node_id, params=recover_action)
        mock_rpc.assert_called_once_with(ctx, 'node_recover', x_req)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    @mock.patch('senlin.objects.NodeRecoverRequest', autospec=True)
    def test_recover_node_failed(self, mock_req, mock_rpc):
        ctx = mock.Mock()
        node_id = 'FAKE_NODE'
        recover_action = {'operation': 'REBUILD'}

        x_req = mock.Mock
        mock_req.return_value = x_req

        mock_rpc.side_effect = Exception('boom')

        # do it
        res = self.hm._recover_node(node_id, ctx, recover_action)

        self.assertIsNone(res)
        mock_req.assert_called_once_with(
            identity=node_id, params=recover_action)
        mock_rpc.assert_called_once_with(ctx, 'node_recover', x_req)

    @mock.patch('senlin.objects.ActionGetRequest')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_wait_for_action(self, mock_rpc, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_SUCCEEDED}
        mock_rpc.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hm._wait_for_action(ctx, action_id, timeout)

        self.assertTrue(res)
        self.assertEqual(err, '')
        mock_rpc.assert_called_with(ctx, 'action_get', x_req)

    @mock.patch('senlin.objects.ActionGetRequest')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_wait_for_action_success_before_timeout(
            self, mock_rpc, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action1 = {'status': consts.ACTION_RUNNING}
        x_action2 = {'status': consts.ACTION_SUCCEEDED}
        mock_rpc.side_effect = [x_action1, x_action2]

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hm._wait_for_action(ctx, action_id, timeout)

        self.assertTrue(res)
        self.assertEqual(err, '')
        mock_rpc.assert_has_calls(
            [
                mock.call(ctx, 'action_get', x_req),
                mock.call(ctx, 'action_get', x_req)
            ]
        )

    @mock.patch('senlin.objects.ActionGetRequest')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_wait_for_action_timeout(self, mock_rpc, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_RUNNING}
        mock_rpc.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hm._wait_for_action(ctx, action_id, timeout)

        self.assertFalse(res)
        self.assertTrue(re.search('timeout', err, re.IGNORECASE))
        mock_rpc.assert_has_calls(
            [
                mock.call(ctx, 'action_get', x_req)
            ]
        )

    @mock.patch('senlin.objects.ActionGetRequest')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_wait_for_action_failed(self, mock_rpc, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_FAILED}
        mock_rpc.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hm._wait_for_action(ctx, action_id, timeout)

        self.assertFalse(res)
        self.assertEqual(err, 'Cluster check action failed or cancelled')
        mock_rpc.assert_called_with(ctx, 'action_get', x_req)

    @mock.patch('senlin.objects.ActionGetRequest')
    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_wait_for_action_cancelled(self, mock_rpc, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_CANCELLED}
        mock_rpc.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hm._wait_for_action(ctx, action_id, timeout)

        self.assertFalse(res)
        self.assertEqual(err, 'Cluster check action failed or cancelled')
        mock_rpc.assert_called_with(ctx, 'action_get', x_req)

    @mock.patch.object(obj_node.Node, 'get_all_by_cluster')
    @mock.patch.object(hm.HealthManager, "_recover_node")
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_any_mode_healthy(
            self, mock_ctx, mock_get, mock_wait, mock_recover, mock_nodes):
        cluster_id = 'CLUSTER_ID'
        interval = 1
        recovery_cond = consts.ANY_FAILED
        node_update_timeout = 1
        recovery_action = {'operation': 'REBUILD'}

        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster

        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        mock_wait.return_value = (True, "")

        x_node1 = mock.Mock(id='FAKE_NODE1', status="ERROR")
        x_node2 = mock.Mock(id='FAKE_NODE2', status="ERROR")
        mock_nodes.return_value = [x_node1, x_node2]

        hc_true = {'run_health_check.return_value': True}

        hc_test_values = [
            [
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
            ],
        ]

        self.hm.cluster_id = cluster_id

        for hc_mocks in hc_test_values:
            self.hm.health_check_types = {
                cluster_id: hc_mocks
            }

            mock_get.reset_mock()
            mock_ctx.reset_mock()
            mock_recover.reset_mock()
            mock_wait.reset_mock()

            # do it
            self.hm._execute_health_check(interval, cluster_id,
                                          recovery_action,
                                          recovery_cond, node_update_timeout)

            mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
            mock_ctx.assert_called_once_with(user_id=x_cluster.user,
                                             project_id=x_cluster.project)

            for mock_hc in hc_mocks:
                mock_hc.run_health_check.assert_has_calls(
                    [
                        mock.call(ctx, x_node1),
                        mock.call(ctx, x_node2)
                    ]
                )

            mock_recover.assert_not_called()
            mock_wait.assert_not_called()

    @mock.patch.object(obj_node.Node, 'get_all_by_cluster')
    @mock.patch.object(hm.HealthManager, "_recover_node")
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_any_mode_unhealthy(
            self, mock_ctx, mock_get, mock_wait, mock_recover, mock_nodes):
        cluster_id = 'CLUSTER_ID'
        interval = 1
        recovery_cond = consts.ANY_FAILED
        node_update_timeout = 1
        recovery_action = {'operation': 'REBUILD'}

        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster

        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        mock_wait.return_value = (True, "")

        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        mock_nodes.return_value = [x_node]

        mock_recover.return_value = {'action': 'FAKE_ACTION_ID'}

        hc_true = {'run_health_check.return_value': True}
        hc_false = {'run_health_check.return_value': False}

        hc_test_values = [
            [
                mock.Mock(**hc_false),
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
            ],
            [
                mock.Mock(**hc_true),
                mock.Mock(**hc_false),
                mock.Mock(**hc_true),
            ],
            [
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
                mock.Mock(**hc_false),
            ]
        ]

        for hc_mocks in hc_test_values:
            self.hm.health_check_types = {
                cluster_id: hc_mocks
            }

            mock_get.reset_mock()
            mock_ctx.reset_mock()
            mock_recover.reset_mock()
            mock_wait.reset_mock()

            # do it
            self.hm._execute_health_check(interval, cluster_id,
                                          recovery_action,
                                          recovery_cond, node_update_timeout)

            mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
            mock_ctx.assert_called_once_with(user_id=x_cluster.user,
                                             project_id=x_cluster.project)

            # health checks should be called until one of them returns false
            previous_hc_returned_false = False
            for mock_hc in hc_mocks:
                if not previous_hc_returned_false:
                    mock_hc.run_health_check.assert_called_once_with(
                        ctx, x_node)
                else:
                    mock_hc.assert_not_called()
                if not mock_hc.run_health_check.return_value:
                    previous_hc_returned_false = True

            mock_recover.assert_called_once_with('FAKE_NODE', ctx, mock.ANY)
            mock_wait.assert_called_once_with(
                ctx, 'FAKE_ACTION_ID', node_update_timeout)

    @mock.patch.object(obj_node.Node, 'get_all_by_cluster')
    @mock.patch.object(hm.HealthManager, "_recover_node")
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_all_mode_healthy(
            self, mock_ctx, mock_get, mock_wait, mock_recover, mock_nodes):
        cluster_id = 'CLUSTER_ID'
        interval = 1
        recovery_cond = consts.ALL_FAILED
        node_update_timeout = 1
        recovery_action = {'operation': 'REBUILD'}

        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster

        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        mock_wait.return_value = (True, "")

        x_node = mock.Mock(id='FAKE_NODE1', status="ERROR")
        mock_nodes.return_value = [x_node]

        hc_true = {'run_health_check.return_value': True}
        hc_false = {'run_health_check.return_value': False}

        hc_test_values = [
            [
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
            ],
            [
                mock.Mock(**hc_false),
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
            ],
            [
                mock.Mock(**hc_true),
                mock.Mock(**hc_false),
                mock.Mock(**hc_true),
            ],
            [
                mock.Mock(**hc_true),
                mock.Mock(**hc_true),
                mock.Mock(**hc_false),
            ],
        ]

        self.hm.cluster_id = cluster_id

        for hc_mocks in hc_test_values:
            self.hm.health_check_types = {
                cluster_id: hc_mocks
            }

            mock_get.reset_mock()
            mock_ctx.reset_mock()
            mock_recover.reset_mock()
            mock_wait.reset_mock()

            # do it
            self.hm._execute_health_check(interval, cluster_id,
                                          recovery_action,
                                          recovery_cond, node_update_timeout)

            mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
            mock_ctx.assert_called_once_with(user_id=x_cluster.user,
                                             project_id=x_cluster.project)

            # health checks should be called until one of them returns true
            previous_hc_returned_true = False
            for mock_hc in hc_mocks:
                if not previous_hc_returned_true:
                    mock_hc.run_health_check.assert_called_once_with(
                        ctx, x_node)
                else:
                    mock_hc.assert_not_called()
                if mock_hc.run_health_check.return_value:
                    previous_hc_returned_true = True

            mock_recover.assert_not_called()
            mock_wait.assert_not_called()

    @mock.patch.object(obj_node.Node, 'get_all_by_cluster')
    @mock.patch.object(hm.HealthManager, "_recover_node")
    @mock.patch.object(hm.HealthManager, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_all_mode_unhealthy(
            self, mock_ctx, mock_get, mock_wait, mock_recover, mock_nodes):
        cluster_id = 'CLUSTER_ID'
        interval = 1
        recovery_cond = consts.ALL_FAILED
        node_update_timeout = 1
        recovery_action = {'operation': 'REBUILD'}

        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID')
        mock_get.return_value = x_cluster

        ctx = mock.Mock()
        mock_ctx.return_value = ctx

        mock_wait.return_value = (True, "")

        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        mock_nodes.return_value = [x_node]

        mock_recover.return_value = {'action': 'FAKE_ACTION_ID'}

        hc_false = {'run_health_check.return_value': False}

        hc_test_values = [
            [
                mock.Mock(**hc_false),
                mock.Mock(**hc_false),
                mock.Mock(**hc_false),
            ]
        ]

        self.hm.cluster_id = cluster_id
        self.hm.node_update_timeout = 1

        for hc_mocks in hc_test_values:
            self.hm.health_check_types = {
                cluster_id: hc_mocks
            }

            mock_get.reset_mock()
            mock_ctx.reset_mock()
            mock_recover.reset_mock()
            mock_wait.reset_mock()

            # do it
            self.hm._execute_health_check(interval, cluster_id,
                                          recovery_action,
                                          recovery_cond, node_update_timeout)

            mock_get.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID',
                                             project_safe=False)
            mock_ctx.assert_called_once_with(user_id=x_cluster.user,
                                             project_id=x_cluster.project)

            # all health checks should be called
            for mock_hc in hc_mocks:
                mock_hc.run_health_check.assert_called_once_with(ctx, x_node)

            mock_recover.assert_called_once_with('FAKE_NODE', ctx, mock.ANY)
            mock_wait.assert_called_once_with(
                ctx, 'FAKE_ACTION_ID', self.hm.node_update_timeout)

    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_cluster_not_found(self, mock_ctx, mock_get):
        cluster_id = 'CLUSTER_ID'
        interval = 1
        recovery_cond = consts.ANY_FAILED
        node_update_timeout = 1
        recovery_action = {'operation': 'REBUILD'}

        mock_get.return_value = None

        # do it
        self.hm._execute_health_check(interval, cluster_id,
                                      recovery_action, recovery_cond,
                                      node_update_timeout)

        mock_ctx.assert_not_called()

    def test_start_check_invalid_type(self):
        entry = {
            'cluster_id': 'CCID',
            'interval': 12,
            'check_type': 'blah',
            'params': {
                'recover_action': [{'name': 'REBUILD'}]
            },
        }

        res = self.hm._start_check(entry)

        self.assertIsNone(res)

    @mock.patch.object(threadgroup.ThreadGroup, 'add_dynamic_timer')
    @mock.patch.object(hm.HealthManager, '_add_health_check')
    @mock.patch.object(hm.HealthCheckType, 'factory')
    def test_start_check_for_polling(self, mock_hc_factory, mock_add_hc,
                                     mock_add_timer):
        x_timer = mock.Mock()
        mock_add_timer.return_value = x_timer

        entry = {
            'cluster_id': 'CCID',
            'interval': 12,
            'check_type': consts.NODE_STATUS_POLLING,
            'params': {
                'recover_action': [{'name': 'REBUILD'}],
                'recovery_conditional': 'ANY_FAILED',
                'node_update_timeout': 1,
            },
        }

        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['timer'] = x_timer
        self.assertEqual(expected, res)
        mock_add_timer.assert_called_once_with(
            self.hm._execute_health_check, None, None, 12, 'CCID',
            {'operation': 'REBUILD'}, 'ANY_FAILED', 1)
        mock_add_hc.assert_called_once_with('CCID', mock.ANY)
        mock_hc_factory.assert_called_once_with(
            consts.NODE_STATUS_POLLING, 'CCID', 12, entry['params'])

    @mock.patch.object(threadgroup.ThreadGroup, 'add_dynamic_timer')
    @mock.patch.object(hm.HealthManager, '_add_health_check')
    @mock.patch.object(hm.HealthCheckType, 'factory')
    def test_start_check_for_poll_url(self, mock_hc_factory, mock_add_hc,
                                      mock_add_timer):
        x_timer = mock.Mock()
        mock_add_timer.return_value = x_timer

        entry = {
            'cluster_id': 'CCID',
            'interval': 12,
            'check_type': consts.NODE_STATUS_POLL_URL,
            'params': {
                'recover_action': [{'name': 'REBUILD'}],
                'recovery_conditional': 'ANY_FAILED',
                'node_update_timeout': 1,
            },
        }

        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['timer'] = x_timer
        self.assertEqual(expected, res)
        mock_add_timer.assert_called_once_with(
            self.hm._execute_health_check, None, None, 12, 'CCID',
            {'operation': 'REBUILD'}, 'ANY_FAILED', 1)
        mock_add_hc.assert_called_once_with('CCID', mock.ANY)
        mock_hc_factory.assert_called_once_with(
            consts.NODE_STATUS_POLL_URL,
            'CCID', 12, entry['params'])

    @mock.patch.object(threadgroup.ThreadGroup, 'add_dynamic_timer')
    @mock.patch.object(hm.HealthManager, '_add_health_check')
    @mock.patch.object(hm.HealthCheckType, 'factory')
    def test_start_check_poll_url_and_polling(self, mock_hc_factory,
                                              mock_add_hc, mock_add_timer):
        x_timer = mock.Mock()
        mock_add_timer.return_value = x_timer

        check_type = ','.join(
            [consts.NODE_STATUS_POLL_URL, consts.NODE_STATUS_POLLING])
        entry = {
            'cluster_id': 'CCID',
            'interval': 12,
            'check_type': check_type,
            'params': {
                'recover_action': [{'name': 'REBUILD'}],
                'recovery_conditional': 'ALL_FAILED',
                'node_update_timeout': 1,
            },
        }

        res = self.hm._start_check(entry)

        expected = copy.deepcopy(entry)
        expected['timer'] = x_timer
        self.assertEqual(expected, res)
        mock_add_timer.assert_called_once_with(
            self.hm._execute_health_check, None, None, 12, 'CCID',
            {'operation': 'REBUILD'}, 'ALL_FAILED', 1)
        mock_add_hc.assert_has_calls(
            [
                mock.call('CCID', mock.ANY),
                mock.call('CCID', mock.ANY)
            ]
        )
        mock_hc_factory.assert_has_calls(
            [
                mock.call(
                    consts.NODE_STATUS_POLL_URL, 'CCID', 12, entry['params']
                ),
                mock.call(
                    consts.NODE_STATUS_POLLING, 'CCID', 12, entry['params']
                ),
            ]
        )

    def test_start_check_for_listening(self):
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

    def test_start_check_for_listening_failed(self):
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

    def test_start_check_other_types(self):
        entry = {
            'cluster_id': 'CCID',
            'check_type': 'BOGUS TYPE',
            'params': {'recover_action': [{'name': 'REBUILD'}]},
        }
        res = self.hm._start_check(entry)

        self.assertIsNone(res)

    def test_stop_check_with_timer(self):
        x_timer = mock.Mock()
        entry = {'timer': x_timer, 'cluster_id': 'CLUSTER_ID'}
        mock_timer_done = self.patchobject(self.hm.TG, 'timer_done')

        x_hc_types = mock.MagicMock()
        x_hc_types.__contains__.return_value = True
        x_hc_types.__iter__.return_value = ['CLUSTER_ID']
        self.hm.health_check_types = x_hc_types

        # do it
        res = self.hm._stop_check(entry)

        self.assertIsNone(res)
        x_timer.stop.assert_called_once_with()
        mock_timer_done.assert_called_once_with(x_timer)
        x_hc_types.pop.assert_called_once_with('CLUSTER_ID')

    def test_stop_check_with_listener(self):
        x_thread = mock.Mock()
        entry = {'listener': x_thread, 'cluster_id': 'CLUSTER_ID'}
        mock_thread_done = self.patchobject(self.hm.TG, 'thread_done')

        x_hc_types = mock.MagicMock()
        x_hc_types.__contains__.return_value = False
        x_hc_types.__iter__.return_value = ['CLUSTER_ID']
        self.hm.health_check_types = x_hc_types

        # do it
        res = self.hm._stop_check(entry)

        self.assertIsNone(res)
        x_thread.stop.assert_called_once_with()
        mock_thread_done.assert_called_once_with(x_thread)
        x_hc_types.pop.assert_not_called()

    @mock.patch('oslo_messaging.Target')
    def test_start(self, mock_target):
        self.hm.TG = mock.Mock()
        target = mock.Mock()
        mock_target.return_value = target
        x_rpc_server = mock.Mock()
        mock_get_rpc = self.patchobject(messaging, 'get_rpc_server',
                                        return_value=x_rpc_server)
        x_timer = mock.Mock()
        mock_add_timer = self.patchobject(self.hm.TG, 'add_dynamic_timer',
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
            self.hm.task, None, cfg.CONF.periodic_interval)

    @mock.patch.object(hr.HealthRegistry, 'create')
    @mock.patch.object(hm.HealthManager, '_start_check')
    def test_register_cluster(self, mock_check, mock_reg_create):
        entry = {
            'cluster_id': 'CLUSTER_ID',
            'check_type': consts.NODE_STATUS_POLLING,
            'interval': 50,
            'params': {
                'blah': '123',
                'detection_modes': [
                    {
                        'type': consts.NODE_STATUS_POLLING,
                        'poll_url': '',
                        'poll_url_ssl_verify': True,
                        'poll_url_conn_error_as_unhealthy': True,
                        'poll_url_healthy_response': '',
                        'poll_url_retry_limit': '',
                        'poll_url_retry_interval': '',
                    }
                ],
            },
            'enabled': True
        }

        ctx = mock.Mock()

        x_reg = mock.Mock(cluster_id=entry['cluster_id'],
                          check_type=entry['check_type'],
                          interval=entry['interval'], params=entry['params'],
                          enabled=entry['enabled'])
        mock_reg_create.return_value = x_reg

        self.hm.register_cluster(
            ctx, cluster_id=entry['cluster_id'], interval=entry['interval'],
            node_update_timeout=1, params=entry['params'],
            enabled=entry['enabled'])

        mock_reg_create.assert_called_once_with(
            ctx, entry['cluster_id'], consts.NODE_STATUS_POLLING,
            entry['interval'], entry['params'], 'ENGINE_ID',
            enabled=entry['enabled'])
        mock_check.assert_called_once_with(entry)
        self.assertEqual(1, len(self.hm.registries))

    @mock.patch.object(hr.HealthRegistry, 'create')
    @mock.patch.object(hm.HealthManager, '_start_check')
    def test_register_cluster_not_enabled(self, mock_check, mock_reg_create):
        entry = {
            'cluster_id': 'CLUSTER_ID',
            'check_type': consts.NODE_STATUS_POLLING,
            'interval': 50,
            'params': {
                'blah': '123',
                'detection_modes': [
                    {
                        'type': consts.NODE_STATUS_POLLING,
                        'poll_url': '',
                        'poll_url_ssl_verify': True,
                        'poll_url_conn_error_as_unhealthy': True,
                        'poll_url_healthy_response': '',
                        'poll_url_retry_limit': '',
                        'poll_url_retry_interval': '',
                    }
                ],
            },
            'enabled': False
        }

        ctx = mock.Mock()

        x_reg = mock.Mock(cluster_id=entry['cluster_id'],
                          check_type=entry['check_type'],
                          interval=entry['interval'], params=entry['params'],
                          enabled=entry['enabled'])
        mock_reg_create.return_value = x_reg

        self.hm.register_cluster(
            ctx, cluster_id=entry['cluster_id'], interval=entry['interval'],
            node_update_timeout=1, params=entry['params'],
            enabled=entry['enabled'])

        mock_reg_create.assert_called_once_with(
            ctx, entry['cluster_id'], consts.NODE_STATUS_POLLING,
            entry['interval'], entry['params'], 'ENGINE_ID',
            enabled=entry['enabled'])
        mock_check.assert_not_called()
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
