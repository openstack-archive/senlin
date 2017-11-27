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
from senlin.common import exception as exc
from senlin.common import scaleutils
from senlin.drivers import base as driver_base
from senlin.engine import cluster_policy
from senlin.objects import node as no
from senlin.policies import base as policy_base
from senlin.policies import lb_policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestLoadBalancingPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestLoadBalancingPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.loadbalance',
            'version': '1.0',
            'properties': {
                'pool': {
                    'id': '',
                    'protocol': 'HTTP',
                    'protocol_port': 80,
                    'subnet': 'internal-subnet',
                    'lb_method': 'ROUND_ROBIN',
                    'admin_state_up': True,
                    'session_persistence': {
                        'type': 'SOURCE_IP',
                        'cookie_name': 'whatever'
                    }
                },
                'vip': {
                    'address': '192.168.1.100',
                    'subnet': 'external-subnet',
                    'connection_limit': 500,
                    'protocol': 'HTTP',
                    'protocol_port': 80,
                    'admin_state_up': True,
                },
                'health_monitor': {
                    'type': 'HTTP',
                    'delay': 10,
                    'timeout': 5,
                    'max_retries': 3,
                    'admin_state_up': True,
                    'http_method': 'GET',
                    'url_path': '/index.html',
                    'expected_codes': '200,201,202'
                },
                'lb_status_timeout': 300
            }
        }
        self.sd = mock.Mock()
        self.patchobject(driver_base, 'SenlinDriver', return_value=self.sd)
        self.lb_driver = mock.Mock()
        self.net_driver = mock.Mock()
        self.octavia_driver = mock.Mock()

    @mock.patch.object(lb_policy.LoadBalancingPolicy, 'validate')
    def test_init(self, mock_validate):
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.loadbalance-1.0', policy.type)
        self.assertEqual(self.spec['properties']['pool'], policy.pool_spec)
        self.assertEqual(self.spec['properties']['vip'], policy.vip_spec)
        self.assertIsNone(policy.lb)

    def test_init_with_default_value(self):
        spec = {
            'type': 'senlin.policy.loadbalance',
            'version': '1.0',
            'properties': {
                'pool': {'subnet': 'internal-subnet'},
                'vip': {'subnet': 'external-subnet'}
            }
        }
        default_spec = {
            'type': 'senlin.policy.loadbalance',
            'version': '1.0',
            'properties': {
                'pool': {
                    'id': None,
                    'protocol': 'HTTP',
                    'protocol_port': 80,
                    'subnet': 'internal-subnet',
                    'lb_method': 'ROUND_ROBIN',
                    'admin_state_up': True,
                    'session_persistence': {},
                },
                'vip': {
                    'address': None,
                    'subnet': 'external-subnet',
                    'connection_limit': -1,
                    'protocol': 'HTTP',
                    'protocol_port': 80,
                    'admin_state_up': True,
                },
                'lb_status_timeout': 300
            }
        }

        policy = lb_policy.LoadBalancingPolicy('test-policy', spec)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.loadbalance-1.0', policy.type)
        self.assertEqual(default_spec['properties']['pool'], policy.pool_spec)
        self.assertEqual(default_spec['properties']['vip'], policy.vip_spec)
        self.assertEqual(default_spec['properties']['lb_status_timeout'],
                         policy.lb_status_timeout)
        self.assertIsNone(policy.lb)

    def test_loadbalancer_value(self):
        spec = {
            'type': 'senlin.policy.loadbalance',
            'version': '1.0',
            'properties': {
                'loadbalancer': 'LB_ID',
                'pool': {
                    'id': 'POOL_ID',
                    'subnet': 'internal-subnet'
                },
                'vip': {
                    'address': '192.168.1.100',
                    'subnet': 'external-subnet'
                },
                'health_monitor': {
                    'id': 'HM_ID'
                }
            }
        }
        self.spec['properties']['pool']['id'] = 'POOL_ID'
        self.spec['properties']['health_monitor']['id'] = 'HM_ID'
        self.spec['properties']['loadbalancer'] = 'LB_ID'
        self.spec['properties']['pool']['session_persistence'] = {}
        self.spec['properties']['vip']['connection_limit'] = -1
        policy = lb_policy.LoadBalancingPolicy('test-policy', spec)
        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.loadbalance-1.0', policy.type)
        self.assertEqual(self.spec['properties']['pool'], policy.pool_spec)
        self.assertEqual(self.spec['properties']['vip'], policy.vip_spec)
        self.assertEqual(self.spec['properties']['loadbalancer'], policy.lb)

    @mock.patch.object(policy_base.Policy, 'validate')
    def test_validate_shallow(self, mock_validate):
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        ctx = mock.Mock()

        res = policy.validate(ctx, False)

        self.assertTrue(res)
        mock_validate.assert_called_with(ctx, False)

    @mock.patch.object(policy_base.Policy, 'validate')
    def test_validate_pool_subnet_notfound(self, mock_validate):
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._networkclient = self.net_driver
        policy._octaviaclient = self.octavia_driver
        ctx = mock.Mock(user='user1', project='project1')
        self.net_driver.subnet_get = mock.Mock(
            side_effect=exc.InternalError(code='404', message='not found'))

        ex = self.assertRaises(exc.InvalidSpec, policy.validate, ctx, True)

        mock_validate.assert_called_with(ctx, True)
        self.net_driver.subnet_get.assert_called_once_with('internal-subnet')
        self.assertEqual("The specified subnet 'internal-subnet' could not "
                         "be found.", six.text_type(ex))

    @mock.patch.object(policy_base.Policy, 'validate')
    def test_validate_vip_subnet_notfound(self, mock_validate):
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._networkclient = self.net_driver
        policy._octaviaclient = self.octavia_driver
        ctx = mock.Mock(user='user1', project='project1')
        self.net_driver.subnet_get = mock.Mock(
            side_effect=[
                mock.Mock(),  # for the internal (pool) one
                exc.InternalError(code='404', message='not found')
            ]
        )

        ex = self.assertRaises(exc.InvalidSpec, policy.validate, ctx, True)

        mock_validate.assert_called_with(ctx, True)
        self.net_driver.subnet_get.assert_has_calls([
            mock.call('internal-subnet'), mock.call('external-subnet')
        ])
        self.assertEqual("The specified subnet 'external-subnet' could not "
                         "be found.", six.text_type(ex))

    @mock.patch.object(policy_base.Policy, 'validate')
    def test_validate_loadbalancer_notfund(self, mock_validate):
        self.spec['properties']['loadbalancer'] = "LB_ID"
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._networkclient = self.net_driver
        policy._octaviaclient = self.octavia_driver
        ctx = mock.Mock(user='user1', project='project1')
        self.octavia_driver.loadbalancer_get = mock.Mock(
            side_effect=exc.InternalError(code='404', message='not found'))

        ex = self.assertRaises(exc.InvalidSpec, policy.validate, ctx, True)

        mock_validate.assert_called_with(ctx, True)
        self.octavia_driver.loadbalancer_get.assert_called_once_with('LB_ID')
        self.assertEqual("The specified loadbalancer 'LB_ID' could not "
                         "be found.", six.text_type(ex))

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_build_policy_data')
    @mock.patch.object(policy_base.Policy, 'attach')
    @mock.patch.object(no.Node, 'update')
    def test_attach_succeeded(self, m_update, m_attach, m_build):
        cluster = mock.Mock(id='CLUSTER_ID', data={})
        node1 = mock.Mock(id='fake1', data={})
        node2 = mock.Mock(id='fake2', data={})
        cluster.nodes = [node1, node2]
        m_attach.return_value = (True, None)
        m_build.return_value = 'policy_data'
        data = {
            'loadbalancer': 'LB_ID',
            'vip_address': '192.168.1.100',
            'pool': 'POOL_ID'
        }
        self.lb_driver.lb_create.return_value = (True, data)
        self.lb_driver.member_add.side_effect = ['MEMBER1_ID', 'MEMBER2_ID']

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy.id = 'FAKE_ID'
        policy._lbaasclient = self.lb_driver

        res, data = policy.attach(cluster)

        self.assertTrue(res)
        self.assertEqual('policy_data', data)
        self.lb_driver.lb_create.assert_called_once_with(policy.vip_spec,
                                                         policy.pool_spec,
                                                         policy.hm_spec)
        member_add_calls = [
            mock.call(node1, 'LB_ID', 'POOL_ID', 80, 'internal-subnet'),
            mock.call(node2, 'LB_ID', 'POOL_ID', 80, 'internal-subnet')
        ]
        self.lb_driver.member_add.assert_has_calls(member_add_calls)
        node_update_calls = [
            mock.call(mock.ANY, node1.id,
                      {'data': {'lb_member': 'MEMBER1_ID'}}),
            mock.call(mock.ANY, node2.id,
                      {'data': {'lb_member': 'MEMBER2_ID'}})
        ]
        m_update.assert_has_calls(node_update_calls)
        expected = {
            policy.id: {'vip_address': '192.168.1.100'}
        }
        self.assertEqual(expected, cluster.data['loadbalancers'])

    @mock.patch.object(policy_base.Policy, 'attach')
    def test_attach_failed_base_return_false(self, mock_attach):
        cluster = mock.Mock()
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        mock_attach.return_value = (False, 'data')

        res, data = policy.attach(cluster)

        self.assertFalse(res)
        self.assertEqual('data', data)

    @mock.patch.object(policy_base.Policy, 'attach')
    def test_attach_failed_lb_creation_error(self, m_attach):
        cluster = mock.Mock()
        m_attach.return_value = (True, None)

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        # lb_driver.lb_create return False
        self.lb_driver.lb_create.return_value = (False, 'error')
        res = policy.attach(cluster)
        self.assertEqual((False, 'error'), res)

    @mock.patch.object(policy_base.Policy, 'attach')
    def test_attach_failed_member_add(self, mock_attach):
        cluster = mock.Mock()
        cluster.nodes = [mock.Mock(id='fake1'), mock.Mock(id='fake2')]
        mock_attach.return_value = (True, None)
        lb_data = {
            'loadbalancer': 'LB_ID',
            'vip_address': '192.168.1.100',
            'pool': 'POOL_ID'
        }
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver
        # lb_driver.member_add return None
        self.lb_driver.lb_create.return_value = (True, lb_data)
        self.lb_driver.member_add.return_value = None

        res = policy.attach(cluster)

        self.assertEqual((False, 'Failed in adding node into lb pool'), res)
        self.lb_driver.lb_delete.assert_called_once_with(**lb_data)

    def test_post_candidates_node_recover_reboot(self):
        node = mock.Mock(id='NODE1_ID')
        action = mock.Mock(action=consts.NODE_RECOVER)
        action.entity = node
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        candidates = policy._get_post_candidates(action)

        self.assertEqual(['NODE1_ID'], candidates)

    def test_post_candidates_node_recover_empty(self):
        node = mock.Mock(id='NODE1_ID')
        action = mock.Mock(action=consts.NODE_RECOVER,
                           outputs={})
        action.entity = node
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        candidates = policy._get_post_candidates(action)

        self.assertEqual(['NODE1_ID'], candidates)

    def test_post_candidates_cluster_resize(self):
        action = mock.Mock(action=consts.CLUSTER_RESIZE,
                           data={
                               'creation': {
                                   'nodes': ['NODE1_ID', 'NODE2_ID']
                               }
                           })
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        candidates = policy._get_post_candidates(action)

        self.assertEqual(['NODE1_ID', 'NODE2_ID'], candidates)

    def test_get_delete_candidates_for_node_delete(self):
        action = mock.Mock(action=consts.NODE_DELETE, inputs={}, data={},
                           entity=mock.Mock(id='NODE_ID'))
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)

        self.assertEqual(['NODE_ID'], res)

    def test_get_delete_candidates_no_deletion_data_del_nodes(self):
        action = mock.Mock(action=consts.CLUSTER_DEL_NODES, data={},
                           inputs={'candidates': ['node1', 'node2']})
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)

        self.assertEqual(['node1', 'node2'], res)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    def test_get_delete_candidates_no_deletion_data_scale_in(self,
                                                             m_nodes_random):
        self.context = utils.dummy_context()
        node1 = mock.Mock(id='node1')
        node2 = mock.Mock(id='node2')
        node3 = mock.Mock(id='node3')
        cluster = mock.Mock()
        cluster.nodes = [node1, node2, node3]
        action = mock.Mock(action=consts.CLUSTER_SCALE_IN, data={})
        action.entity = cluster

        m_nodes_random.return_value = ['node1', 'node3']
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)

        m_nodes_random.assert_called_once_with([node1, node2, node3], 1)
        self.assertEqual(['node1', 'node3'], res)

    @mock.patch.object(scaleutils, 'parse_resize_params')
    @mock.patch.object(scaleutils, 'nodes_by_random')
    def test_get_delete_candidates_no_deletion_data_resize(
            self, m_nodes_random, m_parse_param):

        def _parse_param(action, cluster, current):
            action.data = {'deletion': {'count': 2}}

        self.context = utils.dummy_context()
        node1 = mock.Mock(id='node1')
        node2 = mock.Mock(id='node2')
        node3 = mock.Mock(id='node3')
        cluster = mock.Mock(id='cluster1')
        cluster.nodes = [node1, node2, node3]
        action = mock.Mock(action=consts.CLUSTER_RESIZE, data={})
        action.entity = cluster

        m_parse_param.side_effect = _parse_param
        m_nodes_random.return_value = ['node1', 'node3']

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)

        m_parse_param.assert_called_once_with(action, cluster, 3)
        m_nodes_random.assert_called_once_with([node1, node2, node3], 2)
        self.assertEqual(['node1', 'node3'], res)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    def test_get_delete_candidates_deletion_no_candidates(self,
                                                          m_nodes_random):
        self.context = utils.dummy_context()
        node1 = mock.Mock(id='node1')
        node2 = mock.Mock(id='node2')
        node3 = mock.Mock(id='node3')
        cluster = mock.Mock(id='cluster1')
        cluster.nodes = [node1, node2, node3]
        action = mock.Mock(action=consts.CLUSTER_RESIZE, data={})
        action.entity = cluster
        action.data = {'deletion': {'count': 1}}

        m_nodes_random.return_value = ['node2']

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)

        m_nodes_random.assert_called_once_with([node1, node2, node3], 1)

        self.assertEqual(['node2'], res)
        self.assertEqual({'deletion': {'count': 1, 'candidates': ['node2']}},
                         action.data)

    def test_get_delete_candidates_deletion_count_is_zero(self):
        self.context = utils.dummy_context()
        action = mock.Mock(data={'deletion': {'number': 3}})
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)

        self.assertEqual([], res)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    def test_get_delete_candidates_deletion_count_over_size(self,
                                                            m_nodes_random):
        node1 = mock.Mock(id='node1')
        node2 = mock.Mock(id='node2')
        node3 = mock.Mock(id='node3')
        cluster = mock.Mock(id='cluster1')
        cluster.nodes = [node1, node2, node3]
        action = mock.Mock(action=consts.CLUSTER_RESIZE, data={})
        action.entity = cluster
        action.data = {'deletion': {'count': 4}}

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        policy._get_delete_candidates('CLUSTERID', action)

        m_nodes_random.assert_called_once_with([node1, node2, node3], 3)

    def test_get_delete_candidates_deletion_with_candidates(self):
        action = mock.Mock()
        action.data = {'deletion': {'count': 1, 'candidates': ['node3']}}

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy._get_delete_candidates('CLUSTERID', action)
        self.assertEqual(['node3'], res)


