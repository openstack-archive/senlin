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
from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin.common import exception as exc
from senlin.db import api as db_api
from senlin.objects import cluster as co
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

    @mock.patch.object(db_api, 'cluster_policy_ids_by_cluster')
    @mock.patch.object(db_api, 'node_ids_by_cluster')
    @mock.patch.object(db_api, 'profile_get')
    def test_to_dict(self, mock_profile, mock_nodes, mock_bindings):
        PROFILE_ID = '96f4df4b-889e-4184-ba8d-b5ca122f95bb'
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
        fake_profile = mock.Mock()
        fake_profile.name = 'PROFILEABC'
        mock_profile.return_value = fake_profile
        mock_nodes.return_value = ['N1', 'N2']
        mock_bindings.return_value = ['P1', 'P2']
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
            'status': 'INIT',
            'status_reason': None,
            'metadata': {},
            'data': {},
            'dependents': {},
            'config': {},
            'nodes': ['N1', 'N2'],
            'policies': ['P1', 'P2'],
            'profile_name': 'PROFILEABC',
        }

        self.assertEqual(expected, cluster.to_dict())
