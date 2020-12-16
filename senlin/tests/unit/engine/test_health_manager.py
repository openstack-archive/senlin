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

import re
import time
from unittest import mock

from oslo_config import cfg
from oslo_utils import timeutils as tu

from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common import utils
from senlin.engine import health_manager as hm
from senlin.engine import node as node_mod
from senlin.engine.notifications import nova_endpoint
from senlin import objects
from senlin.objects import cluster as obj_cluster
from senlin.objects import node as obj_node
from senlin.objects import profile as obj_profile
from senlin.rpc import client as rpc_client
from senlin.tests.unit.common import base


class TestChaseUp(base.SenlinTestCase):

    def test_less_than_one_interval(self):
        start = tu.utcnow(True)
        # we assume that the delay before next line is < 5 seconds
        res = hm.chase_up(start, 5)

        self.assertLessEqual(res, 5)

    def test_more_than_one_interval(self):
        start = tu.utcnow(True)
        time.sleep(2)

        # we assume that the delay before next line is < 5 seconds
        res = hm.chase_up(start, 1)

        self.assertLessEqual(res, 1)


@mock.patch('oslo_messaging.NotificationFilter')
class TestNovaNotificationEndpoint(base.SenlinTestCase):

    @mock.patch('senlin.rpc.client.get_engine_client')
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
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )

        mock_filter.assert_called_once_with(
            publisher_id='^compute.*',
            event_type='^compute\.instance\..*',
            context={'project_id': '^PROJECT$'})
        mock_rpc.assert_called_once_with()
        self.assertEqual(x_filter, endpoint.filter_rule)
        self.assertEqual(mock_rpc.return_value, endpoint.rpc)
        for e in event_map:
            self.assertIn(e, endpoint.VM_FAILURE_EVENTS)
            self.assertEqual(event_map[e], endpoint.VM_FAILURE_EVENTS[e])
        self.assertEqual('PROJECT', endpoint.project_id)
        self.assertEqual('CLUSTER_ID', endpoint.cluster_id)

    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info(self, mock_rpc, mock_context, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
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

    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info_no_metadata(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
        ctx = mock.Mock()
        payload = {'metadata': {}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info_no_cluster_in_metadata(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
        ctx = mock.Mock()
        payload = {'metadata': {'foo': 'bar'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info_cluster_id_not_match(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
        ctx = mock.Mock()
        payload = {'metadata': {'cluster_id': 'FOOBAR'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info_event_type_not_interested(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
        ctx = mock.Mock()
        payload = {'metadata': {'cluster_id': 'CLUSTER_ID'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.start',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info_no_node_id(self, mock_rpc, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
        ctx = mock.Mock()
        payload = {'metadata': {'cluster_id': 'CLUSTER_ID'}}
        metadata = {'timestamp': 'TIMESTAMP'}

        res = endpoint.info(ctx, 'PUBLISHER', 'compute.instance.delete.end',
                            payload, metadata)

        self.assertIsNone(res)
        self.assertEqual(0, x_rpc.node_recover.call_count)

    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch('senlin.rpc.client.get_engine_client')
    def test_info_default_values(self, mock_rpc, mock_context, mock_filter):
        x_rpc = mock_rpc.return_value
        recover_action = {'operation': 'REBUILD'}
        endpoint = nova_endpoint.NovaNotificationEndpoint(
            'PROJECT', 'CLUSTER_ID', recover_action
        )
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


@mock.patch(
    'senlin.engine.notifications.heat_endpoint.HeatNotificationEndpoint')
@mock.patch(
    'senlin.engine.notifications.nova_endpoint.NovaNotificationEndpoint')
@mock.patch('oslo_messaging.get_notification_transport')
@mock.patch('oslo_messaging.get_notification_listener')
class TestListenerProc(base.SenlinTestCase):

    def test_listener_proc_nova(self, mock_listener, mock_transport,
                                mock_novaendpoint, mock_heatendpoint):
        cfg.CONF.set_override('nova_control_exchange', 'FAKE_EXCHANGE',
                              group='health_manager')

        x_listener = mock.Mock()
        mock_listener.return_value = x_listener
        x_transport = mock.Mock()
        mock_transport.return_value = x_transport
        x_endpoint = mock.Mock()
        mock_novaendpoint.return_value = x_endpoint

        recover_action = {'operation': 'REBUILD'}
        res = hm.ListenerProc('FAKE_EXCHANGE', 'PROJECT_ID', 'CLUSTER_ID',
                              recover_action)

        self.assertIsNone(res)
        mock_transport.assert_called_once_with(cfg.CONF)
        mock_novaendpoint.assert_called_once_with('PROJECT_ID', 'CLUSTER_ID',
                                                  recover_action)
        mock_listener.assert_called_once_with(
            x_transport, [mock_novaendpoint().target], [x_endpoint],
            executor='threading', pool="senlin-listeners")
        x_listener.start.assert_called_once_with()

    def test_listener_proc_heat(self, mock_listener, mock_transport,
                                mock_novaendpoint, mock_heatendpoint):
        x_listener = mock.Mock()
        mock_listener.return_value = x_listener
        x_transport = mock.Mock()
        mock_transport.return_value = x_transport
        x_endpoint = mock.Mock()
        mock_heatendpoint.return_value = x_endpoint

        recover_action = {'operation': 'REBUILD'}
        res = hm.ListenerProc('heat', 'PROJECT_ID', 'CLUSTER_ID',
                              recover_action)

        self.assertIsNone(res)
        mock_transport.assert_called_once_with(cfg.CONF)
        mock_heatendpoint.assert_called_once_with('PROJECT_ID', 'CLUSTER_ID',
                                                  recover_action)
        mock_listener.assert_called_once_with(
            x_transport, [mock_heatendpoint().target], [x_endpoint],
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
                    'type': 'HYPERVISOR_STATUS_POLLING',
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


class TestHypervisorPollStatusHealthCheck(base.SenlinTestCase):
    def setUp(self):
        super(TestHypervisorPollStatusHealthCheck, self).setUp()

        self.hc = hm.HypervisorPollStatusHealthCheck(
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


class TestHealthCheck(base.SenlinTestCase):

    def setUp(self):
        super(TestHealthCheck, self).setUp()
        ctx = mock.Mock()
        self.fake_rpc = mock.Mock()
        with mock.patch.object(rpc_client, 'get_engine_client',
                               return_value=self.fake_rpc):
            self.hc = hm.HealthCheck(
                ctx=ctx,
                engine_id='ENGINE_ID',
                cluster_id='CID',
                check_type=consts.NODE_STATUS_POLLING,
                interval=60,
                node_update_timeout=60,
                params={
                    'node_update_timeout': 60,
                    'detection_modes': [
                        {'type': consts.NODE_STATUS_POLLING}
                    ],
                    'recovery_conditional': consts.ANY_FAILED
                },
                enabled=True)

    def test_get_health_check_types_polling(self):
        self.hc.get_health_check_types()
        self.assertEqual(consts.POLLING, self.hc.type)

    def test_get_health_check_types_events(self):
        self.hc.check_type = consts.LIFECYCLE_EVENTS
        self.hc.get_health_check_types()
        self.assertEqual(consts.EVENTS, self.hc.type)

    def test_get_recover_actions(self):
        self.hc.params = {
            'node_delete_timeout': 60,
            'node_force_recreate': True,
            'recover_action': [{'name': 'FAKE_RECOVER_ACTION'}]
        }
        self.hc.get_recover_actions()
        self.assertEqual(self.hc.params['node_delete_timeout'],
                         self.hc.recover_action['delete_timeout'])
        self.assertEqual(self.hc.params['node_force_recreate'],
                         self.hc.recover_action['force_recreate'])
        self.assertEqual(self.hc.params['recover_action'][0]['name'],
                         self.hc.recover_action['operation'])

    @mock.patch.object(obj_node.Node, 'get_all_by_cluster')
    @mock.patch.object(hm.HealthCheck, "_recover_node")
    @mock.patch.object(hm.HealthCheck, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_any_mode_healthy(
            self, mock_ctx, mock_get, mock_wait, mock_recover, mock_nodes):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID',
                              id='CID')
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

        for hc_mocks in hc_test_values:
            self.hc.health_check_types = hc_mocks

            mock_get.reset_mock()
            mock_ctx.reset_mock()
            mock_recover.reset_mock()
            mock_wait.reset_mock()

            # do it
            self.hc.execute_health_check()

            mock_get.assert_called_once_with(self.hc.ctx, 'CID',
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
    @mock.patch.object(hm.HealthCheck, "_recover_node")
    @mock.patch.object(hm.HealthCheck, "_wait_for_action")
    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_all_mode_unhealthy(
            self, mock_ctx, mock_get, mock_wait, mock_recover, mock_nodes):
        self.hc.cluster_id = 'CLUSTER_ID'
        self.hc.interval = 1
        self.hc.recovery_cond = consts.ALL_FAILED
        self.hc.node_update_timeout = 1
        self.hc.recovery_action = {'operation': 'REBUILD'}

        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID',
                              id='CLUSTER_ID')
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
            ]
        ]

        for hc_mocks in hc_test_values:
            self.hc.health_check_types = hc_mocks

            mock_get.reset_mock()
            mock_ctx.reset_mock()
            mock_recover.reset_mock()
            mock_wait.reset_mock()

            # do it
            self.hc.execute_health_check()

            mock_get.assert_called_once_with(self.hc.ctx, 'CLUSTER_ID',
                                             project_safe=False)
            mock_ctx.assert_called_once_with(user_id=x_cluster.user,
                                             project_id=x_cluster.project)

            for mock_hc in hc_mocks:
                mock_hc.run_health_check.assert_has_calls(
                    [
                        mock.call(ctx, x_node)
                    ]
                )

            mock_recover.assert_called_once_with(ctx, 'FAKE_NODE')
            mock_wait.assert_called_once_with(
                ctx, 'FAKE_ACTION_ID', self.hc.node_update_timeout)

    @mock.patch.object(obj_cluster.Cluster, 'get')
    @mock.patch.object(context, 'get_service_context')
    def test_execute_health_check_cluster_not_found(self, mock_ctx, mock_get):
        mock_get.return_value = None

        self.hc.execute_health_check()

        mock_ctx.assert_not_called()

    @mock.patch.object(hm.HealthCheck, "_recover_node")
    def test_check_node_health_any_failed(self, mock_recover):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID',
                              id='CLUSTER_ID')
        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        ctx = mock.Mock()

        self.hc.params['recovery_conditional'] = consts.ANY_FAILED
        mock_hc_1 = mock.Mock()
        mock_hc_1.run_health_check.return_value = True
        mock_hc_2 = mock.Mock()
        mock_hc_2.run_health_check.return_value = False

        self.hc.health_check_types = [mock_hc_1, mock_hc_2]

        self.hc._check_node_health(ctx, x_node, x_cluster)

        mock_hc_1.run_health_check.assert_called_once_with(ctx, x_node)
        mock_hc_2.run_health_check.assert_called_once_with(ctx, x_node)
        mock_recover.assert_called_once_with(ctx, x_node.id)

    @mock.patch.object(hm.HealthCheck, "_recover_node")
    def test_check_node_health_all_failed(self, mock_recover):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID',
                              id='CLUSTER_ID')
        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        ctx = mock.Mock()

        self.hc.params['recovery_conditional'] = consts.ALL_FAILED
        mock_hc_1 = mock.Mock()
        mock_hc_1.run_health_check.return_value = False
        mock_hc_2 = mock.Mock()
        mock_hc_2.run_health_check.return_value = False

        self.hc.health_check_types = [mock_hc_1, mock_hc_2]

        self.hc._check_node_health(ctx, x_node, x_cluster)

        mock_hc_1.run_health_check.assert_called_once_with(ctx, x_node)
        mock_hc_2.run_health_check.assert_called_once_with(ctx, x_node)
        mock_recover.assert_called_once_with(ctx, x_node.id)

    @mock.patch.object(hm.HealthCheck, "_recover_node")
    def test_check_node_health_all_failed_negative(self, mock_recover):
        x_cluster = mock.Mock(user='USER_ID', project='PROJECT_ID',
                              id='CLUSTER_ID')
        x_node = mock.Mock(id='FAKE_NODE', status="ERROR")
        ctx = mock.Mock()

        self.hc.params['recovery_conditional'] = consts.ALL_FAILED
        mock_hc_1 = mock.Mock()
        mock_hc_1.run_health_check.return_value = False
        mock_hc_2 = mock.Mock()
        mock_hc_2.run_health_check.return_value = True

        self.hc.health_check_types = [mock_hc_1, mock_hc_2]

        self.hc._check_node_health(ctx, x_node, x_cluster)

        mock_hc_1.run_health_check.assert_called_once_with(ctx, x_node)
        mock_hc_2.run_health_check.assert_called_once_with(ctx, x_node)
        mock_recover.assert_not_called()

    @mock.patch('senlin.objects.ActionGetRequest')
    def test_wait_for_action(self, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_SUCCEEDED}
        self.fake_rpc.call.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hc._wait_for_action(ctx, action_id, timeout)

        self.assertTrue(res)
        self.assertEqual(err, '')
        self.fake_rpc.call.assert_called_with(ctx, 'action_get', x_req)

    @mock.patch('senlin.objects.ActionGetRequest')
    def test_wait_for_action_success_before_timeout(self, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action1 = {'status': consts.ACTION_RUNNING}
        x_action2 = {'status': consts.ACTION_SUCCEEDED}
        self.fake_rpc.call.side_effect = [x_action1, x_action2]

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hc._wait_for_action(ctx, action_id, timeout)

        self.assertTrue(res)
        self.assertEqual(err, '')
        self.fake_rpc.call.assert_has_calls(
            [
                mock.call(ctx, 'action_get', x_req),
                mock.call(ctx, 'action_get', x_req)
            ]
        )

    @mock.patch('senlin.objects.ActionGetRequest')
    def test_wait_for_action_timeout(self, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_RUNNING}
        self.fake_rpc.call.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hc._wait_for_action(ctx, action_id, timeout)

        self.assertFalse(res)
        self.assertTrue(re.search('timeout', err, re.IGNORECASE))
        self.fake_rpc.call.assert_has_calls(
            [
                mock.call(ctx, 'action_get', x_req)
            ]
        )

    @mock.patch('senlin.objects.ActionGetRequest')
    def test_wait_for_action_failed(self, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_FAILED}
        self.fake_rpc.call.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hc._wait_for_action(ctx, action_id, timeout)

        self.assertFalse(res)
        self.assertEqual(err, 'Cluster check action failed or cancelled')
        self.fake_rpc.call.assert_called_with(ctx, 'action_get', x_req)

    @mock.patch('senlin.objects.ActionGetRequest')
    def test_wait_for_action_cancelled(self, mock_action_req):
        x_req = mock.Mock()
        mock_action_req.return_value = x_req

        x_action = {'status': consts.ACTION_CANCELLED}
        self.fake_rpc.call.return_value = x_action

        ctx = mock.Mock()
        action_id = 'FAKE_ACTION_ID'
        timeout = 5

        # do it
        res, err = self.hc._wait_for_action(ctx, action_id, timeout)

        self.assertFalse(res)
        self.assertEqual(err, 'Cluster check action failed or cancelled')
        self.fake_rpc.call.assert_called_with(ctx, 'action_get', x_req)

    @mock.patch('senlin.objects.NodeRecoverRequest', autospec=True)
    def test_recover_node(self, mock_req):
        ctx = mock.Mock()
        node_id = 'FAKE_NODE'
        self.hc.recover_action = {'operation': 'REBUILD'}

        x_req = mock.Mock
        mock_req.return_value = x_req

        x_action = {'action': 'RECOVER_ID1'}
        self.fake_rpc.call.return_value = x_action

        # do it
        res = self.hc._recover_node(ctx, node_id)

        self.assertEqual(x_action, res)
        mock_req.assert_called_once_with(
            identity=node_id, params=self.hc.recover_action)
        self.fake_rpc.call.assert_called_once_with(ctx, 'node_recover', x_req)

    @mock.patch('senlin.objects.NodeRecoverRequest', autospec=True)
    def test_recover_node_failed(self, mock_req):
        ctx = mock.Mock()
        node_id = 'FAKE_NODE'
        self.hc.recover_action = {'operation': 'REBUILD'}

        x_req = mock.Mock
        mock_req.return_value = x_req

        self.fake_rpc.call.side_effect = Exception('boom')

        # do it
        res = self.hc._recover_node(ctx, node_id)

        self.assertIsNone(res)
        mock_req.assert_called_once_with(
            identity=node_id, params=self.hc.recover_action)
        self.fake_rpc.call.assert_called_once_with(ctx, 'node_recover', x_req)

    @mock.patch('senlin.objects.HealthRegistry', autospec=True)
    def test_db_create(self, mock_hrdb):
        self.hc.db_create()
        mock_hrdb.create.assert_called_once_with(
            self.hc.ctx, self.hc.cluster_id, self.hc.check_type,
            self.hc.interval, self.hc.params, self.hc.engine_id,
            self.hc.enabled)

    @mock.patch('senlin.objects.HealthRegistry', autospec=True)
    def test_db_delete(self, mock_hrdb):
        self.hc.db_delete()
        mock_hrdb.delete.assert_called_once_with(self.hc.ctx,
                                                 self.hc.cluster_id)

    @mock.patch('senlin.objects.HealthRegistry', autospec=True)
    def test_enable(self, mock_hrdb):
        self.hc.enable()
        mock_hrdb.update.assert_called_once_with(
            self.hc.ctx, self.hc.cluster_id, {'enabled': True})

    @mock.patch('senlin.objects.HealthRegistry', autospec=True)
    def test_disable(self, mock_hrdb):
        self.hc.disable()
        mock_hrdb.update.assert_called_once_with(
            self.hc.ctx, self.hc.cluster_id, {'enabled': False})


class TestRuntimeHealthRegistry(base.SenlinTestCase):

    def setUp(self):
        super(TestRuntimeHealthRegistry, self).setUp()

        mock_ctx = mock.Mock()
        self.mock_tg = mock.Mock()
        self.rhr = hm.RuntimeHealthRegistry(mock_ctx, 'ENGINE_ID',
                                            self.mock_tg)

    def create_mock_entry(self, ctx=None, engine_id='ENGINE_ID',
                          cluster_id='CID',
                          check_type=None,
                          interval=60, node_update_timeout=60, params=None,
                          enabled=True, timer=None, listener=None,
                          type=consts.POLLING):
        mock_entry = mock.Mock(
            ctx=ctx,
            engine_id=engine_id,
            cluster_id=cluster_id,
            check_type=check_type,
            interval=interval,
            node_update_timeout=node_update_timeout,
            params=params,
            enabled=enabled,
            timer=timer,
            listener=listener,
            execute_health_check=mock.Mock(),
            type=type)
        return mock_entry

    @mock.patch.object(hm, 'HealthCheck')
    def test_register_cluster(self, mock_hc):
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING])
        mock_entry.db_create = mock.Mock()
        mock_hc.return_value = mock_entry

        self.rhr.register_cluster('CID', 60, 60, {})

        self.assertEqual(mock_entry, self.rhr.registries['CID'])
        self.mock_tg.add_dynamic_timer.assert_called_once_with(
            mock_entry.execute_health_check, None, None)
        self.mock_tg.add_thread.assert_not_called()
        mock_entry.db_create.assert_called_once_with()

    @mock.patch.object(hm, 'HealthCheck')
    def test_register_cluster_failed(self, mock_hc):
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING])
        mock_entry.db_create = mock.Mock()
        mock_entry.db_delete = mock.Mock()

        mock_hc.return_value = mock_entry
        self.rhr.add_health_check = mock.Mock()
        self.rhr.add_health_check.side_effect = Exception

        self.rhr.register_cluster('CID', 60, 60, {})

        self.assertEqual(mock_entry, self.rhr.registries['CID'])
        self.mock_tg.add_dynamic_timer.assert_not_called()
        self.mock_tg.add_thread.assert_not_called()
        mock_entry.db_create.assert_called_once_with()
        mock_entry.db_delete.assert_called_once_with()

    def test_unregister_cluster_with_timer(self):
        timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            timer=timer)
        self.rhr.registries['CID'] = mock_entry
        mock_entry.db_delete = mock.Mock()

        self.rhr.unregister_cluster('CID')

        mock_entry.db_delete.assert_called_once_with()
        timer.stop.assert_called_once_with()
        self.mock_tg.timer_done.assert_called_once_with(timer)
        self.assertIsNone(mock_entry.timer)

    def test_unregister_cluster_with_listener(self):
        listener = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            listener=listener)
        self.rhr.registries['CID'] = mock_entry
        mock_entry.db_delete = mock.Mock()

        self.rhr.unregister_cluster('CID')

        mock_entry.db_delete.assert_called_once_with()
        listener.stop.assert_called_once_with()
        self.mock_tg.thread_done.assert_called_once_with(listener)
        self.assertIsNone(mock_entry.listener)

    def test_unregister_cluster_failed(self):
        listener = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            listener=listener)
        self.rhr.registries['CID'] = mock_entry
        mock_entry.db_delete.side_effect = Exception

        self.rhr.unregister_cluster('CID')

        listener.stop.assert_called_once_with()
        self.mock_tg.thread_done.assert_called_once_with(listener)
        self.assertIsNone(mock_entry.listener)

    def test_enable_cluster(self):
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            enabled=False)

        def mock_enable():
            mock_entry.enabled = True
            return True

        mock_entry.enable = mock_enable

        self.rhr.registries['CID'] = mock_entry

        self.rhr.enable_cluster('CID')

        self.assertTrue(mock_entry.enabled)
        self.mock_tg.add_dynamic_timer.assert_called_once_with(
            mock_entry.execute_health_check, None, None)
        self.mock_tg.add_thread.assert_not_called()

    def test_enable_cluster_failed(self):
        timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            enabled=False, timer=timer)
        mock_entry.enable = mock.Mock()
        mock_entry.enable.side_effect = Exception

        self.rhr.registries['CID'] = mock_entry

        self.rhr.enable_cluster('CID')

        self.mock_tg.add_dynamic_timer.assert_not_called()
        self.mock_tg.add_thread.assert_not_called()
        timer.stop.assert_called_once_with()
        self.mock_tg.timer_done.assert_called_once_with(timer)

    def test_disable_cluster(self):
        timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            enabled=True, timer=timer)

        def mock_disable():
            mock_entry.enabled = False

        mock_entry.disable = mock_disable

        self.rhr.registries['CID'] = mock_entry

        self.rhr.disable_cluster('CID')

        self.assertEqual(False, mock_entry.enabled)

        self.mock_tg.add_dynamic_timer.assert_not_called()
        self.mock_tg.add_thread.assert_not_called()
        timer.stop.assert_called_once_with()
        self.mock_tg.timer_done.assert_called_once_with(timer)

    def test_disable_cluster_failed(self):
        timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING],
            enabled=True, timer=timer)

        mock_entry.enable.side_effect = Exception

        self.rhr.registries['CID'] = mock_entry

        self.rhr.disable_cluster('CID')

        self.mock_tg.add_dynamic_timer.assert_not_called()
        self.mock_tg.add_thread.assert_not_called()
        timer.stop.assert_called_once_with()
        self.mock_tg.timer_done.assert_called_once_with(timer)

    def test_add_timer(self):
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING])
        self.rhr.registries['CID'] = mock_entry
        fake_timer = mock.Mock()
        self.mock_tg.add_dynamic_timer = mock.Mock()
        self.mock_tg.add_dynamic_timer.return_value = fake_timer

        self.rhr._add_timer('CID')

        self.assertEqual(fake_timer, mock_entry.timer)
        self.mock_tg.add_dynamic_timer.assert_called_once_with(
            mock_entry.execute_health_check, None, None)

    def test_add_timer_failed(self):
        fake_timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING], timer=fake_timer)
        self.rhr.registries['CID'] = mock_entry
        self.mock_tg.add_dynamic_timer = mock.Mock()

        self.rhr._add_timer('CID')

        self.assertEqual(fake_timer, mock_entry.timer)
        self.mock_tg.add_dynamic_timer.assert_not_called()

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test_add_listener_nova(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('nova_control_exchange', 'FAKE_NOVA_EXCHANGE',
                              group='health_manager')
        mock_entry = self.create_mock_entry(
            check_type=[consts.LIFECYCLE_EVENTS])
        self.rhr.registries['CID'] = mock_entry
        fake_listener = mock.Mock()
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type='os.nova.server-1.0')
        mock_profile.return_value = x_profile
        self.mock_tg.add_thread = mock.Mock()
        self.mock_tg.add_thread.return_value = fake_listener

        self.rhr._add_listener('CID')

        mock_cluster.assert_called_once_with(self.rhr.ctx, 'CID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.rhr.ctx, 'PROFILE_ID',
                                             project_safe=False)
        self.mock_tg.add_thread.assert_called_once_with(
            hm.ListenerProc, 'FAKE_NOVA_EXCHANGE', 'PROJECT_ID', 'CID',
            mock_entry.recover_action)

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test_add_listener_heat(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('heat_control_exchange', 'FAKE_HEAT_EXCHANGE',
                              group='health_manager')
        mock_entry = self.create_mock_entry(
            check_type=[consts.LIFECYCLE_EVENTS])
        self.rhr.registries['CID'] = mock_entry
        fake_listener = mock.Mock()
        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type='os.heat.stack-1.0')
        mock_profile.return_value = x_profile
        self.mock_tg.add_thread = mock.Mock()
        self.mock_tg.add_thread.return_value = fake_listener

        self.rhr._add_listener('CID')

        mock_cluster.assert_called_once_with(self.rhr.ctx, 'CID',
                                             project_safe=False)
        mock_profile.assert_called_once_with(self.rhr.ctx, 'PROFILE_ID',
                                             project_safe=False)
        self.mock_tg.add_thread.assert_called_once_with(
            hm.ListenerProc, 'FAKE_HEAT_EXCHANGE', 'PROJECT_ID', 'CID',
            mock_entry.recover_action)

    @mock.patch.object(obj_profile.Profile, 'get')
    @mock.patch.object(obj_cluster.Cluster, 'get')
    def test_add_listener_failed(self, mock_cluster, mock_profile):
        cfg.CONF.set_override('heat_control_exchange', 'FAKE_HEAT_EXCHANGE',
                              group='health_manager')
        fake_listener = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.LIFECYCLE_EVENTS], listener=fake_listener)
        self.rhr.registries['CID'] = mock_entry

        x_cluster = mock.Mock(project='PROJECT_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        x_profile = mock.Mock(type='os.heat.stack-1.0')
        mock_profile.return_value = x_profile
        self.mock_tg.add_thread = mock.Mock()

        self.rhr._add_listener('CID')

        mock_cluster.assert_not_called()
        mock_profile.assert_not_called()

        self.mock_tg.add_thread.assert_not_called()

    def test_add_health_check_polling(self):
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING])
        self.rhr.registries['CID'] = mock_entry
        self.rhr._add_timer = mock.Mock()
        self.rhr._add_listener = mock.Mock()

        self.rhr.add_health_check(mock_entry)

        self.rhr._add_timer.assert_called_once_with('CID')
        self.rhr._add_listener.assert_not_called()

    def test_add_health_check_events(self):
        mock_entry = self.create_mock_entry(
            check_type=[consts.LIFECYCLE_EVENTS], type=consts.EVENTS)
        self.rhr.registries['CID'] = mock_entry
        self.rhr._add_timer = mock.Mock()
        self.rhr._add_listener = mock.Mock()

        self.rhr.add_health_check(mock_entry)

        self.rhr._add_timer.assert_not_called()
        self.rhr._add_listener.assert_called_once_with('CID')

    def test_add_health_check_disabled(self):
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING], enabled=False)
        self.rhr.registries['CID'] = mock_entry
        self.rhr._add_timer = mock.Mock()
        self.rhr._add_listener = mock.Mock()

        self.rhr.add_health_check(mock_entry)

        self.rhr._add_timer.assert_not_called()
        self.rhr._add_listener.assert_not_called()

    def test_add_health_check_timer_exists(self):
        fake_timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING], timer=fake_timer)
        self.rhr.registries['CID'] = mock_entry
        self.rhr._add_timer = mock.Mock()
        self.rhr._add_listener = mock.Mock()

        self.rhr.add_health_check(mock_entry)

        self.rhr._add_timer.assert_not_called()
        self.rhr._add_listener.assert_not_called()

    def test_remove_health_check_timer(self):
        fake_timer = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING], timer=fake_timer)
        self.rhr.registries['CID'] = mock_entry

        self.rhr.remove_health_check(mock_entry)

        fake_timer.stop.assert_called_once_with()
        self.mock_tg.timer_done.assert_called_once_with(fake_timer)
        self.mock_tg.thread_done.assert_not_called()
        self.assertIsNone(mock_entry.timer)

    def test_remove_health_check_listener(self):
        fake_listener = mock.Mock()
        mock_entry = self.create_mock_entry(
            check_type=[consts.NODE_STATUS_POLLING], listener=fake_listener)
        self.rhr.registries['CID'] = mock_entry

        self.rhr.remove_health_check(mock_entry)

        fake_listener.stop.assert_called_once_with()
        self.mock_tg.timer_done.assert_not_called()
        self.mock_tg.thread_done.assert_called_once_with(fake_listener)
        self.assertIsNone(mock_entry.listener)
