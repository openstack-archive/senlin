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

from unittest import mock

from oslo_config import cfg
from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin.common import exception as exc
from senlin.objects import cluster as co
from senlin.objects import cluster_policy as cpo
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestCluster(base.SenlinTestCase):

    def setUp(self):
        super(TestCluster, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(co.Cluster, 'get')
    def test_find_by_uuid(self, mock_get):
        x_cluster = mock.Mock()
        mock_get.return_value = x_cluster
        aid = uuidutils.generate_uuid()

        result = co.Cluster.find(self.ctx, aid)

        self.assertEqual(x_cluster, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(co.Cluster, 'get_by_name')
    @mock.patch.object(co.Cluster, 'get')
    def test_find_by_uuid_as_name(self, mock_get, mock_get_name):
        x_cluster = mock.Mock()
        mock_get_name.return_value = x_cluster
        mock_get.return_value = None

        aid = uuidutils.generate_uuid()
        result = co.Cluster.find(self.ctx, aid, False)

        self.assertEqual(x_cluster, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)

    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_find_by_name(self, mock_get_name):
        x_cluster = mock.Mock()
        mock_get_name.return_value = x_cluster
        aid = 'this-is-not-uuid'

        result = co.Cluster.find(self.ctx, aid)

        self.assertEqual(x_cluster, result)
        mock_get_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(co.Cluster, 'get_by_short_id')
    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_find_by_shortid(self, mock_get_name, mock_get_shortid):
        x_cluster = mock.Mock()
        mock_get_shortid.return_value = x_cluster
        mock_get_name.return_value = None
        aid = 'abcd-1234-abcd'

        result = co.Cluster.find(self.ctx, aid, False)

        self.assertEqual(x_cluster, result)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, aid,
                                                 project_safe=False)

    @mock.patch.object(co.Cluster, 'get_by_short_id')
    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_find_not_found(self, mock_get_name, mock_get_short_id):
        mock_get_name.return_value = None
        mock_get_short_id.return_value = None

        self.assertRaises(exc.ResourceNotFound,
                          co.Cluster.find,
                          self.ctx, 'bogus')

        mock_get_name.assert_called_once_with(self.ctx, 'bogus',
                                              project_safe=True)
        mock_get_short_id.assert_called_once_with(self.ctx, 'bogus',
                                                  project_safe=True)

    def test_to_dict(self):
        PROFILE_ID = '96f4df4b-889e-4184-ba8d-b5ca122f95bb'
        POLICY1_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'
        POLICY2_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536d3'
        NODE1_ID = '26f4df4b-889e-4184-ba8d-b5ca122f9566'
        NODE2_ID = '26f4df4b-889e-4184-ba8d-b5ca122f9567'

        utils.create_profile(self.ctx, PROFILE_ID)
        policy_1 = utils.create_policy(self.ctx, POLICY1_ID, 'P1')
        policy_2 = utils.create_policy(self.ctx, POLICY2_ID, 'P2')

        values = {
            'profile_id': PROFILE_ID,
            'name': 'test-cluster',
            'desired_capacity': 1,
            'status': 'INIT',
            'init_at': timeutils.utcnow(True),
            'max_size': -1,
            'min_size': 0,
            'timeout': cfg.CONF.default_action_timeout,
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
        }
        cluster = co.Cluster.create(self.ctx, values)
        p1 = cpo.ClusterPolicy(cluster_id=cluster.id, policy_id=policy_1.id,
                               enabled=True, id=uuidutils.generate_uuid(),
                               last_op=None)
        p2 = cpo.ClusterPolicy(cluster_id=cluster.id, policy_id=policy_2.id,
                               enabled=True, id=uuidutils.generate_uuid(),
                               last_op=None)
        values = {
            'priority': 12,
            'enabled': True,
        }
        p1.create(self.ctx, cluster.id, POLICY1_ID, values)
        p2.create(self.ctx, cluster.id, POLICY2_ID, values)
        utils.create_node(self.ctx, NODE1_ID, PROFILE_ID, cluster.id)
        utils.create_node(self.ctx, NODE2_ID, PROFILE_ID, cluster.id)
        cluster = co.Cluster.get(self.ctx, cluster.id)
        expected = {
            'id': cluster.id,
            'name': cluster.name,
            'profile_id': PROFILE_ID,
            'user': cluster.user,
            'project': cluster.project,
            'domain': cluster.domain,
            'init_at': mock.ANY,
            'created_at': None,
            'updated_at': None,
            'min_size': 0,
            'max_size': -1,
            'desired_capacity': 1,
            'timeout': cfg.CONF.default_action_timeout,
            'status': str('INIT'),
            'status_reason': None,
            'metadata': {},
            'data': {},
            'dependents': {},
            'config': {},
            'nodes': [mock.ANY, mock.ANY],
            'policies': [mock.ANY, mock.ANY],
            'profile_name': str('test-profile'),
        }
        cluster_dict = cluster.to_dict()

        self.assertEqual(expected, cluster_dict)
        self.assertEqual(2, len(cluster_dict['nodes']))
        self.assertEqual(2, len(cluster_dict['policies']))
