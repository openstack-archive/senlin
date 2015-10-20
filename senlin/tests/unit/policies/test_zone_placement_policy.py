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
from oslo_utils import timeutils
import six

from senlin.db.sqlalchemy import api as db_api
from senlin.engine import cluster as cluster_base
from senlin.policies import zone_placement_policy as zp
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestZonePlacementPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestZonePlacementPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.zone_placement',
            'version': '1.0',
            'properties': {
                'zones': [
                    {'name': 'AZ1', 'weight': 100},
                    {'name': 'AZ2', 'weight': 80},
                    {'name': 'AZ3', 'weight': 60},
                    {'name': 'AZ4', 'weight': 40}
                ]
            }
        }
        self.profile1 = self._create_profile('PROFILE1')
        self.cluster = self._create_cluster('CLUSTER1',
                                            self.profile1['id'])
        self.nodes_p1 = self._create_nodes(self.cluster['id'],
                                           self.profile1['id'], 10)

    def _create_profile(self, profile_id):
        values = {
            'id': profile_id,
            'type': 'os.nova.server',
            'name': 'test-profile',
            'created_time': timeutils.utcnow(),
            'user': self.context.user,
            'project': self.context.project,
        }
        return db_api.profile_create(self.context, values)

    def _create_cluster(self, cluster_id, profile_id):
        values = {
            'id': cluster_id,
            'profile_id': profile_id,
            'name': 'test-cluster',
            'user': self.context.user,
            'project': self.context.project,
            'next_index': 1,
        }

        return db_api.cluster_create(self.context, values)

    def _create_nodes(self, cluster_id, profile_id, count):
        nodes = []
        for i in range(count):
            values = {
                'id': 'FAKE_NODE_%s_%s' % (profile_id, (i + 1)),
                'name': 'test_node_%s' % (i + 1),
                'physical_id': 'FAKE_PHY_ID_%s' % (i + 1),
                'cluster_id': cluster_id,
                'profile_id': profile_id,
                'project': self.context.project,
                'index': i + 1,
                'role': None,
                'created_time': timeutils.utcnow(),
                'updated_time': None,
                'deleted_time': None,
                'status': 'ACTIVE',
                'status_reason': 'create complete',
                'metadata': {'foo': '123'},
                'data': {'key1': 'value1'},
            }
            db_node = db_api.node_create(self.context, values)
            nodes.append(six.text_type(db_node.id))
        return nodes

    def test_policy_init(self):
        policy = zp.ZonePlacementPolicy('test-policy', self.spec)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.zone_placement-1.0', policy.type)
        expected = {'AZ1': 100, 'AZ2': 80, 'AZ3': 60, 'AZ4': 40}
        self.assertEqual(expected, policy.zones)
        self.assertIsNone(policy. _novaclient)

    def test__validate_zones(self):
        # in the condition that user inputs several error az,
        nc = mock.Mock()
        nc.availability_zone_list.return_value = [
            {'zoneState': {'available': 1}, 'zoneName': 'AZ1'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ2'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ3'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ4'}
        ]

        self.spec['properties']['zones'].append({'name': 'AZ5'})
        policy = zp.ZonePlacementPolicy('test-policy', self.spec)
        policy._novaclient = nc

        result = policy._validate_zones(self.cluster)

        self.assertNotIn('AZ5', result)

    def test__validate_zones_failed(self):
        # in the condition that user inputs all error az,
        nc = mock.Mock()
        nc.availability_zone_list.return_value = [
            {'zoneState': {'available': 1}, 'zoneName': 'AZ5'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ6'},
        ]

        policy = zp.ZonePlacementPolicy('test-policy', self.spec)
        policy._novaclient = nc
        result = policy._validate_zones(self.cluster)
        self.assertEqual(0, len(result))

    def test__get_current_dist(self):
        node1 = mock.Mock()
        node1.get_details.return_value = {
            'OS-EXT-AZ:availability_zone': 'AZ1',
        }
        node2 = mock.Mock()
        node2.get_details.return_value = {
            'foobar': 'irrelevant'
        }

        cluster = mock.Mock()
        cluster.nodes = [node1, node2]

        policy = zp.ZonePlacementPolicy('test-policy', self.spec)
        zones = policy.zones
        result = policy._get_current_dist(self.context, zones, cluster)

        self.assertEqual(4, len(result))
        self.assertEqual(1, result['AZ1'])
        self.assertEqual(0, result['AZ2'])
        self.assertEqual(0, result['AZ3'])
        self.assertEqual(0, result['AZ4'])

    def test_balance_strategy(self):
        # each az's ratio is same (default), test the placement
        self.spec['properties']['zones'] = [
            {'name': 'AZ1'}, {'name': 'AZ2'}, {'name': 'AZ3'}, {'name': 'AZ4'}
        ]
        policy = zp.ZonePlacementPolicy('test-policy', self.spec)
        zones = policy.zones

        current = {'AZ1': 2, 'AZ2': 2, 'AZ3': 2, 'AZ4': 1}
        plan = policy._create_plan(current, zones, 5)
        answer = {'AZ1': 1, 'AZ2': 1, 'AZ3': 1, 'AZ4': 2}
        self.assertEqual(answer, plan)

    def test_ratio_strategy(self):
        # each az has different ratio,test the placement
        # should fix the num
        policy = zp.ZonePlacementPolicy('test-policy', self.spec)
        zones = policy.zones
        current = {'AZ1': 2, 'AZ2': 2, 'AZ3': 2, 'AZ4': 1}
        plan = policy._create_plan(current, zones, 7)
        answer = {'AZ1': 3, 'AZ2': 2, 'AZ3': 1, 'AZ4': 1}
        self.assertEqual(answer, plan)

    @mock.patch.object(zp.ZonePlacementPolicy, '_get_current_dist')
    def test_pre_op(self, mock_get):
        # test pre_op method whether returns the correct action.data
        nc = mock.Mock()
        nc.availability_zone_list.return_value = [
            {'zoneState': {'available': 1}, 'zoneName': 'AZ1'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ2'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ3'},
            {'zoneState': {'available': 1}, 'zoneName': 'AZ4'}
        ]

        policy = zp.ZonePlacementPolicy('test-policy', self.spec)
        policy._novaclient = nc

        action = mock.Mock()
        action.context = self.context
        mock_get.return_value = {'AZ1': 2, 'AZ2': 2, 'AZ3': 2, 'AZ4': 1}

        cluster_base.Cluster.load = mock.Mock(return_value=self.cluster)

        action.data = {}
        action.inputs = {}
        policy.pre_op(self.cluster.id, action)
        placement = {'count': 1, 'placements': [{'zone': 'AZ1'}]}
        self.assertEqual(placement, action.data['placement'])

        action.data = {'creation': {'count': 7}}
        policy.pre_op(self.cluster.id, action)
        placement = {'count': 7, 'placements': [{'zone': 'AZ1'},
                                                {'zone': 'AZ1'},
                                                {'zone': 'AZ1'},
                                                {'zone': 'AZ2'},
                                                {'zone': 'AZ2'},
                                                {'zone': 'AZ3'},
                                                {'zone': 'AZ4'}]}
        self.assertEqual(placement, action.data['placement'])
