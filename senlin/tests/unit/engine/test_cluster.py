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

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import cluster as clusterm
from senlin.engine import cluster_policy as cp_mod
from senlin.engine import event as eventm
from senlin.policies import base as policy_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestCluster(base.SenlinTestCase):

    def setUp(self):
        super(TestCluster, self).setUp()
        self.context = utils.dummy_context(project='cluster_test_project')
        self.profile = self._create_profile('PROFILE_ID')

    def _create_cluster(self, cluster_id):
        values = {
            'id': cluster_id,
            'profile_id': self.profile.id,
            'name': 'test-cluster',
            'user': self.context.user,
            'project': self.context.project,
        }

        return db_api.cluster_create(self.context, values)

    def _create_profile(self, profile_id):
        values = {
            'id': profile_id,
            'type': 'os.heat.stack-1.0',
            'name': 'test-profile',
            'type': 'os.heat.stack',
            'context': self.context.to_dict(),
            'spec': {
                'type': 'os.heat.stack',
                'version': '1.0',
                'properties': {
                    'foo': 'bar'
                }
            },
            'user': self.context.user,
            'project': self.context.project
        }
        return db_api.profile_create(self.context, values)

    def test_cluster_init(self):
        cluster = clusterm.Cluster('test-cluster', 0, 'PROFILE_ID')

        self.assertIsNone(cluster.id)
        self.assertEqual('test-cluster', cluster.name)
        self.assertEqual('PROFILE_ID', cluster.profile_id)
        self.assertEqual('', cluster.user)
        self.assertEqual('', cluster.project)
        self.assertEqual('', cluster.domain)
        self.assertEqual('', cluster.parent)

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
        self.assertEqual({'profile': None, 'nodes': [], 'policies': []},
                         cluster.rt)

    def test_cluster_init_with_none(self):
        kwargs = {
            'min_size': None,
            'max_size': None,
            'metadata': None
        }
        cluster = clusterm.Cluster('test-cluster', 0, 'PROFILE_ID',
                                   **kwargs)
        self.assertEqual(-1, cluster.max_size)
        self.assertEqual(0, cluster.min_size)
        self.assertEqual({}, cluster.metadata)

        self.assertIsNone(cluster.id)
        self.assertEqual('test-cluster', cluster.name)
        self.assertEqual('PROFILE_ID', cluster.profile_id)
        self.assertEqual('', cluster.user)
        self.assertEqual('', cluster.project)
        self.assertEqual('', cluster.domain)
        self.assertEqual('', cluster.parent)

    def test_cluster_store_init(self):
        mock_info = self.patchobject(eventm, 'info')

        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   user=self.context.user,
                                   project=self.context.project)
        self.assertIsNone(cluster.id)
        cluster_id = cluster.store(self.context)
        self.assertIsNotNone(cluster_id)

        result = db_api.cluster_get(self.context, cluster_id=cluster_id)

        self.assertIsNotNone(result)
        self.assertEqual('test-cluster', result.name)
        self.assertEqual(self.profile.id, result.profile_id)
        self.assertEqual(self.context.user, result.user)
        self.assertEqual(self.context.project, result.project)
        self.assertEqual('', result.domain)
        self.assertEqual('', result.parent)

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
        self.assertEqual({}, result.meta_data)

        mock_info.assert_called_once_with(self.context, cluster, 'create')

    def test_cluster_store_update(self):
        mock_info = self.patchobject(eventm, 'info')

        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   user=self.context.user,
                                   project=self.context.project)
        self.assertIsNone(cluster.id)
        cluster_id = cluster.store(self.context)
        self.assertIsNotNone(cluster_id)

        mock_info.assert_called_once_with(self.context, cluster, 'create')
        mock_info.reset_mock()

        # do an update
        cluster.name = 'test-cluster-1'
        cluster.parent = 'another-cluster'

        cluster.min_size = 1
        cluster.max_size = 3
        cluster.desired_capacity = 2
        cluster.timeout = 120
        cluster.data = {'FOO': 'BAR'}
        cluster.metadata = {'KEY': 'VALUE'}

        new_id = cluster.store(self.context)
        self.assertEqual(cluster_id, new_id)

        result = db_api.cluster_get(self.context, cluster_id)
        self.assertIsNotNone(result)

        self.assertEqual('test-cluster-1', result.name)
        self.assertEqual(self.context.user, result.user)
        self.assertEqual(self.context.project, result.project)
        self.assertEqual('another-cluster', result.parent)

        self.assertEqual(1, result.min_size)
        self.assertEqual(3, result.max_size)
        self.assertEqual(2, result.desired_capacity)

        self.assertEqual(120, result.timeout)
        self.assertEqual({'FOO': 'BAR'}, result.data)
        self.assertEqual({'KEY': 'VALUE'}, result.meta_data)

        mock_info.assert_called_once_with(self.context, cluster, 'update')

    def test_cluster_load(self):
        ex = self.assertRaises(exception.ClusterNotFound,
                               clusterm.Cluster.load,
                               self.context, 'non-existent', None)
        self.assertEqual('The cluster (non-existent) could not be found.',
                         six.text_type(ex))

        cluster = self._create_cluster('CLUSTER_ID')
        result = clusterm.Cluster.load(self.context, 'CLUSTER_ID')

        self.assertEqual(cluster.id, result.id)
        self.assertEqual(cluster.name, result.name)
        self.assertEqual(cluster.user, result.user)
        self.assertEqual(cluster.project, result.project)
        self.assertEqual(cluster.domain, result.domain)
        self.assertEqual(cluster.parent, result.parent)
        self.assertEqual(cluster.init_at, result.init_at)
        self.assertEqual(cluster.created_at, result.created_at)
        self.assertEqual(cluster.updated_at, result.updated_at)
        self.assertEqual(0, result.min_size)
        self.assertEqual(-1, result.max_size)
        self.assertEqual(cluster.desired_capacity, result.desired_capacity)
        self.assertEqual(cluster.next_index, result.next_index)
        self.assertEqual(cluster.profile_id, result.profile_id)
        self.assertEqual(cluster.status, result.status)
        self.assertEqual(cluster.status_reason, result.status_reason)
        self.assertEqual(cluster.data, result.data)
        self.assertEqual({}, result.metadata)

    def test_cluster_load_diff_project(self):
        self._create_cluster('CLUSTER_ID')

        new_ctx = utils.dummy_context(project='a-different-project')
        ex = self.assertRaises(exception.ClusterNotFound,
                               clusterm.Cluster.load,
                               new_ctx, 'CLUSTER_ID', None)
        self.assertEqual('The cluster (CLUSTER_ID) could not be found.',
                         six.text_type(ex))
        res = clusterm.Cluster.load(new_ctx, 'CLUSTER_ID', None,
                                    project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual('CLUSTER_ID', res.id)

    def test_cluster_load_all(self):
        result = clusterm.Cluster.load_all(self.context)
        self.assertEqual([], [c for c in result])

        cluster1 = self._create_cluster('CLUSTER1')
        cluster2 = self._create_cluster('CLUSTER2')

        # NOTE: we don't test all other parameters because the db api tests
        #       already covered that
        result = clusterm.Cluster.load_all(self.context)
        clusters = [c for c in result]
        self.assertEqual(2, len(clusters))
        self.assertEqual(cluster1.id, clusters[0].id)
        self.assertEqual(cluster2.id, clusters[1].id)

    def test_cluster_to_dict(self):
        cluster = self._create_cluster('CLUSTER123')
        self.assertIsNotNone(cluster.id)
        expected = {
            'id': cluster.id,
            'name': cluster.name,
            'profile_id': cluster.profile_id,
            'user': cluster.user,
            'project': cluster.project,
            'domain': cluster.domain,
            'parent': cluster.parent,
            'init_at': cluster.init_at,
            'created_at': cluster.created_at,
            'updated_at': cluster.updated_at,
            'min_size': 0,
            'max_size': -1,
            'desired_capacity': cluster.desired_capacity,
            'timeout': cfg.CONF.default_action_timeout,
            'status': cluster.status,
            'status_reason': cluster.status_reason,
            'metadata': {},
            'data': cluster.data,
            'nodes': [],
            'policies': [],
            'profile_name': self.profile.name,
        }

        result = clusterm.Cluster.load(self.context, cluster_id='CLUSTER123')
        self.assertEqual(expected, result.to_dict())

    def test_cluster_set_status(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.store(self.context)
        self.assertEqual(clusterm.Cluster.INIT, cluster.status)
        self.assertIsNotNone(cluster.init_at)
        self.assertIsNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)

        # create
        cluster.do_create(self.context)
        self.assertEqual(cluster.CREATING, cluster.status)
        self.assertEqual('Creation in progress', cluster.status_reason)
        self.assertIsNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)

        cluster.set_status(self.context, cluster.ACTIVE, 'Creation succeeded')
        self.assertEqual(cluster.ACTIVE, cluster.status)
        self.assertEqual('Creation succeeded', cluster.status_reason)
        self.assertIsNotNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)

        # update
        cluster.do_update(self.context)
        self.assertEqual(cluster.UPDATING, cluster.status)
        self.assertEqual('Update in progress', cluster.status_reason)
        self.assertIsNotNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)

        cluster.set_status(self.context, cluster.ACTIVE, 'Update succeeded',
                           data={'key': 'value'})
        self.assertEqual(cluster.ACTIVE, cluster.status)
        self.assertEqual('Update succeeded', cluster.status_reason)
        self.assertIsNotNone(cluster.created_at)
        self.assertIsNotNone(cluster.updated_at)
        self.assertEqual({'key': 'value'}, cluster.data)

        # set status without a reason
        reason = cluster.status_reason
        cluster.set_status(self.context, 'BOOM')
        self.assertEqual('BOOM', cluster.status)
        self.assertEqual(reason, cluster.status_reason)

    def test_cluster_set_status_with_new_profile(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.store(self.context)
        cluster.status = cluster.UPDATING

        self._create_profile('NEW_PROFILE')
        cluster.set_status(self.context, cluster.ACTIVE, 'Update succeeded',
                           profile_id='NEW_PROFILE')

        self.assertEqual(cluster.ACTIVE, cluster.status)
        self.assertEqual('Update succeeded', cluster.status_reason)
        self.assertIsNotNone(cluster.updated_at)
        self.assertEqual('NEW_PROFILE', cluster.profile_id)
        self.assertEqual('NEW_PROFILE', cluster.rt['profile'].id)

    def test_cluster_do_create_wrong_status(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.status = cluster.ACTIVE
        res = cluster.do_create(self.context)
        self.assertFalse(res)

    def test_cluster_nodes_property(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.nodes)

        # with nodes
        node1 = mock.Mock()
        node2 = mock.Mock()
        cluster.rt = {'nodes': [node1, node2]}
        self.assertEqual([node1, node2], cluster.nodes)

    def test_cluster_policies_property(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.policies)

        # with policies attached
        policy1 = mock.Mock()
        policy2 = mock.Mock()
        cluster.rt = {'policies': [policy1, policy2]}
        self.assertEqual([policy1, policy2], cluster.policies)

    def test_cluster_add_node(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.nodes)

        # add one node
        node = mock.Mock()
        cluster.add_node(node)
        self.assertEqual([node], cluster.nodes)

        # add another node
        another_node = mock.Mock()
        cluster.add_node(another_node)
        self.assertEqual([node, another_node], cluster.nodes)

    def test_cluster_remove_node(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.nodes)

        # remove from empty list should be okay
        res = cluster.remove_node('BOGUS')
        self.assertIsNone(res)

        # add one node
        node1 = mock.Mock()
        node1.id = 'NODE1'
        cluster.add_node(node1)
        self.assertEqual([node1], cluster.nodes)

        # remove non-existent node should be okay
        node2 = mock.Mock()
        node2.id = 'NODE2'
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
        node3.id = 'NODE2'

        res = cluster.remove_node(node3.id)
        self.assertIsNone(res)
        self.assertEqual([], cluster.nodes)

    @mock.patch.object(policy_base.Policy, 'load')
    @mock.patch.object(cp_mod, 'ClusterPolicy')
    def test_attach_policy(self, mock_cp, mock_load):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.id = 'FAKE_CLUSTER'
        policy = mock.Mock()
        policy.attach.return_value = (True, None)
        policy.PRIORITY = 10
        mock_load.return_value = policy

        binding = mock.Mock()
        mock_cp.return_value = binding

        values = {'enabled': True}
        res, reason = cluster.attach_policy(self.context, 'FAKE_POLICY',
                                            values)
        policy.attach.assert_called_once_with(cluster)
        mock_load.assert_called_once_with(self.context, 'FAKE_POLICY')
        mock_cp.assert_called_once_with('FAKE_CLUSTER', 'FAKE_POLICY',
                                        priority=10,
                                        enabled=True, data=None)
        binding.store.assert_called_once_with(self.context)
        self.assertIn(policy, cluster.policies)

    @mock.patch.object(policy_base.Policy, 'load')
    def test_attach_policy_already_attached(self, mock_load):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)

        existing = mock.Mock()
        existing.id = 'FAKE_POLICY_1'
        cluster.rt['policies'] = [existing]
        policy = mock.Mock()
        mock_load.return_value = policy

        # do it
        res, reason = cluster.attach_policy(self.context, 'FAKE_POLICY_1', {})

        self.assertTrue(res)
        self.assertEqual('Policy already attached.', reason)
        mock_load.assert_called_once_with(self.context, 'FAKE_POLICY_1')

    @mock.patch.object(policy_base.Policy, 'load')
    def test_attach_policy_type_conflict(self, mock_load):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.id = 'FAKE_CLUSTER'
        existing = mock.Mock()
        existing.id = 'PLCY2'
        existing.type = 'POLICY_TYPE_ONE'
        cluster.rt['policies'] = [existing]
        policy = mock.Mock()
        policy.singleton = True
        policy.type = 'POLICY_TYPE_ONE'
        mock_load.return_value = policy

        # do it
        res, reason = cluster.attach_policy(self.context, 'PLCY1', {})

        # assert
        self.assertFalse(res)
        expected = ('Only one instance of policy type (POLICY_TYPE_ONE) can '
                    'be attached to a cluster, but another instance '
                    '(PLCY2) is found attached to the cluster '
                    '(FAKE_CLUSTER) already.')
        self.assertEqual(expected, reason)
        mock_load.assert_called_once_with(self.context, 'PLCY1')

    @mock.patch.object(cp_mod, 'ClusterPolicy')
    @mock.patch.object(policy_base.Policy, 'load')
    def test_attach_policy_type_conflict_but_ok(self, mock_load, mock_cp):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)

        existing = mock.Mock()
        existing.id = 'FAKE_2'
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
        res, reason = cluster.attach_policy(self.context, 'FAKE_1', values)

        # assert
        self.assertTrue(res)
        self.assertEqual('Policy attached.', reason)

        policy.attach.assert_called_once_with(cluster)
        mock_load.assert_called_once_with(self.context, 'FAKE_1')
        mock_cp.assert_called_once_with(cluster.id, 'FAKE_1',
                                        priority=10,
                                        enabled=True, data=None)
        binding.store.assert_called_once_with(self.context)
        self.assertIn(policy, cluster.policies)

    @mock.patch.object(policy_base.Policy, 'load')
    def test_do_attach_policy_failed_do_attach(self, mock_load):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)

        policy = mock.Mock()
        policy.attach.return_value = (False, 'Bad things happened.')
        mock_load.return_value = policy

        # do it
        res, reason = cluster.attach_policy(self.context, 'FAKE_1', {})

        self.assertFalse(res)
        self.assertEqual('Bad things happened.', reason)
        policy.attach.assert_called_once_with(cluster)
        mock_load.assert_called_once_with(self.context, 'FAKE_1')

    @mock.patch.object(db_api, 'cluster_policy_detach')
    @mock.patch.object(policy_base.Policy, 'load')
    def test_detach_policy(self, mock_load, mock_detach):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.id = 'FAKE_CLUSTER'

        policy = mock.Mock()
        policy.id == 'FAKE_POLICY'
        existing = mock.Mock()
        existing.id = 'FAKE_POLICY'
        cluster.rt['policies'] = [existing]
        policy.detach.return_value = (True, None)
        mock_load.return_value = policy

        res, reason = cluster.detach_policy(self.context, 'FAKE_POLICY')

        self.assertTrue(res)
        self.assertEqual('Policy detached.', reason)
        policy.detach.assert_called_once_with(cluster)
        mock_load.assert_called_once_with(self.context, 'FAKE_POLICY')
        mock_detach.assert_called_once_with(self.context, 'FAKE_CLUSTER',
                                            'FAKE_POLICY')
        self.assertEqual([], cluster.rt['policies'])

    def test_detach_policy_not_attached(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.rt['policies'] = []

        res, reason = cluster.detach_policy(self.context, 'FAKE_POLICY')

        self.assertFalse(res)
        self.assertEqual('Policy not attached.', reason)

    @mock.patch.object(policy_base.Policy, 'load')
    def test_detach_policy_failed_detach(self, mock_load):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        policy = mock.Mock()
        policy.id = 'FAKE_POLICY'
        policy.detach.return_value = False, 'Things went wrong.'
        mock_load.return_value = policy
        cluster.rt['policies'] = [policy]

        res, reason = cluster.detach_policy(self.context, 'FAKE_POLICY')

        self.assertFalse(res)
        self.assertEqual('Things went wrong.', reason)
        mock_load.assert_called_once_with(self.context, 'FAKE_POLICY')
        policy.detach.assert_called_once_with(cluster)

    @mock.patch.object(db_api, 'cluster_policy_update')
    def test_update_policy(self, mock_update):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.id = 'FAKE_CLUSTER'
        existing = mock.Mock()
        existing.id = 'FAKE_POLICY'
        cluster.rt['policies'] = [existing]
        values = {
            'enabled': False
        }
        res, reason = cluster.update_policy(self.context, 'FAKE_POLICY',
                                            **values)
        self.assertTrue(res)
        self.assertEqual('Policy updated.', reason)
        mock_update.assert_called_once_with(
            self.context, 'FAKE_CLUSTER', 'FAKE_POLICY', {'enabled': False})

    def test_update_policy_not_attached(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.rt['policies'] = []

        # do it
        values = {'enabled': False}
        res, reason = cluster.update_policy(self.context, 'FAKE_POLICY',
                                            **values)
        self.assertFalse(res)
        self.assertEqual('Policy not attached.', reason)

    def test_update_policy_no_update_needed(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        existing = mock.Mock()
        existing.id = 'FAKE_POLICY'
        cluster.rt['policies'] = [existing]

        # do it
        values = {}
        res, reason = cluster.update_policy(self.context, 'FAKE_POLICY',
                                            **values)

        self.assertTrue(res)
        self.assertEqual('No update is needed.', reason)

    def test_get_region_distribution(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)

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
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
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
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
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
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
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
