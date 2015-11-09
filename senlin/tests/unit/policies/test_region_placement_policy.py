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

from senlin.drivers import base as driver_base
from senlin.engine import cluster as cluster_mod
from senlin.policies import base as policy_base
from senlin.policies import region_placement as rp
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestRegionPlacementPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestRegionPlacementPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.region_placement',
            'version': '1.0',
            'properties': {
                'regions': [
                    {'name': 'R1', 'weight': 100, 'cap': 50},
                    {'name': 'R2', 'weight': 50, 'cap': 50},
                    {'name': 'R3', 'weight': 30, 'cap': -1},
                    {'name': 'R4', 'weight': 20, 'cap': -1}
                ]
            }
        }

    def test_policy_init(self):
        policy = rp.RegionPlacementPolicy('test-policy', self.spec)

        self.assertIsNone(policy.id)
        self.assertIsNone(policy. _keystoneclient)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.region_placement-1.0', policy.type)
        expected = {
            'R1': {
                'weight': 100,
                'cap': 50
            },
            'R2': {
                'weight': 50,
                'cap': 50,
            },
            'R3': {
                'weight': 30,
                'cap': -1,
            },
            'R4': {
                'weight': 20,
                'cap': -1,
            }
        }
        self.assertEqual(expected, policy.regions)

    @mock.patch.object(policy_base.Policy, '_build_conn_params')
    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_keystone(self, mock_sd, mock_conn):
        params = mock.Mock()
        mock_conn.return_value = params
        kc = mock.Mock()
        driver = mock.Mock()
        driver.identity.return_value = kc
        mock_sd.return_value = driver
        cluster = mock.Mock()
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy.keystone(cluster)

        self.assertEqual(kc, res)
        self.assertEqual(kc, policy._keystoneclient)
        mock_conn.assert_called_once_with(cluster)
        mock_sd.assert_called_once_with()
        driver.identity.assert_called_once_with(params)

    def test__validate_regions(self):
        cluster = mock.Mock()
        kc = mock.Mock()
        kc.region_list.return_value = [
            {'id': 'R1', 'parent_region_id': None},
            {'id': 'R2', 'parent_region_id': None},
            {'id': 'R3', 'parent_region_id': 'R1'},
        ]

        policy = rp.RegionPlacementPolicy('p1', self.spec)
        policy._keystoneclient = kc

        result = policy._validate_regions(cluster)

        for r in ['R1', 'R2', 'R3']:
            self.assertIn(r, result)
        self.assertNotIn('R4', result)

    def test__get_current_dist(self):
        node1 = mock.Mock()
        node1.data = {
            'placement': {
                'region_name': 'R1'
            }
        }
        node2 = mock.Mock()
        node2.data = {
            'placement': {
                'region_name': 'R2',
            }
        }
        node3 = mock.Mock()
        node3.data = {'key': 'value'}

        nodes = [node1, node2, node3]

        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions
        result = policy._get_current_dist(regions, nodes)

        self.assertEqual(4, len(result))
        self.assertEqual(1, result['R1'])
        self.assertEqual(1, result['R2'])
        self.assertEqual(0, result['R3'])
        self.assertEqual(0, result['R4'])

    def test__create_plan(self):
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions

        current = {'R1': 2, 'R2': 2, 'R3': 2, 'R4': 1}
        plan = policy._create_plan(current, regions, 5)
        answer = {'R1': 4, 'R2': 1, 'R3': 0, 'R4': 0}
        self.assertEqual(answer, plan)

        current = {'R1': 2, 'R2': 2, 'R3': 0, 'R4': 1}
        plan = policy._create_plan(current, regions, 5)
        answer = {'R1': 3, 'R2': 1, 'R3': 1, 'R4': 0}
        self.assertEqual(answer, plan)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_pre_op(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions
        plan = {'R1': 1, 'R2': 0, 'R3': 2, 'R4': 0}
        current_dist = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0}
        self.patchobject(policy, '_validate_regions', return_value=regions)
        self.patchobject(policy, '_create_plan', return_value=plan)
        self.patchobject(policy, '_get_current_dist',
                         return_value=current_dist)

        action = mock.Mock()
        action.context = self.context
        action.inputs = {}
        action.data = {
            'creation': {
                'count': 3,
            }
        }

        cluster = mock.Mock()
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)

        self.assertEqual(3, action.data['placement']['count'])
        self.assertEqual(3, len(action.data['placement']['placements']))
        self.assertIn({'region_name': 'R1'},
                      action.data['placement']['placements'])
        self.assertIn({'region_name': 'R3'},
                      action.data['placement']['placements'])
        self.assertNotIn({'region_name': 'R2'},
                         action.data['placement']['placements'])
        self.assertNotIn({'region_name': 'R4'},
                         action.data['placement']['placements'])

        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        policy._validate_regions.assert_called_once_with(cluster)
        policy._get_current_dist.assert_called_once_with(policy.regions,
                                                         cluster.nodes)
        policy._create_plan.assert_called_once_with(current_dist, regions, 3)

    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_pre_op_count_from_inputs(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions
        plan = {'R1': 1, 'R2': 0, 'R3': 2, 'R4': 0}
        current_dist = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0}
        self.patchobject(policy, '_validate_regions', return_value=regions)
        self.patchobject(policy, '_create_plan', return_value=plan)
        self.patchobject(policy, '_get_current_dist',
                         return_value=current_dist)

        action = mock.Mock()
        action.context = self.context
        action.inputs = {'count': 3}
        action.data = {}

        cluster = mock.Mock()
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)
        self.assertEqual(3, action.data['placement']['count'])
        self.assertEqual(3, len(action.data['placement']['placements']))
        self.assertIn({'region_name': 'R1'},
                      action.data['placement']['placements'])
        self.assertIn({'region_name': 'R3'},
                      action.data['placement']['placements'])
        self.assertNotIn({'region_name': 'R2'},
                         action.data['placement']['placements'])
        self.assertNotIn({'region_name': 'R4'},
                         action.data['placement']['placements'])

    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_pre_op_no_regions(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        self.patchobject(policy, '_validate_regions', return_value=[])

        action = mock.Mock()
        action.context = self.context
        action.data = {'creation': {'count': 3}}

        cluster = mock.Mock()
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)
        self.assertEqual('ERROR', action.data['status'])
        self.assertEqual('No region is found usable.', action.data['reason'])

    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_pre_op_no_feasible_plan(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions
        current_dist = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0}
        self.patchobject(policy, '_validate_regions', return_value=regions)
        self.patchobject(policy, '_create_plan', return_value=None)
        self.patchobject(policy, '_get_current_dist',
                         return_value=current_dist)

        action = mock.Mock()
        action.context = self.context
        action.inputs = {}
        action.data = {'creation': {'count': 3}}

        cluster = mock.Mock()
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)

        self.assertEqual('ERROR', action.data['status'])
        self.assertEqual('There is no feasible plan to accommodate all nodes.',
                         action.data['reason'])

        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        policy._validate_regions.assert_called_once_with(cluster)
        policy._get_current_dist.assert_called_once_with(policy.regions,
                                                         cluster.nodes)
        policy._create_plan.assert_called_once_with(current_dist, regions, 3)
