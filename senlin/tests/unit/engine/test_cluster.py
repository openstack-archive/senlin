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
from oslo_config import cfg
import six

from senlin.common import consts
from senlin.common import exception
from senlin.engine import cluster as cm
from senlin.engine import cluster_policy as cpm
from senlin.engine import health_manager
from senlin.engine import node as node_mod
from senlin.objects import cluster as co
from senlin.objects import cluster_policy as cpo
from senlin.objects import node as no
from senlin.policies import base as pcb
from senlin.profiles import base as pfb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

PROFILE_ID = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'
CLUSTER_ID = '60efdaa1-06c2-4fcf-ae44-17a2d85ff3ea'
POLICY_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'


class TestCluster(base.SenlinTestCase):

    def setUp(self):
        super(TestCluster, self).setUp()
        self.context = utils.dummy_context(project='cluster_test_project')

    def test_init(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)

        self.assertIsNone(cluster.id)
        self.assertEqual('test-cluster', cluster.name)
        self.assertEqual(PROFILE_ID, cluster.profile_id)
        self.assertEqual('', cluster.user)
        self.assertEqual('', cluster.project)
        self.assertEqual('', cluster.domain)

        self.assertIsNone(cluster.init_at)
        self.assertIsNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)

        self.assertEqual(0, cluster.min_size)
        self.assertEqual(-1, cluster.max_size)
        self.assertEqual(0, cluster.desired_capacity)
        self.assertEqual(1, cluster.next_index)
        self.assertEqual(cfg.CONF.default_action_timeout, cluster.timeout)
        self.assertEqual('INIT', cluster.status)
        self.assertEqual('Initializing', cluster.status_reason)
        self.assertEqual({}, cluster.data)
        self.assertEqual({}, cluster.metadata)
        self.assertEqual({}, cluster.dependents)
        self.assertEqual({}, cluster.config)
        self.assertEqual({'profile': None, 'nodes': [], 'policies': []},
                         cluster.rt)

    def test_init_with_none(self):
        kwargs = {
            'min_size': None,
            'max_size': None,
            'metadata': None
        }
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID, **kwargs)
        self.assertEqual(0, cluster.min_size)
        self.assertEqual(-1, cluster.max_size)
        self.assertEqual({}, cluster.metadata)

    @mock.patch.object(cm.Cluster, '_load_runtime_data')
    def test_init_with_context(self, mock_load):
        cm.Cluster('test-cluster', 0, PROFILE_ID, context=self.context)
        mock_load.assert_called_once_with(self.context)

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(pcb.Policy, 'load')
    @mock.patch.object(pfb.Profile, 'load')
    @mock.patch.object(no.Node, 'get_all_by_cluster')
    def test__load_runtime_data(self, mock_nodes, mock_profile, mock_policy,
                                mock_pb):
        x_binding = mock.Mock()
        x_binding.policy_id = POLICY_ID
        mock_pb.return_value = [x_binding]
        x_policy = mock.Mock()
        mock_policy.return_value = x_policy
        x_profile = mock.Mock()
        mock_profile.return_value = x_profile
        x_node_1 = mock.Mock()
        x_node_2 = mock.Mock()
        mock_nodes.return_value = [x_node_1, x_node_2]

        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.id = CLUSTER_ID

        cluster._load_runtime_data(self.context)

        rt = cluster.rt
        self.assertEqual(x_profile, rt['profile'])
        self.assertEqual([x_node_1, x_node_2], rt['nodes'])
        self.assertEqual(2, len(rt['nodes']))
        self.assertIsInstance(rt['nodes'], list)
        self.assertEqual([x_policy], rt['policies'])

        mock_pb.assert_called_once_with(self.context, CLUSTER_ID)
        mock_policy.assert_called_once_with(self.context,
                                            POLICY_ID,
                                            project_safe=False)
        mock_profile.assert_called_once_with(self.context,
                                             profile_id=PROFILE_ID,
                                             project_safe=False)
        mock_nodes.assert_called_once_with(self.context, CLUSTER_ID)

    def test__load_runtime_data_id_is_none(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)

        cluster._load_runtime_data(self.context)

        rt = cluster.rt
        self.assertIsNone(rt['profile'])
        self.assertEqual([], rt['nodes'])
        self.assertEqual(0, len(rt['nodes']))
        self.assertIsInstance(rt['nodes'], list)
        self.assertEqual([], rt['policies'])

    def test_store_for_create(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID,
                             user=self.context.user_id,
                             project=self.context.project_id)
        mock_load = self.patchobject(cluster, '_load_runtime_data')
        self.assertIsNone(cluster.id)

        cluster_id = cluster.store(self.context)
        self.assertIsNotNone(cluster_id)
        mock_load.assert_called_once_with(self.context)

        result = co.Cluster.get(self.context, cluster_id=cluster_id)

        self.assertIsNotNone(result)
        self.assertEqual('test-cluster', result.name)
        self.assertEqual(PROFILE_ID, result.profile_id)
        self.assertEqual(self.context.user_id, result.user)
        self.assertEqual(self.context.project_id, result.project)
        self.assertEqual(self.context.domain_id, result.domain)

        self.assertIsNotNone(result.init_at)
        self.assertIsNone(result.created_at)
        self.assertIsNone(result.updated_at)

        self.assertEqual(0, result.min_size)
        self.assertEqual(-1, result.max_size)
        self.assertEqual(0, result.desired_capacity)
        self.assertEqual(1, result.next_index)
        self.assertEqual(cfg.CONF.default_action_timeout, result.timeout)
        self.assertEqual('INIT', result.status)
        self.assertEqual('Initializing', result.status_reason)
        self.assertEqual({}, result.data)
        self.assertEqual({}, result.metadata)

    def test_store_for_update(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID,
                             user=self.context.user_id,
                             project=self.context.project_id)
        mock_load = self.patchobject(cluster, '_load_runtime_data')
        self.assertIsNone(cluster.id)

        cluster_id = cluster.store(self.context)

        self.assertIsNotNone(cluster_id)
        mock_load.assert_called_once_with(self.context)

        # do an update
        cluster.name = 'test-cluster-1'

        cluster.min_size = 1
        cluster.max_size = 3
        cluster.desired_capacity = 2
        cluster.timeout = 120
        cluster.data = {'FOO': 'BAR'}
        cluster.metadata = {'KEY': 'VALUE'}
        cluster.config = {'KEY': 'VALUE'}

        new_id = cluster.store(self.context)
        self.assertEqual(cluster_id, new_id)

        result = co.Cluster.get(self.context, cluster_id)
        self.assertIsNotNone(result)

        self.assertEqual('test-cluster-1', result.name)
        self.assertEqual(self.context.user_id, result.user)
        self.assertEqual(self.context.project_id, result.project)

        self.assertEqual(1, result.min_size)
        self.assertEqual(3, result.max_size)
        self.assertEqual(2, result.desired_capacity)

        self.assertEqual(120, result.timeout)
        self.assertEqual({'FOO': 'BAR'}, result.data)
        self.assertEqual({'KEY': 'VALUE'}, result.metadata)
        self.assertEqual({'KEY': 'VALUE'}, result.config)

    @mock.patch.object(cm.Cluster, '_from_object')
    def test_load_via_db_object(self, mock_init):
        x_obj = mock.Mock()

        result = cm.Cluster.load(self.context, dbcluster=x_obj)

        self.assertEqual(mock_init.return_value, result)
        mock_init.assert_called_once_with(self.context, x_obj)

    @mock.patch.object(co.Cluster, 'get')
    @mock.patch.object(cm.Cluster, '_from_object')
    def test_load_via_cluster_id(self, mock_init, mock_get):
        x_obj = mock.Mock()
        mock_get.return_value = x_obj

        result = cm.Cluster.load(self.context, cluster_id=CLUSTER_ID)

        self.assertEqual(mock_init.return_value, result)
        mock_get.assert_called_once_with(self.context, CLUSTER_ID,
                                         project_safe=True)
        mock_init.assert_called_once_with(self.context, x_obj)

    @mock.patch.object(co.Cluster, 'get')
    def test_load_not_found(self, mock_get):
        mock_get.return_value = None
        ex = self.assertRaises(exception.ResourceNotFound,
                               cm.Cluster.load,
                               self.context, cluster_id=CLUSTER_ID)
        self.assertEqual("The cluster '%s' could not be found." % CLUSTER_ID,
                         six.text_type(ex))
        mock_get.assert_called_once_with(self.context, CLUSTER_ID,
                                         project_safe=True)

    @mock.patch.object(cm.Cluster, '_from_object')
    @mock.patch.object(co.Cluster, 'get_all')
    def test_load_all(self, mock_get, mock_init):
        x_obj_1 = mock.Mock()
        x_obj_2 = mock.Mock()
        mock_get.return_value = [x_obj_1, x_obj_2]

        x_cluster_1 = mock.Mock()
        x_cluster_2 = mock.Mock()
        mock_init.side_effect = [x_cluster_1, x_cluster_2]

        result = cm.Cluster.load_all(self.context)

        self.assertEqual([x_cluster_1, x_cluster_2], [c for c in result])
        mock_get.assert_called_once_with(self.context,
                                         limit=None, marker=None,
                                         sort=None, filters=None,
                                         project_safe=True)
        mock_init.assert_has_calls([
            mock.call(self.context, x_obj_1),
            mock.call(self.context, x_obj_2)])

    @mock.patch.object(co.Cluster, 'update')
    def test_set_status_for_create(self, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID,
                             id=CLUSTER_ID, status='CREATING')

        cluster.set_status(self.context, consts.CS_ACTIVE, 'Cluster created')

        self.assertEqual(consts.CS_ACTIVE, cluster.status)
        self.assertEqual('Cluster created', cluster.status_reason)
        self.assertIsNotNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)

        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {
                'created_at': mock.ANY,
                'status': consts.CS_ACTIVE,
                'status_reason': 'Cluster created'
            }
        )

    @mock.patch.object(co.Cluster, 'update')
    def test_set_status_for_update(self, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID,
                             id=CLUSTER_ID, status='UPDATING')

        cluster.set_status(self.context, consts.CS_ACTIVE, 'Cluster updated')

        self.assertEqual(consts.CS_ACTIVE, cluster.status)
        self.assertEqual('Cluster updated', cluster.status_reason)
        self.assertIsNotNone(cluster.updated_at)

    @mock.patch.object(co.Cluster, 'update')
    def test_set_status_for_resize(self, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID,
                             id=CLUSTER_ID, status='RESIZING')

        cluster.set_status(self.context, consts.CS_ACTIVE, 'Cluster resized')

        self.assertEqual(consts.CS_ACTIVE, cluster.status)
        self.assertEqual('Cluster resized', cluster.status_reason)
        self.assertIsNotNone(cluster.updated_at)

    @mock.patch.object(pfb.Profile, 'load')
    @mock.patch.object(co.Cluster, 'update')
    def test_set_status_for_update_with_profile(self, mock_update,
                                                mock_load):
        x_profile = mock.Mock()
        mock_load.return_value = x_profile
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID, id=CLUSTER_ID,
                             status='UPDATING')

        new_profile_id = 'a64f0b03-4b77-49d5-89e0-7bcc77c4ce67'
        cluster.set_status(self.context, consts.CS_ACTIVE, 'Cluster updated',
                           profile_id=new_profile_id)

        self.assertEqual(consts.CS_ACTIVE, cluster.status)
        self.assertEqual('Cluster updated', cluster.status_reason)
        self.assertIsNotNone(cluster.updated_at)
        self.assertEqual(x_profile, cluster.rt['profile'])
        self.assertEqual(new_profile_id, cluster.profile_id)
        mock_load.assert_called_once_with(self.context,
                                          profile_id=new_profile_id)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {
                'status': consts.CS_ACTIVE,
                'status_reason': 'Cluster updated',
                'profile_id': new_profile_id,
                'updated_at': mock.ANY,
            }
        )

    @mock.patch.object(co.Cluster, 'update')
    def test_set_status_without_reason(self, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID, id=CLUSTER_ID,
                             status='UPDATING',
                             status_reason='Update in progress')

        cluster.set_status(self.context, consts.CS_WARNING)

        self.assertEqual(consts.CS_WARNING, cluster.status)
        self.assertEqual('Update in progress', cluster.status_reason)
        mock_update.assert_called_once_with(self.context, CLUSTER_ID,
                                            {'status': consts.CS_WARNING})

    @mock.patch.object(pfb.Profile, "create_cluster_object")
    def test_do_create(self, mock_create_cluster):
        mock_create_cluster.return_value = None

        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        mock_status = self.patchobject(cluster, 'set_status')

        res = cluster.do_create(self.context)

        self.assertTrue(res)
        mock_status.assert_called_once_with(
            self.context, consts.CS_CREATING, 'Creation in progress')

    def test_do_create_wrong_status(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.status = consts.CS_ACTIVE

        res = cluster.do_create(self.context)

        self.assertFalse(res)

    @mock.patch.object(pfb.Profile, "delete_cluster_object")
    @mock.patch.object(co.Cluster, 'delete')
    def test_do_delete(self, mock_delete, mock_delete_cluster):
        mock_delete.return_value = None
        mock_delete_cluster.return_value = None

        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.id = CLUSTER_ID
        mock_status = self.patchobject(cluster, 'set_status')

        res = cluster.do_delete(self.context)

        mock_delete.assert_called_once_with(self.context, CLUSTER_ID)
        self.assertTrue(res)
        mock_status.assert_called_once_with(
            self.context, consts.CS_DELETING, 'Deletion in progress')

    def test_do_update(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        mock_status = self.patchobject(cluster, 'set_status')

        res = cluster.do_update(self.context)

        mock_status.assert_called_once_with(self.context, consts.CS_UPDATING,
                                            'Update in progress')
        self.assertTrue(res)

    def test_do_check(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        mock_status = self.patchobject(cluster, 'set_status')

        res = cluster.do_check(self.context)

        mock_status.assert_called_once_with(self.context, consts.CS_CHECKING,
                                            'Check in progress')
        self.assertTrue(res)

    def test_do_recover(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        mock_status = self.patchobject(cluster, 'set_status')

        res = cluster.do_recover(self.context)

        mock_status.assert_called_once_with(self.context, consts.CS_RECOVERING,
                                            'Recovery in progress')
        self.assertTrue(res)

    def test_do_operation(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        mock_status = self.patchobject(cluster, 'set_status')

        res = cluster.do_operation(self.context, operation='dance')

        mock_status.assert_called_once_with(self.context, consts.CS_OPERATING,
                                            'Operation dance in progress')
        self.assertTrue(res)

    def test_nodes_property(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        self.assertEqual([], cluster.nodes)

        # with nodes
        node1 = mock.Mock()
        node2 = mock.Mock()
        cluster.rt['nodes'] = [node1, node2]

        self.assertEqual([node1, node2], cluster.nodes)

    def test_policies_property(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        self.assertEqual([], cluster.policies)

        # with policies attached
        policy1 = mock.Mock()
        policy2 = mock.Mock()
        cluster.rt['policies'] = [policy1, policy2]
        self.assertEqual([policy1, policy2], cluster.policies)

    def test_add_node(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        self.assertEqual([], cluster.nodes)

        # add one node
        node = mock.Mock()
        cluster.add_node(node)
        self.assertEqual([node], cluster.nodes)

        # add another node
        another_node = mock.Mock()
        cluster.add_node(another_node)
        self.assertEqual([node, another_node], cluster.nodes)

    def test_remove_node(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        self.assertEqual([], cluster.nodes)

        # remove from empty list should be okay
        res = cluster.remove_node('BOGUS')
        self.assertIsNone(res)

        # add one node
        node1 = mock.Mock()
        node1.id = '62d52dd6-5f83-4340-b079-349da2f9ffd9'
        cluster.add_node(node1)
        self.assertEqual([node1], cluster.nodes)

        # remove non-existent node should be okay
        node2 = mock.Mock()
        node2.id = 'd68214b2-e466-457f-a661-c8413a094a10'
        res = cluster.remove_node(node2)
        self.assertIsNone(res)
        self.assertEqual([node1], cluster.nodes)

        # add another node
        cluster.add_node(node2)
        self.assertEqual([node1, node2], cluster.nodes)

        # remove first node
        res = cluster.remove_node(node1.id)
        self.assertIsNone(res)
        self.assertEqual([node2], cluster.nodes)

        # reload and remove node
        node3 = mock.Mock()
        node3.id = 'd68214b2-e466-457f-a661-c8413a094a10'

        res = cluster.remove_node(node3.id)
        self.assertIsNone(res)
        self.assertEqual([], cluster.nodes)

    def test_update_node(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        self.assertEqual([], cluster.nodes)

        node1 = mock.Mock(id='fake', status='ACTIVE')
        # add one
        cluster.add_node(node1)

        node1.status = 'ERROR'
        cluster.update_node([node1])
        self.assertEqual([node1], cluster.nodes)

        # update new ones
        node2 = mock.Mock(id='fake1', status='ACTIVE')
        node3 = mock.Mock(id='fake2', status='ERROR')
        cluster.update_node([node2, node3])
        self.assertEqual([node2, node3], cluster.nodes)

    @mock.patch.object(pcb.Policy, 'load')
    @mock.patch.object(cpm, 'ClusterPolicy')
    def test_attach_policy(self, mock_cp, mock_load):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.id = CLUSTER_ID

        policy = mock.Mock()
        policy.attach.return_value = (True, None)
        policy.PRIORITY = 10
        mock_load.return_value = policy

        binding = mock.Mock()
        mock_cp.return_value = binding

        values = {'enabled': True}
        res, reason = cluster.attach_policy(self.context, POLICY_ID, values)
        policy.attach.assert_called_once_with(cluster, enabled=True)
        mock_load.assert_called_once_with(self.context, POLICY_ID)
        mock_cp.assert_called_once_with(CLUSTER_ID, POLICY_ID, priority=10,
                                        enabled=True, data=None)
        binding.store.assert_called_once_with(self.context)
        self.assertIn(policy, cluster.policies)

    @mock.patch.object(pcb.Policy, 'load')
    def test_attach_policy_already_attached(self, mock_load):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)

        policy_id = '62d52dd6-5f83-4340-b079-349da2f9ffd9'
        existing = mock.Mock(id=policy_id)
        cluster.rt['policies'] = [existing]
        policy = mock.Mock()
        mock_load.return_value = policy

        # do it
        res, reason = cluster.attach_policy(self.context, policy_id, {})

        self.assertTrue(res)
        self.assertEqual('Policy already attached.', reason)
        mock_load.assert_called_once_with(self.context, policy_id)

    @mock.patch.object(pcb.Policy, 'load')
    def test_attach_policy_type_conflict(self, mock_load):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.id = CLUSTER_ID

        existing = mock.Mock()
        existing.id = POLICY_ID
        existing.type = 'POLICY_TYPE_ONE'
        cluster.rt['policies'] = [existing]

        policy = mock.Mock()
        policy.singleton = True
        policy.type = 'POLICY_TYPE_ONE'
        mock_load.return_value = policy

        # do it
        new_policy_id = '62d52dd6-5f83-4340-b079-349da2f9ffd9'
        res, reason = cluster.attach_policy(self.context, new_policy_id, {})

        # assert
        self.assertFalse(res)
        expected = ('Only one instance of policy type (POLICY_TYPE_ONE) can '
                    'be attached to a cluster, but another instance '
                    '(%s) is found attached to the cluster '
                    '(%s) already.' % (POLICY_ID, CLUSTER_ID))
        self.assertEqual(expected, reason)
        mock_load.assert_called_once_with(self.context, new_policy_id)

    @mock.patch.object(cpm, 'ClusterPolicy')
    @mock.patch.object(pcb.Policy, 'load')
    def test_attach_policy_type_conflict_but_ok(self, mock_load, mock_cp):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)

        existing = mock.Mock()
        existing.id = POLICY_ID
        existing.type = 'POLICY_TYPE_ONE'
        cluster.rt['policies'] = [existing]

        policy = mock.Mock()
        policy.singleton = False
        policy.type = 'POLICY_TYPE_ONE'
        policy.attach.return_value = (True, None)
        policy.PRIORITY = 10
        mock_load.return_value = policy

        binding = mock.Mock()
        mock_cp.return_value = binding

        values = {'enabled': True}

        # do it
        new_policy_id = '62d52dd6-5f83-4340-b079-349da2f9ffd9'
        res, reason = cluster.attach_policy(self.context, new_policy_id,
                                            values)

        # assert
        self.assertTrue(res)
        self.assertEqual('Policy attached.', reason)

        policy.attach.assert_called_once_with(cluster, enabled=True)
        mock_load.assert_called_once_with(self.context, new_policy_id)
        mock_cp.assert_called_once_with(cluster.id, new_policy_id, priority=10,
                                        enabled=True, data=None)
        binding.store.assert_called_once_with(self.context)
        self.assertIn(policy, cluster.policies)

    @mock.patch.object(pcb.Policy, 'load')
    def test_attach_policy_failed_do_attach(self, mock_load):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)

        policy = mock.Mock()
        policy.attach.return_value = (False, 'Bad things happened.')
        mock_load.return_value = policy

        # do it
        new_id = '62d52dd6-5f83-4340-b079-349da2f9ffd9'
        res, reason = cluster.attach_policy(self.context, new_id, {})

        self.assertFalse(res)
        self.assertEqual('Bad things happened.', reason)
        policy.attach.assert_called_once_with(cluster, enabled=True)
        mock_load.assert_called_once_with(self.context, new_id)

    @mock.patch.object(cpo.ClusterPolicy, 'delete')
    @mock.patch.object(pcb.Policy, 'load')
    def test_detach_policy(self, mock_load, mock_detach):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.id = CLUSTER_ID

        policy = mock.Mock()
        policy.id = POLICY_ID
        existing = mock.Mock()
        existing.id = POLICY_ID
        cluster.rt['policies'] = [existing]
        policy.detach.return_value = (True, None)
        mock_load.return_value = policy

        res, reason = cluster.detach_policy(self.context, POLICY_ID)

        self.assertTrue(res)
        self.assertEqual('Policy detached.', reason)
        policy.detach.assert_called_once_with(cluster)
        mock_load.assert_called_once_with(self.context, POLICY_ID)
        mock_detach.assert_called_once_with(self.context, CLUSTER_ID,
                                            POLICY_ID)
        self.assertEqual([], cluster.rt['policies'])

    def test_detach_policy_not_attached(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.rt['policies'] = []

        res, reason = cluster.detach_policy(self.context, POLICY_ID)

        self.assertFalse(res)
        self.assertEqual('Policy not attached.', reason)

    @mock.patch.object(pcb.Policy, 'load')
    def test_detach_policy_failed_detach(self, mock_load):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        policy = mock.Mock()
        policy.id = POLICY_ID
        policy.detach.return_value = False, 'Things went wrong.'
        mock_load.return_value = policy
        cluster.rt['policies'] = [policy]

        res, reason = cluster.detach_policy(self.context, POLICY_ID)

        self.assertFalse(res)
        self.assertEqual('Things went wrong.', reason)
        mock_load.assert_called_once_with(self.context, POLICY_ID)
        policy.detach.assert_called_once_with(cluster)

    @mock.patch.object(cpo.ClusterPolicy, 'update')
    def test_update_policy(self, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.id = CLUSTER_ID

        existing = mock.Mock()
        existing.id = POLICY_ID
        existing.type = "senlin.policy.foo"
        cluster.rt['policies'] = [existing]
        values = {
            'enabled': False
        }

        res, reason = cluster.update_policy(self.context, POLICY_ID, **values)

        self.assertTrue(res)
        self.assertEqual('Policy updated.', reason)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID, POLICY_ID, {'enabled': False})

    def test_update_policy_not_attached(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        cluster.rt['policies'] = []
        values = {'enabled': False}

        # do it
        res, reason = cluster.update_policy(self.context, POLICY_ID, **values)

        self.assertFalse(res)
        self.assertEqual('Policy not attached.', reason)

    def test_update_policy_no_update_needed(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        existing = mock.Mock()
        existing.id = POLICY_ID
        cluster.rt['policies'] = [existing]
        values = {}

        # do it
        res, reason = cluster.update_policy(self.context, POLICY_ID, **values)

        self.assertTrue(res)
        self.assertEqual('No update is needed.', reason)

    @mock.patch.object(cpo.ClusterPolicy, "update")
    @mock.patch.object(health_manager, "enable")
    def test_update_policy_enable_health(self, mock_enable, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID, id=CLUSTER_ID)
        existing = mock.Mock(id=POLICY_ID, type="senlin.policy.health")
        cluster.rt['policies'] = [existing]
        values = {"enabled": True}

        # do it
        res, reason = cluster.update_policy(self.context, POLICY_ID, **values)

        self.assertTrue(res)
        mock_enable.assert_called_once_with(CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID, POLICY_ID, {'enabled': True})

    @mock.patch.object(cpo.ClusterPolicy, "update")
    @mock.patch.object(health_manager, "disable")
    def test_update_policy_disable_health(self, mock_disable, mock_update):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID, id=CLUSTER_ID)
        existing = mock.Mock(id=POLICY_ID, type="senlin.policy.health")
        cluster.rt['policies'] = [existing]
        values = {"enabled": False}

        # do it
        res, reason = cluster.update_policy(self.context, POLICY_ID, **values)

        self.assertTrue(res)
        mock_disable.assert_called_once_with(CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID, POLICY_ID, {'enabled': False})

    def test_get_region_distribution(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)

        node1 = mock.Mock()
        node1.data = {'placement': {'region_name': 'R1'}}
        node2 = mock.Mock()
        node2.data = {'placement': {'region_name': 'R2'}}
        node3 = mock.Mock()
        node3.data = {'key': 'value'}

        node4 = mock.Mock()
        node4.data = {'placement': {'region_name': 'BAD'}}

        nodes = [node1, node2, node3, node4]
        for n in nodes:
            cluster.add_node(n)

        result = cluster.get_region_distribution(['R1', 'R2', 'R3'])

        self.assertEqual(3, len(result))
        self.assertEqual(1, result['R1'])
        self.assertEqual(1, result['R2'])
        self.assertEqual(0, result['R3'])

    def test_get_zone_distribution(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        node1 = mock.Mock()
        node1.data = {}
        node1.get_details.return_value = {
            'OS-EXT-AZ:availability_zone': 'AZ1',
        }
        node2 = mock.Mock()
        node2.data = {
            'foobar': 'irrelevant'
        }
        node3 = mock.Mock()
        node3.data = {
            'placement': {
                'zone': 'AZ2'
            }
        }

        nodes = [node1, node2, node3]
        for n in nodes:
            cluster.add_node(n)

        result = cluster.get_zone_distribution(self.context,
                                               ['AZ1', 'AZ2', 'AZ3'])

        self.assertEqual(3, len(result))
        self.assertEqual(1, result['AZ1'])
        self.assertEqual(1, result['AZ2'])
        self.assertEqual(0, result['AZ3'])

        node1.get_details.assert_called_once_with(self.context)

    def test_nodes_by_region(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        node1 = mock.Mock(data={'placement': {'region_name': 'R1'}})
        node2 = mock.Mock(data={'placement': {'region_name': 'R2'}})
        node3 = mock.Mock(data={'key': 'value'})
        node4 = mock.Mock(data={'placement': {'region_name': 'BAD'}})

        nodes = [node1, node2, node3, node4]
        for n in nodes:
            cluster.add_node(n)

        result = cluster.nodes_by_region('R1')
        self.assertEqual(1, len(result))
        self.assertEqual(node1, result[0])

        result = cluster.nodes_by_region('R2')
        self.assertEqual(1, len(result))
        self.assertEqual(node2, result[0])

        result = cluster.nodes_by_region('R3')
        self.assertEqual(0, len(result))

    def test_nodes_by_zone(self):
        cluster = cm.Cluster('test-cluster', 0, PROFILE_ID)
        node1 = mock.Mock(data={'placement': {'zone': 'AZ1'}})
        node2 = mock.Mock(data={'placement': {'zone': 'AZ2'}})
        node3 = mock.Mock(data={'key': 'value'})
        node4 = mock.Mock(data={'placement': {'zone': 'BAD'}})

        nodes = [node1, node2, node3, node4]
        for n in nodes:
            cluster.add_node(n)

        result = cluster.nodes_by_zone('AZ1')
        self.assertEqual(1, len(result))
        self.assertEqual(node1, result[0])

        result = cluster.nodes_by_zone('AZ2')
        self.assertEqual(1, len(result))
        self.assertEqual(node2, result[0])

        result = cluster.nodes_by_region('AZ3')
        self.assertEqual(0, len(result))

    @mock.patch.object(node_mod.Node, 'load_all')
    @mock.patch.object(node_mod.Node, 'do_check')
    @mock.patch.object(cm.Cluster, 'update_node')
    def test_health_check(self, mock_update, mock_check, mock_load):
        cluster = cm.Cluster('test-cluster', 5, PROFILE_ID,
                             min_size=2, id=CLUSTER_ID)
        node1 = node_mod.Node('fake1', PROFILE_ID, status='ACTIVE')
        node2 = node_mod.Node('fake2', PROFILE_ID, status='ACTIVE')
        nodes = [node1, node2]
        for node in nodes:
            cluster.add_node(node)

        node1.status = 'ERROR'
        mock_load.return_value = [node1, node2]

        cluster.health_check(self.context)

        self.assertEqual(2, len(cluster.nodes))
        self.assertEqual([node1, node2], cluster.nodes)

        mock_update.assert_called_once_with([node1, node2])
        mock_check.assert_has_calls([
            mock.call(self.context),
            mock.call(self.context)
        ])
        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_below_min_size(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 5, PROFILE_ID,
                             min_size=2, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ERROR')
        node3 = mock.Mock(status='WARNING')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST')
        rt = cluster.rt
        self.assertEqual(3, len(rt['nodes']))
        self.assertIsInstance(rt['nodes'], list)
        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'status': consts.CS_ERROR,
             'status_reason': 'TEST: number of active nodes is below '
                              'min_size (2).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_below_desired_capacity(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 5, PROFILE_ID,
                             min_size=1, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ERROR')
        node3 = mock.Mock(status='WARNING')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST')

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'status': consts.CS_WARNING,
             'status_reason': 'TEST: number of active nodes is below '
                              'desired_capacity (5).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_equal_desired_capacity(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 3, PROFILE_ID,
                             min_size=1, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ACTIVE')
        node3 = mock.Mock(status='ACTIVE')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST')

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'status': consts.CS_ACTIVE,
             'status_reason': 'TEST: number of active nodes is equal or above '
                              'desired_capacity (3).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_above_desired_capacity(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 2, PROFILE_ID,
                             min_size=1, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ACTIVE')
        node3 = mock.Mock(status='ACTIVE')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST')

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'status': consts.CS_ACTIVE,
             'status_reason': 'TEST: number of active nodes is equal or above '
                              'desired_capacity (2).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_above_max_size(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 2, PROFILE_ID,
                             max_size=2, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ACTIVE')
        node3 = mock.Mock(status='ACTIVE')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST')

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'status': consts.CS_WARNING,
             'status_reason': 'TEST: number of active nodes is above '
                              'max_size (2).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_with_new_desired(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 5, PROFILE_ID, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ERROR')
        node3 = mock.Mock(status='WARNING')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST', desired_capacity=2)

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'desired_capacity': 2,
             'status': consts.CS_WARNING,
             'status_reason': 'TEST: number of active nodes is below '
                              'desired_capacity (2).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status__new_desired_is_zero(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 5, PROFILE_ID, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ERROR')
        node3 = mock.Mock(status='WARNING')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST', desired_capacity=0)

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'desired_capacity': 0,
             'status': consts.CS_ACTIVE,
             'status_reason': 'TEST: number of active nodes is equal or above '
                              'desired_capacity (0).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_with_new_min(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 5, PROFILE_ID,
                             id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ERROR')
        node3 = mock.Mock(status='WARNING')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST', min_size=2)

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'min_size': 2,
             'status': consts.CS_ERROR,
             'status_reason': 'TEST: number of active nodes is below '
                              'min_size (2).'})

    @mock.patch.object(co.Cluster, 'update')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_eval_status_with_new_max(self, mock_load, mock_update):
        cluster = cm.Cluster('test-cluster', 2, PROFILE_ID,
                             max_size=5, id=CLUSTER_ID)
        node1 = mock.Mock(status='ACTIVE')
        node2 = mock.Mock(status='ACTIVE')
        node3 = mock.Mock(status='ACTIVE')
        mock_load.return_value = [node1, node2, node3]

        cluster.eval_status(self.context, 'TEST', max_size=6)

        mock_load.assert_called_once_with(self.context, cluster_id=CLUSTER_ID)
        mock_update.assert_called_once_with(
            self.context, CLUSTER_ID,
            {'max_size': 6,
             'status': consts.CS_ACTIVE,
             'status_reason': 'TEST: number of active nodes is equal or above '
                              'desired_capacity (2).'})
