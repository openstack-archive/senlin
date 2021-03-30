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

from collections import namedtuple
import copy
from unittest import mock


from oslo_config import cfg

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common import scaleutils as su
from senlin.engine import health_manager
from senlin.policies import base as pb
from senlin.policies import health_policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestHealthPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestHealthPolicy, self).setUp()
        self.context = utils.dummy_context()

        self.spec = {
            'type': 'senlin.policy.health',
            'version': '1.2',
            'properties': {
                'detection': {
                    "detection_modes": [
                        {
                            'type': 'NODE_STATUS_POLLING'
                        },
                    ],
                    'interval': 60
                },
                'recovery': {
                    'fencing': ['COMPUTE'],
                    'actions': [
                        {'name': 'REBUILD'}
                    ]
                }
            }
        }

        fake_profile = mock.Mock(type_name='os.nova.server',
                                 type='os.nova.server-1.0',)
        fake_node = mock.Mock(status='ACTIVE')
        fake_cluster = mock.Mock(id='CLUSTER_ID', nodes=[fake_node],
                                 rt={'profile': fake_profile})
        self.cluster = fake_cluster
        self.patch('senlin.rpc.client.get_engine_client')
        self.hp = health_policy.HealthPolicy('test-policy', self.spec)

    def test_policy_init(self):
        DetectionMode = namedtuple(
            'DetectionMode',
            [self.hp.DETECTION_TYPE] + list(self.hp._DETECTION_OPTIONS))

        detection_modes = [
            DetectionMode(
                type='NODE_STATUS_POLLING',
                poll_url='',
                poll_url_ssl_verify=True,
                poll_url_conn_error_as_unhealthy=True,
                poll_url_healthy_response='',
                poll_url_retry_limit='',
                poll_url_retry_interval=''
            )
        ]

        spec = {
            'type': 'senlin.policy.health',
            'version': '1.2',
            'properties': {
                'detection': {
                    "detection_modes": [
                        {
                            'type': 'NODE_STATUS_POLLING'
                        },
                    ],
                    'interval': 60
                },
                'recovery': {
                    'fencing': ['COMPUTE'],
                    'actions': [
                        {'name': 'REBUILD'}
                    ]
                }
            }
        }

        hp = health_policy.HealthPolicy('test-policy', spec)

        self.assertIsNone(hp.id)
        self.assertEqual('test-policy', hp.name)
        self.assertEqual('senlin.policy.health-1.2', hp.type)
        self.assertEqual(detection_modes, hp.detection_modes)
        self.assertEqual(60, hp.interval)
        self.assertEqual([{'name': 'REBUILD', 'params': None}],
                         hp.recover_actions)

    def test_policy_init_ops(self):
        spec = {
            'type': 'senlin.policy.health',
            'version': '1.2',
            'properties': {
                'detection': {
                    "detection_modes": [
                        {
                            'type': 'NODE_STATUS_POLLING'
                        },
                        {
                            'type': 'HYPERVISOR_STATUS_POLLING'
                        },
                        {
                            'type': 'NODE_STATUS_POLL_URL'
                        },
                    ],
                    'interval': 60
                },
                'recovery': {
                    'fencing': ['COMPUTE'],
                    'actions': [
                        {'name': 'REBUILD'}
                    ]
                }
            }
        }

        operations = [None, 'ALL_FAILED', 'ANY_FAILED']
        for op in operations:
            # set operation in spec
            if op:
                spec['properties']['detection']['recovery_conditional'] = op

            # test __init__
            hp = health_policy.HealthPolicy('test-policy', spec)

            # check result
            self.assertIsNone(hp.id)
            self.assertEqual('test-policy', hp.name)
            self.assertEqual('senlin.policy.health-1.2', hp.type)
            self.assertEqual(60, hp.interval)
            self.assertEqual([{'name': 'REBUILD', 'params': None}],
                             hp.recover_actions)

    def test_validate(self):
        spec = copy.deepcopy(self.spec)
        spec["properties"]["recovery"]["actions"] = [
            {"name": "REBUILD"}, {"name": "RECREATE"}
        ]
        self.hp = health_policy.HealthPolicy('test-policy', spec)

        ex = self.assertRaises(exc.ESchema,
                               self.hp.validate,
                               self.context)

        self.assertEqual("Only one 'actions' is supported for now.",
                         str(ex))

    def test_validate_valid_interval(self):
        spec = copy.deepcopy(self.spec)
        spec["properties"]["detection"]["interval"] = 20
        self.hp = health_policy.HealthPolicy('test-policy', spec)

        cfg.CONF.set_override('health_check_interval_min', 20)

        self.hp.validate(self.context)

    def test_validate_invalid_interval(self):
        spec = copy.deepcopy(self.spec)
        spec["properties"]["detection"]["interval"] = 10
        self.hp = health_policy.HealthPolicy('test-policy', spec)

        cfg.CONF.set_override('health_check_interval_min', 20)

        ex = self.assertRaises(exc.InvalidSpec,
                               self.hp.validate,
                               self.context)

        expected_error = ("Specified interval of %(interval)d seconds has to "
                          "be larger than health_check_interval_min of "
                          "%(min_interval)d seconds set in configuration."
                          ) % {"interval": 10, "min_interval": 20}
        self.assertEqual(expected_error, str(ex))

    @mock.patch.object(health_manager, 'register')
    def test_attach(self, mock_hm_reg):

        policy_data = {
            'HealthPolicy': {
                'data': {
                    'interval': self.hp.interval,
                    'detection_modes': [
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
                    'node_delete_timeout': 20,
                    'node_force_recreate': False,
                    'recovery_conditional': 'ANY_FAILED'
                },
                'version': '1.2'
            }
        }

        res, data = self.hp.attach(self.cluster)
        self.assertTrue(res)
        self.assertEqual(policy_data, data)
        kwargs = {
            'interval': self.hp.interval,
            'node_update_timeout': 300,
            'params': {
                'recover_action': self.hp.recover_actions,
                'node_delete_timeout': 20,
                'node_force_recreate': False,
                'recovery_conditional': 'ANY_FAILED',
                'detection_modes': [
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
            },
            'enabled': True
        }
        mock_hm_reg.assert_called_once_with('CLUSTER_ID',
                                            engine_id=None,
                                            **kwargs)

    @mock.patch.object(health_manager, 'register')
    def test_attach_failed_action_matching_rebuild(self, mock_hm_reg):

        fake_profile = mock.Mock(type_name='os.heat.stack-1.0',
                                 type='os.heat.stack')
        fake_cluster = mock.Mock(id='CLUSTER_ID', rt={'profile': fake_profile})

        res, data = self.hp.attach(fake_cluster)

        self.assertFalse(res)
        self.assertEqual("Recovery action REBUILD is only applicable to "
                         "os.nova.server clusters.", data)

    @mock.patch.object(health_manager, 'register')
    def test_attach_failed_action_matching_reboot(self, mock_hm_reg):
        spec = copy.deepcopy(self.spec)
        spec['properties']['recovery']['actions'] = [{'name': 'REBOOT'}]
        hp = health_policy.HealthPolicy('test-policy-1', spec)

        fake_profile = mock.Mock(type_name='os.heat.stack-1.0',
                                 type='os.heat.stack')
        fake_cluster = mock.Mock(id='CLUSTER_ID', rt={'profile': fake_profile})

        res, data = hp.attach(fake_cluster)

        self.assertFalse(res)
        self.assertEqual("Recovery action REBOOT is only applicable to "
                         "os.nova.server clusters.", data)

    @mock.patch.object(health_manager, 'register')
    def test_attach_failed_with_notify_timeout(self, mock_hm_reg):
        mock_hm_reg.return_value = False
        res, data = self.hp.attach(self.cluster)
        self.assertFalse(res)
        self.assertEqual("Registering health manager for cluster timed "
                         "out.", data)

    @mock.patch.object(health_manager, 'unregister')
    def test_detach(self, mock_hm_unreg):
        res, data = self.hp.detach(self.cluster)
        self.assertTrue(res)
        self.assertEqual('', data)
        mock_hm_unreg.assert_called_once_with('CLUSTER_ID')

    @mock.patch.object(health_manager, 'unregister')
    def test_detach_failed_with_notify_timeout(self, mock_hm_unreg):
        mock_hm_unreg.return_value = False
        res, data = self.hp.detach(self.cluster)
        self.assertFalse(res)
        self.assertEqual("Unregistering health manager for cluster timed "
                         "out.", data)
        mock_hm_unreg.assert_called_once_with('CLUSTER_ID')

    def test_pre_op_default(self):
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_SCALE_OUT)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        data = {
            'health': {
                'recover_action': [{'name': 'REBUILD', 'params': None}],
                'fencing': ['COMPUTE'],
            }
        }
        self.assertEqual(data, action.data)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_scale_in(self, mock_disable):
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_SCALE_IN)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_update(self, mock_disable):
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_UPDATE)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_cluster_recover(self, mock_disable):
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_RECOVER)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_cluster_replace_nodes(self, mock_disable):
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_REPLACE_NODES)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_cluster_del_nodes(self, mock_disable):
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_DEL_NODES)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_node_delete(self, mock_disable):
        action = mock.Mock(context='action_context', data={},
                           action=consts.NODE_DELETE)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_resize_with_data(self, mock_disable):
        action = mock.Mock(context='action_context', data={'deletion': 'foo'},
                           action=consts.CLUSTER_RESIZE)

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(su, 'parse_resize_params')
    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_resize_without_data(self, mock_disable, mock_parse):
        def fake_check(action, cluster, current):
            action.data['deletion'] = {'foo': 'bar'}
            return pb.CHECK_OK, 'good'

        x_cluster = mock.Mock()
        x_cluster.nodes = [mock.Mock(), mock.Mock(), mock.Mock()]
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_RESIZE)
        action.entity = x_cluster
        mock_parse.side_effect = fake_check

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(self.cluster.id)
        mock_parse.assert_called_once_with(action, x_cluster, 3)

    @mock.patch.object(su, 'parse_resize_params')
    @mock.patch.object(health_manager, 'disable')
    def test_pre_op_resize_parse_error(self, mock_disable, mock_parse):
        x_cluster = mock.Mock()
        x_cluster.nodes = [mock.Mock(), mock.Mock()]
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_RESIZE)
        action.entity = x_cluster
        mock_parse.return_value = pb.CHECK_ERROR, 'no good'

        res = self.hp.pre_op(self.cluster.id, action)

        self.assertFalse(res)
        self.assertEqual(pb.CHECK_ERROR, action.data['status'])
        self.assertEqual('no good', action.data['reason'])
        mock_parse.assert_called_once_with(action, x_cluster, 2)
        self.assertEqual(0, mock_disable.call_count)

    def test_post_op_default(self):
        action = mock.Mock(action='FAKE_ACTION')

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)

    @mock.patch.object(health_manager, 'enable')
    def test_post_op_scale_in(self, mock_enable):
        action = mock.Mock(action=consts.CLUSTER_SCALE_IN)

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'enable')
    def test_post_op_update(self, mock_enable):
        action = mock.Mock(action=consts.CLUSTER_UPDATE)

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'enable')
    def test_post_op_cluster_recover(self, mock_enable):
        action = mock.Mock(action=consts.CLUSTER_RECOVER)

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'enable')
    def test_post_op_cluster_replace_nodes(self, mock_enable):
        action = mock.Mock(action=consts.CLUSTER_REPLACE_NODES)

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'enable')
    def test_post_op_cluster_del_nodes(self, mock_enable):
        action = mock.Mock(action=consts.CLUSTER_DEL_NODES)

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(health_manager, 'enable')
    def test_post_op_node_delete(self, mock_enable):
        action = mock.Mock(action=consts.NODE_DELETE)

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)

    @mock.patch.object(su, 'parse_resize_params')
    @mock.patch.object(health_manager, 'enable')
    def test_post_op_resize_without_data(self, mock_enable, mock_parse):
        def fake_check(action, cluster, current):
            action.data['deletion'] = {'foo': 'bar'}
            return pb.CHECK_OK, 'good'

        x_cluster = mock.Mock()
        x_cluster.nodes = [mock.Mock(), mock.Mock()]
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_RESIZE)
        action.entity = x_cluster
        mock_parse.side_effect = fake_check

        res = self.hp.post_op(self.cluster.id, action)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(self.cluster.id)
        mock_parse.assert_called_once_with(action, x_cluster, 2)

    @mock.patch.object(su, 'parse_resize_params')
    @mock.patch.object(health_manager, 'enable')
    def test_post_op_resize_parse_error(self, mock_enable, mock_parse):
        x_cluster = mock.Mock()
        x_cluster.nodes = [mock.Mock()]
        action = mock.Mock(context='action_context', data={},
                           action=consts.CLUSTER_RESIZE)
        action.entity = x_cluster
        mock_parse.return_value = pb.CHECK_ERROR, 'no good'

        res = self.hp.post_op(self.cluster.id, action)

        self.assertFalse(res)
        self.assertEqual(pb.CHECK_ERROR, action.data['status'])
        self.assertEqual('no good', action.data['reason'])

        mock_parse.assert_called_once_with(action, x_cluster, 1)
        self.assertEqual(0, mock_enable.call_count)
