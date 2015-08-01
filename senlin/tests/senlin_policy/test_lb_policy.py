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
from oslo_context import context as oslo_context
import six

from senlin.common import consts
from senlin.common import context
from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.drivers.openstack import lbaas as lb_driver
from senlin.engine import cluster_policy
from senlin.engine import node as node_mod
from senlin.policies import base as policy_base
from senlin.policies import lb_policy
from senlin.tests.common import base
from senlin.tests.common import utils


class TestLoadBalancingPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestLoadBalancingPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'pool': {
                'protocol': 'HTTP',
                'protocol_port': 80,
                'subnet': 'test-subnet',
                'lb_method': 'ROUND_ROBIN',
                'admin_state_up': True,
                'session_persistence': {
                    'type': 'SOURCE_IP',
                    'cookie_name': 'whatever'
                }
            },
            'vip': {
                'address': '192.168.1.100',
                'subnet': 'test-subnet',
                'connection_limit': 500,
                'protocol': 'HTTP',
                'protocol_port': 80,
                'admin_state_up': True,
            }
        }

    @mock.patch.object(lb_policy.LoadBalancingPolicy, 'validate')
    def test_lb_policy_init(self, mock_validate):
        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('LoadBalancingPolicy', policy.type)
        self.assertEqual(self.spec['pool'], policy.pool_spec)
        self.assertEqual(self.spec['vip'], policy.vip_spec)
        self.assertIsNone(policy.lb)
        mock_validate.assert_called_once_with()

    def test_lb_policy_init_default_value(self):
        kwargs = {
            'spec': {
                'pool': {'subnet': 'test-subnet'},
                'vip': {'subnet': 'test-subnet'}
            }
        }
        default_spec = {
            'pool': {
                'protocol': 'HTTP',
                'protocol_port': 80,
                'subnet': 'test-subnet',
                'lb_method': 'ROUND_ROBIN',
                'admin_state_up': True,
                'session_persistence': {},
            },
            'vip': {
                'address': None,
                'subnet': 'test-subnet',
                'connection_limit': -1,
                'protocol': 'HTTP',
                'protocol_port': 80,
                'admin_state_up': True,
            }

        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('LoadBalancingPolicy', policy.type)
        self.assertEqual(default_spec['pool'], policy.pool_spec)
        self.assertEqual(default_spec['vip'], policy.vip_spec)
        self.assertIsNone(policy.lb)

    @mock.patch.object(policy_base.Policy, 'validate')
    def test_lb_policy_validate(self, mock_validate):
        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        policy.validate()
        mock_validate.assert_called_with()

    @mock.patch.object(db_api, 'cred_get')
    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(context.RequestContext, 'from_dict')
    @mock.patch.object(oslo_context, 'get_current')
    def test_lb_policy_build_context(self, mock_get_current, mock_from_dict,
                                     mock_get_service_context, mock_cred_get):
        service_ctx = {
            'auth_url': 'AUTH_URL',
            'user_name': 'senlin',
            'user_domain_name': 'default',
            'password': '123'
        }
        current_ctx = {
            'auth_url': 'AUTH_URL',
            'user_name': 'user1',
            'user_domain_name': 'default',
            'password': '456'
        }
        cred_info = {
            'openstack': {
                'trust': {
                    'id': 'TRUST_ID',
                    'trustor': 'user1',
                    'trustee': 'senlin'
                }
            }
        }

        cluster = mock.Mock()
        cluster.user = 'user1'
        cluster.project = 'project1'
        cred = mock.Mock()
        cred.cred = cred_info
        mock_get_service_context.return_value = service_ctx
        mock_get_current.return_value = current_ctx
        mock_cred_get.return_value = cred
        mock_from_dict.return_value = 'context_result'

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy._build_context(cluster)
        self.assertEqual('context_result', res)
        mock_get_service_context.assert_called_once_with()
        mock_cred_get.assert_called_once_with(current_ctx, 'user1', 'project1')
        params = {
            'auth_url': service_ctx['auth_url'],
            'user_name': service_ctx['user_name'],
            'user_domain_name': service_ctx['user_domain_name'],
            'password': service_ctx['password'],
            'trusts': [cred_info['openstack']['trust']],
            'project_id': cluster.project
        }
        mock_from_dict.assert_called_once_with(params)

    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(db_api, 'cred_get')
    def test_lb_policy_build_context_trust_not_found(
            self, mock_cred_get, mock_get_service_context):

        self.patchobject(oslo_context, 'get_current')
        mock_cred_get.return_value = None
        cluster = mock.Mock()
        cluster.user = 'user1'
        cluster.project = 'project1'

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        ex = self.assertRaises(exception.TrustNotFound, policy._build_context,
                               cluster)
        msg = "The trust for trustor (user1) could not be found."
        self.assertEqual(msg, six.text_type(ex))

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_build_policy_data')
    @mock.patch.object(node_mod.Node, 'load_all')
    @mock.patch.object(policy_base.Policy, 'attach')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_attach_succeeded(self, mock_lb_driver,
                                        mock_policy_base_attach,
                                        mock_node_load_all,
                                        mock_build_policy_data):
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node2 = mock.Mock()
        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        mock_policy_base_attach.return_value = (True, None)
        mock_node_load_all.return_value = [node1, node2]
        mock_build_policy_data.return_value = 'policy_data'
        data = {
            'loadbalancer': 'LB_ID',
            'pool': 'POOL_ID'
        }
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        lb_driver.lb_create.return_value = (True, data)
        lb_driver.member_add.side_effect = ['MEMBER1_ID', 'MEMBER2_ID']
        res, data = policy.attach(cluster)
        self.assertTrue(res)
        self.assertEqual('policy_data', data)
        lb_driver.lb_create.assert_called_once_with(policy.vip_spec,
                                                    policy.pool_spec)
        mock_node_load_all.assert_called_once_with(mock.ANY,
                                                   cluster_id='CLUSTER_ID')
        calls_member_add = [mock.call(n, 'LB_ID', 'POOL_ID', 80, 'test-subnet'
                                      ) for n in [node1, node2]]
        lb_driver.member_add.assert_has_calls(calls_member_add)
        node1.data.update.assert_called_once_with({'lb_member': 'MEMBER1_ID'})
        node2.data.update.assert_called_once_with({'lb_member': 'MEMBER2_ID'})
        node1.store.assert_called_once_with(mock.ANY)
        node2.store.assert_called_once_with(mock.ANY)

    @mock.patch.object(policy_base.Policy, 'attach')
    def test_lb_policy_attach_failed_base_policy_attach_return_false(
            self, mock_policy_base_attach):

        cluster = mock.Mock()
        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        # Base policy attaching return False
        mock_policy_base_attach.return_value = (False, 'data')
        res, data = policy.attach(cluster)
        self.assertFalse(res)
        self.assertEqual('data', data)

    @mock.patch.object(policy_base.Policy, 'attach')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_attach_failed_lb_creation_failed(
            self, mock_lb_driver, mock_policy_base_attach):

        cluster = mock.Mock()
        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        mock_policy_base_attach.return_value = (True, None)
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        # lb_driver.lb_create return False
        lb_driver.lb_create.return_value = (False, 'data')
        res, data = policy.attach(cluster)
        self.assertFalse(res)
        self.assertEqual('data', data)

    @mock.patch.object(node_mod.Node, 'load_all')
    @mock.patch.object(policy_base.Policy, 'attach')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_attach_failed_member_add_failed(
            self, mock_lb_driver, mock_policy_base_attach, mock_node_load_all):

        cluster = mock.Mock()
        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        mock_policy_base_attach.return_value = (True, None)
        mock_node_load_all.return_value = ['node1', 'node2']
        lb_data = {
            'loadbalancer': 'LB_ID',
            'pool': 'POOL_ID'
        }
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        # lb_driver.member_add return None
        lb_driver.lb_create.return_value = (True, lb_data)
        lb_driver.member_add.return_value = None
        res, data = policy.attach(cluster)
        self.assertFalse(res)
        self.assertEqual('Failed in adding node into lb pool', data)
        lb_driver.lb_delete.assert_called_once_with(**lb_data)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    def test_lb_policy_detach_succeeded_no_policy_data(
            self, mock_policy_load, mock_extract_policy_data):

        cluster = mock.Mock()
        cp = mock.Mock()
        mock_policy_load.return_value = cp
        mock_extract_policy_data.return_value = None
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(lb_driver, 'LoadBalancerDriver')
        self.patchobject(oslo_context, 'get_current')

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        res, data = policy.detach(cluster)
        self.assertTrue(res)
        self.assertEqual('LB resources deletion succeeded.', data)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_detach_succeeded_lb_delete_succeeded(
            self, mock_lb_driver, mock_cluster_policy_load,
            mock_extract_policy_data):

        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0',
                'data': policy_data
            }
        }
        cp.data = cp_data
        mock_cluster_policy_load.return_value = cp
        mock_extract_policy_data.return_value = policy_data
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(oslo_context, 'get_current')
        lb_driver.lb_delete.return_value = (True, 'lb_delete succeeded.')

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        res, data = policy.detach(cluster)
        self.assertTrue(res)
        self.assertEqual('lb_delete succeeded.', data)
        mock_cluster_policy_load.assert_called_once_with(mock.ANY,
                                                         'CLUSTER_ID',
                                                         policy.id)
        mock_extract_policy_data.assert_called_once_with(cp_data)
        lb_driver.lb_delete.assert_called_once_with(**policy_data)

    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_detach_failed_lb_delete_failed(self, mock_lb_driver):

        cluster = mock.Mock()
        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(oslo_context, 'get_current')
        self.patchobject(cluster_policy.ClusterPolicy, 'load')
        self.patchobject(lb_policy.LoadBalancingPolicy,
                         '_extract_policy_data')
        lb_driver.lb_delete.return_value = (False, 'lb_delete failed.')

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        res, data = policy.detach(cluster)
        self.assertFalse(res)
        self.assertEqual('lb_delete failed.', data)

    def test_lb_policy_post_op_no_nodes(self):

        cluster_id = 'CLUSTER_ID'
        action = mock.Mock()
        action.data = {'nodes': []}

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)

        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_post_op_add_nodes_succeeded(self, mock_lb_driver,
                                                   mock_cluster_policy_load,
                                                   mock_extract_policy_data,
                                                   mock_node_load):

        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cluster_id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node2 = mock.Mock()
        node1.data = {}
        node2.data = {}
        action = mock.Mock()
        action.data = {
            'nodes': ['NODE1_ID', 'NODE2_ID'],
            'creation': {'count': 2}
        }
        action.context = 'action_context'
        action.action = consts.CLUSTER_RESIZE
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0',
                'data': policy_data
            }
        }
        cp.data = cp_data
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        lb_driver.member_add.side_effect = ['MEMBER1_ID', 'MEMBER2_ID']
        mock_node_load.side_effect = [node1, node2]
        mock_cluster_policy_load.return_value = cp
        mock_extract_policy_data.return_value = policy_data

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)
        mock_cluster_policy_load.assert_called_once_with('action_context',
                                                         'CLUSTER_ID',
                                                         policy.id)
        mock_extract_policy_data.assert_called_once_with(cp_data)
        calls_node_load = [mock.call('action_context', node_id=n,
                                     show_deleted=True
                                     ) for n in ['NODE1_ID', 'NODE2_ID']]
        mock_node_load.assert_has_calls(calls_node_load)
        calls_member_add = [mock.call(n, 'LB_ID', 'POOL_ID', 80, 'test-subnet'
                                      ) for n in [node1, node2]]
        lb_driver.member_add.assert_has_calls(calls_member_add)
        node1.store.assert_called_once_with('action_context')
        node2.store.assert_called_once_with('action_context')
        self.assertEqual({'lb_member': 'MEMBER1_ID'}, node1.data)
        self.assertEqual({'lb_member': 'MEMBER2_ID'}, node2.data)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_post_op_add_nodes_already_in_pool(
            self, mock_lb_driver, mock_extract_policy_data, mock_node_load):

        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cluster_id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node2 = mock.Mock()
        node1.data = {'lb_member': 'MEMBER1_ID'}
        node2.data = {}
        action = mock.Mock()
        action.data = {
            'nodes': ['NODE1_ID', 'NODE2_ID'],
            'creation': {'count': 2}
        }
        action.context = 'action_context'
        action.action = consts.CLUSTER_RESIZE
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(cluster_policy.ClusterPolicy, 'load')
        lb_driver.member_add.side_effect = ['MEMBER2_ID']
        mock_node_load.side_effect = [node1, node2]
        mock_extract_policy_data.return_value = policy_data

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)
        lb_driver.member_add.assert_called_once_with(node2, 'LB_ID', 'POOL_ID',
                                                     80, 'test-subnet')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_post_op_add_nodes_failed(self, mock_lb_driver,
                                                mock_extract_policy_data,
                                                mock_node_load):

        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cluster_id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node1.data = {}
        action = mock.Mock()
        action.data = {
            'nodes': ['NODE1_ID'],
            'creation': {'count': 1}
        }
        action.context = 'action_context'
        action.action = consts.CLUSTER_RESIZE
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(cluster_policy.ClusterPolicy, 'load')
        lb_driver.member_add.return_value = None
        mock_node_load.side_effect = [node1]
        mock_extract_policy_data.return_value = policy_data

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)
        self.assertEqual(policy_base.CHECK_ERROR, action.data['status'])
        self.assertEqual('Failed in adding new node into lb pool',
                         action.data['reason'])
        lb_driver.member_add.assert_called_once_with(node1, 'LB_ID', 'POOL_ID',
                                                     80, 'test-subnet')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_post_op_del_nodes_succeeded(self, mock_lb_driver,
                                                   mock_cluster_policy_load,
                                                   mock_extract_policy_data,
                                                   mock_node_load):

        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cluster_id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node2 = mock.Mock()
        node1.data = {'lb_member': 'MEMBER1_ID'}
        node2.data = {'lb_member': 'MEMBER2_ID'}
        action = mock.Mock()
        action.data = {
            'nodes': ['NODE1_ID', 'NODE2_ID'],
            'deletion': {'count': 2}
        }
        action.context = 'action_context'
        action.action = consts.CLUSTER_RESIZE
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0',
                'data': policy_data
            }
        }
        cp.data = cp_data
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        lb_driver.member_remove.return_value = True
        mock_node_load.side_effect = [node1, node2]
        mock_cluster_policy_load.return_value = cp
        mock_extract_policy_data.return_value = policy_data

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)
        mock_cluster_policy_load.assert_called_once_with('action_context',
                                                         'CLUSTER_ID',
                                                         policy.id)
        mock_extract_policy_data.assert_called_once_with(cp_data)
        calls_node_load = [mock.call('action_context', node_id=n,
                                     show_deleted=True
                                     ) for n in ['NODE1_ID', 'NODE2_ID']]
        mock_node_load.assert_has_calls(calls_node_load)
        calls_member_del = [mock.call('LB_ID', 'POOL_ID', m
                                      ) for m in ['MEMBER1_ID', 'MEMBER2_ID']]
        lb_driver.member_remove.assert_has_calls(calls_member_del)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_post_op_remove_nodes_not_in_pool(
            self, mock_lb_driver, mock_extract_policy_data, mock_node_load):

        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cluster_id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node2 = mock.Mock()
        node1.data = {}
        node2.data = {'lb_member': 'MEMBER2_ID'}
        action = mock.Mock()
        action.data = {
            'nodes': ['NODE1_ID', 'NODE2_ID'],
            'deletion': {'count': 2}
        }
        action.context = 'action_context'
        action.action = consts.CLUSTER_RESIZE
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(cluster_policy.ClusterPolicy, 'load')
        lb_driver.member_remove.return_value = True
        mock_node_load.side_effect = [node1, node2]
        mock_extract_policy_data.return_value = policy_data

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)
        lb_driver.member_remove.assert_called_once_with('LB_ID', 'POOL_ID',
                                                        'MEMBER2_ID')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
    @mock.patch.object(lb_driver, 'LoadBalancerDriver')
    def test_lb_policy_post_op_remove_nodes_failed(self, mock_lb_driver,
                                                   mock_extract_policy_data,
                                                   mock_node_load):

        lb_driver = mock.Mock()
        mock_lb_driver.return_value = lb_driver
        cluster_id = 'CLUSTER_ID'
        node1 = mock.Mock()
        node1.data = {'lb_member': 'MEMBER1_ID'}
        action = mock.Mock()
        action.data = {
            'nodes': ['NODE1_ID'],
            'deletion': {'count': 1}
        }
        action.context = 'action_context'
        action.action = consts.CLUSTER_RESIZE
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        self.patchobject(lb_policy.LoadBalancingPolicy, '_build_context')
        self.patchobject(cluster_policy.ClusterPolicy, 'load')
        lb_driver.member_remove.return_value = False
        mock_node_load.side_effect = [node1]
        mock_extract_policy_data.return_value = policy_data

        kwargs = {
            'spec': self.spec
        }
        policy = lb_policy.LoadBalancingPolicy('LoadBalancingPolicy',
                                               'test-policy', **kwargs)
        res = policy.post_op(cluster_id, action)
        self.assertIsNone(res)
        self.assertEqual(policy_base.CHECK_ERROR, action.data['status'])
        self.assertEqual('Failed in removing deleted node from lb pool',
                         action.data['reason'])
        lb_driver.member_remove.assert_called_once_with('LB_ID', 'POOL_ID',
                                                        'MEMBER1_ID')
