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
from senlin.engine import event as eventm
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestCluster(base.SenlinTestCase):

    def setUp(self):
        super(TestCluster, self).setUp()
        self.context = utils.dummy_context()
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
            'type': 'os.heat.stack',
            'name': 'test-profile',
            'context': self.context.to_dict()
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

        self.assertIsNone(cluster.init_time)
        self.assertIsNone(cluster.created_time)
        self.assertIsNone(cluster.updated_time)
        self.assertIsNone(cluster.deleted_time)

        self.assertEqual(0, cluster.min_size)
        self.assertEqual(-1, cluster.max_size)
        self.assertEqual(0, cluster.desired_capacity)
        self.assertEqual(1, cluster.next_index)
        self.assertEqual(cfg.CONF.default_action_timeout, cluster.timeout)
        self.assertEqual('INIT', cluster.status)
        self.assertEqual('Initializing', cluster.status_reason)
        self.assertEqual({}, cluster.data)
        self.assertEqual({}, cluster.metadata)
        self.assertEqual({}, cluster.rt)

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

        self.assertIsNotNone(result.init_time)
        self.assertIsNone(result.created_time)
        self.assertIsNone(result.updated_time)
        self.assertIsNone(result.deleted_time)

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
        self.assertEqual(cluster.init_time, result.init_time)
        self.assertEqual(cluster.created_time, result.created_time)
        self.assertEqual(cluster.updated_time, result.updated_time)
        self.assertEqual(cluster.deleted_time, result.deleted_time)
        self.assertEqual(cluster.min_size, result.min_size)
        self.assertEqual(cluster.max_size, result.max_size)
        self.assertEqual(cluster.desired_capacity, result.desired_capacity)
        self.assertEqual(cluster.next_index, result.next_index)
        self.assertEqual(cluster.profile_id, result.profile_id)
        self.assertEqual(cluster.status, result.status)
        self.assertEqual(cluster.status_reason, result.status_reason)
        self.assertEqual(cluster.data, result.data)
        self.assertEqual(cluster.meta_data, result.metadata)

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
            'init_time': cluster.init_time,
            'created_time': cluster.created_time,
            'updated_time': cluster.updated_time,
            'deleted_time': cluster.deleted_time,
            'min_size': cluster.min_size,
            'max_size': cluster.max_size,
            'desired_capacity': cluster.desired_capacity,
            'timeout': cluster.timeout,
            'status': cluster.status,
            'status_reason': cluster.status_reason,
            'metadata': cluster.meta_data,
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
        self.assertIsNotNone(cluster.init_time)
        self.assertIsNone(cluster.created_time)
        self.assertIsNone(cluster.updated_time)

        # create
        cluster.do_create(self.context)
        self.assertEqual(cluster.CREATING, cluster.status)
        self.assertEqual('Creation in progress', cluster.status_reason)
        self.assertIsNone(cluster.created_time)
        self.assertIsNone(cluster.updated_time)

        cluster.set_status(self.context, cluster.ACTIVE, 'Creation succeeded')
        self.assertEqual(cluster.ACTIVE, cluster.status)
        self.assertEqual('Creation succeeded', cluster.status_reason)
        self.assertIsNotNone(cluster.created_time)
        self.assertIsNone(cluster.updated_time)

        # update
        cluster.do_update(self.context)
        self.assertEqual(cluster.UPDATING, cluster.status)
        self.assertEqual('Update in progress', cluster.status_reason)
        self.assertIsNotNone(cluster.created_time)
        self.assertIsNone(cluster.updated_time)

        cluster.set_status(self.context, cluster.ACTIVE, 'Update succeeded')
        self.assertEqual(cluster.ACTIVE, cluster.status)
        self.assertEqual('Update succeeded', cluster.status_reason)
        self.assertIsNotNone(cluster.created_time)
        self.assertIsNotNone(cluster.updated_time)

        # set status without a reason
        reason = cluster.status_reason
        cluster.set_status(self.context, 'BOOM')
        self.assertEqual('BOOM', cluster.status)
        self.assertEqual(reason, cluster.status_reason)

        # Delete
        cluster.do_delete(self.context)
        self.assertEqual(cluster.DELETED, cluster.status)
        self.assertEqual('Deletion succeeded', cluster.status_reason)
        self.assertIsNotNone(cluster.created_time)
        self.assertIsNotNone(cluster.updated_time)
        self.assertIsNotNone(cluster.deleted_time)

    def test_cluster_do_create_wrong_status(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        cluster.status = cluster.ACTIVE
        res = cluster.do_create(self.context)
        self.assertFalse(res)

    def test_cluster_get_nodes(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.get_nodes())

        # with nodes
        node1 = mock.Mock()
        node2 = mock.Mock()
        cluster.rt = {'nodes': [node1, node2]}
        res = cluster.get_nodes()
        self.assertEqual([node1, node2], res)

    def test_cluster_get_policies(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.get_policies())

        # with policies attached
        policy1 = mock.Mock()
        policy2 = mock.Mock()
        cluster.rt = {'policies': [policy1, policy2]}
        res = cluster.get_policies()
        self.assertEqual([policy1, policy2], res)

    def test_cluster_add_policy(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.get_policies())

        # attach one policy (for initialize the policies list)
        policy = mock.Mock()
        cluster.add_policy(policy)
        res = cluster.get_policies()
        self.assertEqual([policy], res)

        # attach another policy
        policy_another = mock.Mock()
        cluster.add_policy(policy_another)
        res = cluster.get_policies()
        self.assertEqual([policy, policy_another], res)

    def test_cluster_remove_policy(self):
        cluster = clusterm.Cluster('test-cluster', 0, self.profile.id,
                                   project=self.context.project)
        # empty
        self.assertEqual([], cluster.get_policies())

        # remove from empty list should be okay
        res = cluster.remove_policy('BOGUS')
        self.assertIsNone(res)

        # attach one policy
        policy1 = mock.Mock()
        policy1.id = 'PP1'
        cluster.add_policy(policy1)
        self.assertEqual([policy1], cluster.get_policies())

        # remove non-existent should be okay
        policy_other = mock.Mock()
        policy_other.id = 'OTHER'
        res = cluster.remove_policy(policy_other)
        self.assertIsNone(res)
        self.assertEqual([policy1], cluster.get_policies())

        # attach another policy
        policy2 = mock.Mock()
        policy2.id = 'PP2'
        cluster.add_policy(policy2)
        self.assertEqual([policy1, policy2], cluster.get_policies())

        res = cluster.remove_policy(policy2)
        self.assertIsNone(res)
        self.assertEqual([policy1], cluster.get_policies())