@mock.patch.object(cluster_policy.ClusterPolicy, 'load')
@mock.patch.object(lb_policy.LoadBalancingPolicy, '_extract_policy_data')
class TestLoadBalancingPolicyOperations(base.SenlinTestCase):

    def setUp(self):
        super(TestLoadBalancingPolicyOperations, self).setUp()

        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.loadbalance',
            'version': '1.0',
            'properties': {
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
                },
                'health_monitor': {
                    'type': 'HTTP',
                    'delay': '1',
                    'timeout': 1,
                    'max_retries': 5,
                    'admin_state_up': True,
                    'http_method': 'GET',
                    'url_path': '/index.html',
                    'expected_codes': '200,201,202'
                }
            }
        }
        self.lb_driver = mock.Mock()
        self.patchobject(oslo_context, 'get_current')

    def test_detach_no_policy_data(self, m_extract, m_load):
        cluster = mock.Mock()
        m_extract.return_value = None
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        res, data = policy.detach(cluster)

        self.assertTrue(res)
        self.assertEqual('LB resources deletion succeeded.', data)

    def test_detach_succeeded(self, m_extract, m_load):
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
        m_load.return_value = cp
        m_extract.return_value = policy_data
        self.lb_driver.lb_delete.return_value = (True, 'lb_delete succeeded.')
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver
        cluster = mock.Mock(
            id='CLUSTER_ID',
            data={
                'loadbalancers': {
                    policy.id: {'vip_address': '192.168.1.100'}

                }
            })
        node = mock.Mock(id='fake', data={})
        cluster.nodes = [node]

        res, data = policy.detach(cluster)

        self.assertTrue(res)
        self.assertEqual('lb_delete succeeded.', data)
        m_load.assert_called_once_with(mock.ANY, cluster.id, policy.id)
        m_extract.assert_called_once_with(cp_data)
        self.lb_driver.lb_delete.assert_called_once_with(**policy_data)
        self.assertEqual({}, cluster.data)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    def test_detach_existed_lbass_succeeded(self, m_remove, m_extract,
                                            m_load):
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID',
            'preexisting': True,
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0',
                'data': policy_data
            }
        }
        cp.data = cp_data
        m_load.return_value = cp
        m_extract.return_value = policy_data

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver
        cluster = mock.Mock(
            id='CLUSTER_ID',
            data={
                'loadbalancers': {
                    policy.id: {'vip_address': '192.168.1.100'}

                }
            })
        node = mock.Mock(id='fake', data={})
        cluster.nodes = [node]
        m_remove.return_value = []

        res, data = policy.detach(cluster)

        self.assertTrue(res)
        self.assertEqual('LB resources deletion succeeded.', data)
        m_load.assert_called_once_with(mock.ANY, cluster.id, policy.id)
        m_extract.assert_called_once_with(cp_data)
        m_remove.assert_called_with(mock.ANY, ['fake'], cp, self.lb_driver)
        self.assertEqual({}, cluster.data)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    def test_detach_existed_lbass_failed(self, m_remove, m_extract, m_load):
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID',
            'preexisting': True,
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0',
                'data': policy_data
            }
        }
        cp.data = cp_data
        m_load.return_value = cp
        m_extract.return_value = policy_data

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver
        cluster = mock.Mock(
            id='CLUSTER_ID',
            data={
                'loadbalancers': {
                    policy.id: {'vip_address': '192.168.1.100'}

                }
            })
        node1 = mock.Mock(id='node1', data={})
        node2 = mock.Mock(id='node2', data={})
        cluster.nodes = [node1, node2]
        m_remove.return_value = [node2.id]

        res, data = policy.detach(cluster)

        self.assertFalse(res)
        self.assertEqual('Failed to remove servers from existed LB.', data)
        m_load.assert_called_once_with(mock.ANY, cluster.id, policy.id)
        m_extract.assert_called_once_with(cp_data)
        m_remove.assert_called_with(mock.ANY, ['node1', 'node2'], cp,
                                    self.lb_driver)
        self.assertEqual({
            'loadbalancers': {
                None: {'vip_address': '192.168.1.100'}
            }},
            cluster.data)

    def test_detach_failed_lb_delete(self, m_extract, m_load):
        cluster = mock.Mock()
        policy_data = {
            'preexisting': False,
        }
        m_extract.return_value = policy_data
        self.lb_driver.lb_delete.return_value = (False, 'lb_delete failed.')

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        res, data = policy.detach(cluster)

        self.assertFalse(res)
        self.assertEqual('lb_delete failed.', data)

    def test_post_op_no_nodes(self, m_extract, m_load):
        action = mock.Mock(data={})

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)

        res = policy.post_op('FAKE_ID', action)

        self.assertIsNone(res)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'update')
    def test__add_member(self, m_node_update, m_node_get,
                         m_extract, m_load):
        node1 = mock.Mock(id='NODE1_ID', data={})
        node2 = mock.Mock(id='NODE2_ID', data={})
        action = mock.Mock(context='action_context',
                           action=consts.CLUSTER_RESIZE,
                           data={
                               'creation': {
                                   'nodes': ['NODE1_ID', 'NODE2_ID']
                               }
                           })
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
        self.lb_driver.member_add.side_effect = ['MEMBER1_ID', 'MEMBER2_ID']
        m_node_get.side_effect = [node1, node2]
        m_extract.return_value = policy_data
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        # do it
        candidates = ['NODE1_ID', 'NODE2_ID']
        res = policy._add_member(action.context, candidates,
                                 cp, self.lb_driver)

        # assertions
        self.assertEqual([], res)
        m_extract.assert_called_once_with(cp_data)
        calls_node_get = [
            mock.call('action_context', node_id='NODE1_ID'),
            mock.call('action_context', node_id='NODE2_ID')
        ]
        m_node_get.assert_has_calls(calls_node_get)
        calls_node_update = [
            mock.call(action.context, 'NODE1_ID', mock.ANY),
            mock.call(action.context, 'NODE2_ID', mock.ANY)
        ]
        m_node_update.assert_has_calls(calls_node_update)
        calls_member_add = [
            mock.call(node1, 'LB_ID', 'POOL_ID', 80, 'test-subnet'),
            mock.call(node2, 'LB_ID', 'POOL_ID', 80, 'test-subnet'),
        ]
        self.lb_driver.member_add.assert_has_calls(calls_member_add)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'update')
    def test__add_member_fail(self, m_node_update, m_node_get,
                              m_extract, m_load):
        node1 = mock.Mock(id='NODE1_ID', data={})
        action = mock.Mock(context='action_context',
                           action=consts.CLUSTER_RESIZE,
                           data={
                               'creation': {
                                   'nodes': ['NODE1_ID']
                               }
                           })
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
        self.lb_driver.member_add.return_value = None
        m_node_get.return_value = node1
        m_extract.return_value = policy_data
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        # do it
        candidates = ['NODE1_ID']
        res = policy._add_member(action.context, candidates,
                                 cp, self.lb_driver)

        # assertions
        self.assertEqual(['NODE1_ID'], res)
        m_extract.assert_called_once_with(cp_data)
        m_node_get.assert_called_once_with(
            'action_context', node_id='NODE1_ID')
        m_node_update.assert_called_once_with(
            'action_context', 'NODE1_ID', mock.ANY)
        self.lb_driver.member_add.assert_called_once_with(
            node1, 'LB_ID', 'POOL_ID', 80, 'test-subnet')

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_add_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_get_post_candidates')
    def test_post_op_node_create(self, m_get, m_remove, m_add,
                                 m_candidates, m_load):
        ctx = mock.Mock()
        cid = 'CLUSTER_ID'
        cluster = mock.Mock(user='user1', project='project1')
        action = mock.Mock(data={}, context=ctx, action=consts.NODE_CREATE,
                           node=mock.Mock(id='NODE_ID'))
        action.entity = cluster
        cp = mock.Mock()
        m_load.return_value = cp
        m_add.return_value = []
        m_get.return_value = ['NODE_ID']

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver
        # do it
        res = policy.post_op(cid, action)

        # assertion
        self.assertIsNone(res)
        m_get.assert_called_once_with(action)
        m_load.assert_called_once_with(ctx, cid, policy.id)
        m_add.assert_called_once_with(ctx, ['NODE_ID'], cp, self.lb_driver)
        self.assertFalse(m_remove.called)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_add_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_get_post_candidates')
    def test_post_op_add_nodes(self, m_get, m_remove, m_add,
                               m_candidates, m_load):
        cid = 'CLUSTER_ID'
        cluster = mock.Mock(user='user1', project='project1')
        action = mock.Mock(context='action_context',
                           action=consts.CLUSTER_RESIZE,
                           data={
                               'creation': {
                                   'nodes': ['NODE1_ID', 'NODE2_ID']
                               }
                           })
        action.entity = cluster
        candidates = ['NODE1_ID', 'NODE2_ID']
        m_get.return_value = candidates
        cp = mock.Mock()
        m_load.return_value = cp
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        # do it
        res = policy.post_op(cid, action)

        # assertions
        self.assertIsNone(res)
        m_get.assert_called_once_with(action)
        m_load.assert_called_once_with('action_context', cid, policy.id)
        m_add.assert_called_once_with(action.context, candidates,
                                      cp, self.lb_driver)
        self.assertFalse(m_remove.called)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_add_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_process_recovery')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_get_post_candidates')
    def test_post_op_node_recover(self, m_get, m_recovery, m_add,
                                  m_candidates, m_load):
        cid = 'CLUSTER_ID'
        node = mock.Mock(user='user1', project='project1', id='NODE1')
        action = mock.Mock(context='action_context',
                           action=consts.NODE_RECOVER,
                           data={},
                           outputs={})
        action.entity = node
        m_recovery.return_value = ['NODE1']
        m_get.return_value = ['NODE1']
        cp = mock.Mock()
        m_load.return_value = cp
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        # do it
        res = policy.post_op(cid, action)

        # assertions
        self.assertIsNone(res)
        m_get.assert_called_once_with(action)
        m_load.assert_called_once_with('action_context', cid, policy.id)
        m_add.assert_called_once_with(action.context, ['NODE1'],
                                      cp, self.lb_driver)
        m_recovery.assert_called_once_with(['NODE1'], cp, self.lb_driver,
                                           action)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_add_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_get_post_candidates')
    def test_post_op_clusterresize_failed(self, m_get, m_remove, m_add,
                                          m_candidates, m_load):
        cluster_id = 'CLUSTER_ID'
        action = mock.Mock(data={'creation': {'nodes': ['NODE1_ID']}},
                           context='action_context',
                           action=consts.CLUSTER_RESIZE)

        cp = mock.Mock()
        m_load.return_value = cp
        m_get.return_value = ['NODE1_ID']
        m_add.return_value = ['NODE1_ID']
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        res = policy.post_op(cluster_id, action)

        self.assertIsNone(res)
        self.assertEqual(policy_base.CHECK_ERROR, action.data['status'])
        self.assertEqual("Failed in adding nodes into lb pool: "
                         "['NODE1_ID']", action.data['reason'])
        m_get.assert_called_once_with(action)
        m_add.assert_called_once_with(action.context, ['NODE1_ID'],
                                      cp, self.lb_driver)
        self.assertFalse(m_remove.called)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'update')
    def test__remove_member(self, m_node_update, m_node_get,
                            m_extract, m_load):
        node1 = mock.Mock(id='NODE1', data={'lb_member': 'MEM_ID1'})
        node2 = mock.Mock(id='NODE2', data={'lb_member': 'MEM_ID2'})
        action = mock.Mock(
            context='action_context', action=consts.CLUSTER_DEL_NODES,
            data={
                'deletion': {
                    'count': 2,
                    'candidates': ['NODE1', 'NODE2']
                }
            })
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0', 'data': policy_data
            }
        }
        cp.data = cp_data
        self.lb_driver.member_remove.return_value = True
        m_node_get.side_effect = [node1, node2]
        m_extract.return_value = policy_data
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        candidates = [node1.id, node2.id]
        res = policy._remove_member(action.context, candidates,
                                    cp, self.lb_driver)

        m_extract.assert_called_once_with(cp_data)
        calls_node_get = [
            mock.call(action.context, node_id='NODE1'),
            mock.call(action.context, node_id='NODE2')
        ]
        m_node_get.assert_has_calls(calls_node_get)
        calls_node_update = [
            mock.call(action.context, 'NODE1', mock.ANY),
            mock.call(action.context, 'NODE2', mock.ANY)
        ]
        m_node_update.assert_has_calls(calls_node_update)
        calls_member_del = [
            mock.call('LB_ID', 'POOL_ID', 'MEM_ID1'),
            mock.call('LB_ID', 'POOL_ID', 'MEM_ID2')
        ]
        self.lb_driver.member_remove.assert_has_calls(calls_member_del)
        self.assertEqual([], res)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'update')
    def test__remove_member_not_in_pool(self, m_node_update, m_node_get,
                                        m_extract, m_load):
        node1 = mock.Mock(id='NODE1', data={'lb_member': 'MEM_ID1'})
        node2 = mock.Mock(id='NODE2', data={})
        action = mock.Mock(
            context='action_context', action=consts.CLUSTER_DEL_NODES,
            data={
                'deletion': {
                    'count': 2,
                    'candidates': ['NODE1', 'NODE2']
                }
            })
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0', 'data': policy_data
            }
        }
        cp.data = cp_data
        self.lb_driver.member_remove.return_value = True
        m_node_get.side_effect = [node1, node2]
        m_extract.return_value = policy_data
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        candidates = [node1.id, node2.id]
        res = policy._remove_member(action.context, candidates,
                                    cp, self.lb_driver)

        m_extract.assert_called_once_with(cp_data)
        calls_node_get = [
            mock.call(action.context, node_id='NODE1'),
            mock.call(action.context, node_id='NODE2')
        ]
        m_node_get.assert_has_calls(calls_node_get)
        m_node_update.assert_called_once_with(
            action.context, 'NODE1', mock.ANY)
        self.lb_driver.member_remove.assert_called_once_with(
            'LB_ID', 'POOL_ID', 'MEM_ID1')
        self.assertEqual([], res)

    @mock.patch.object(no.Node, 'get')
    @mock.patch.object(no.Node, 'update')
    def test__remove_member_fail(self, m_node_update, m_node_get,
                                 m_extract, m_load):
        node1 = mock.Mock(id='NODE1', data={'lb_member': 'MEM_ID1'})
        action = mock.Mock(
            context='action_context', action=consts.CLUSTER_DEL_NODES,
            data={
                'deletion': {
                    'count': 1,
                    'candidates': ['NODE1']
                }
            })
        cp = mock.Mock()
        policy_data = {
            'loadbalancer': 'LB_ID',
            'listener': 'LISTENER_ID',
            'pool': 'POOL_ID',
            'healthmonitor': 'HM_ID'
        }
        cp_data = {
            'LoadBalancingPolicy': {
                'version': '1.0', 'data': policy_data
            }
        }
        cp.data = cp_data
        self.lb_driver.member_remove.return_value = False
        m_node_get.return_value = node1
        m_extract.return_value = policy_data
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        candidates = [node1.id]
        res = policy._remove_member(action.context, candidates,
                                    cp, self.lb_driver)

        m_extract.assert_called_once_with(cp_data)
        m_node_get.assert_called_once_with(action.context, node_id='NODE1')
        m_node_update.assert_called_once_with(
            action.context, 'NODE1', mock.ANY)
        self.lb_driver.member_remove.assert_called_once_with(
            'LB_ID', 'POOL_ID', 'MEM_ID1')
        self.assertEqual(['NODE1'], res)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    def test_pre_op_del_nodes_ok(self, m_remove, m_candidates, m_load):
        cluster_id = 'CLUSTER_ID'
        cluster = mock.Mock(user='user1', project='project1')
        action = mock.Mock(
            context='action_context', action=consts.CLUSTER_DEL_NODES,
            data={
                'deletion': {
                    'count': 2,
                    'candidates': ['NODE1_ID', 'NODE2_ID']
                }
            })
        action.entity = cluster
        m_candidates.return_value = ['NODE1_ID', 'NODE2_ID']
        cp = mock.Mock()
        m_load.return_value = cp
        m_remove.return_value = []
        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver

        res = policy.pre_op(cluster_id, action)
        self.assertIsNone(res)

        m_load.assert_called_once_with('action_context', cluster_id, policy.id)

        expected_data = {'deletion': {'candidates': ['NODE1_ID', 'NODE2_ID'],
                                      'count': 2}}
        self.assertEqual(expected_data, action.data)

    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    def test_pre_op_del_nodes_failed(self, m_remove, m_candidates, m_load):
        cluster_id = 'CLUSTER_ID'
        cluster = mock.Mock(user='user1', project='project1')
        action = mock.Mock(
            action=consts.CLUSTER_RESIZE,
            context='action_context',
            data={'deletion': {'candidates': ['NODE1_ID']}})
        action.entity = cluster
        m_remove.return_value = ['NODE1_ID']

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        policy._lbaasclient = self.lb_driver
        res = policy.pre_op(cluster_id, action)

        self.assertIsNone(res)
        self.assertEqual(policy_base.CHECK_ERROR, action.data['status'])
        self.assertEqual("Failed in removing deleted node(s) from lb pool: "
                         "['NODE1_ID']", action.data['reason'])

        m_remove.assert_called_once_with(action.context, ['NODE1_ID'],
                                         mock.ANY, self.lb_driver)

    @mock.patch.object(no.Node, 'update')
    def test__process_recovery_not_lb_member(self, m_update, m1, m2):
        node = mock.Mock(id='NODE', data={})
        action = mock.Mock(
            action=consts.NODE_RECOVER,
            context='action_context')
        action.entity = node

        cp = mock.Mock()

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        res = policy._process_recovery(['NODE'], cp, self.lb_driver, action)

        self.assertEqual(['NODE'], res)
        m_update.assert_called_once_with(action.context, {'data': {}})

    @mock.patch.object(no.Node, 'update')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    def test__process_recovery_reboot(self, m_remove, m_update, m1, m2):
        node = mock.Mock(id='NODE', data={'lb_member': 'mem_1'})
        action = mock.Mock(
            action=consts.NODE_RECOVER,
            context='action_context')
        action.entity = node

        cp = mock.Mock()

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        res = policy._process_recovery(['NODE'], cp, self.lb_driver, action)

        self.assertIsNone(res)

        self.assertFalse(m_remove.called)
        self.assertFalse(m_update.called)

    @mock.patch.object(no.Node, 'update')
    @mock.patch.object(lb_policy.LoadBalancingPolicy, '_remove_member')
    def test__process_recovery_recreate(self, m_remove, m_update, m1, m2):
        node = mock.Mock(id='NODE', data={'lb_member': 'mem_1',
                                          'recovery': 'RECREATE'})
        action = mock.Mock(
            action=consts.NODE_RECOVER,
            context='action_context')
        action.entity = node

        cp = mock.Mock()

        policy = lb_policy.LoadBalancingPolicy('test-policy', self.spec)
        res = policy._process_recovery(['NODE'], cp, self.lb_driver, action)

        self.assertEqual(['NODE'], res)
        m_remove.assert_called_once_with(action.context, ['NODE'], cp,
                                         self.lb_driver, handle_err=False)
        m_update.assert_called_once_with(action.context, {'data': {}})
