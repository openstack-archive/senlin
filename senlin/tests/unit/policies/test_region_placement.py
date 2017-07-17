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
import six

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common import scaleutils as su
from senlin.engine import cluster as cm
from senlin.policies import base as pb
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

    @mock.patch.object(pb.Policy, 'validate')
    def test_validate_okay(self, mock_base_validate):
        policy = rp.RegionPlacementPolicy('test-policy', self.spec)
        kc = mock.Mock()
        kc.validate_regions.return_value = ['R1', 'R2', 'R3', 'R4']
        policy._keystoneclient = kc
        ctx = mock.Mock(user='U1', project='P1')

        res = policy.validate(ctx, True)

        self.assertTrue(res)
        mock_base_validate.assert_called_once_with(ctx, True)
        kc.validate_regions.assert_called_once_with(['R1', 'R2', 'R3', 'R4'])

    @mock.patch.object(pb.Policy, 'validate')
    def test_validate_no_validate_props(self, mock_base_validate):
        policy = rp.RegionPlacementPolicy('test-policy', self.spec)
        ctx = mock.Mock(user='U1', project='P1')

        res = policy.validate(ctx, False)

        self.assertTrue(res)
        mock_base_validate.assert_called_once_with(ctx, False)

    @mock.patch.object(pb.Policy, 'validate')
    def test_validate_region_not_found(self, mock_base_validate):
        policy = rp.RegionPlacementPolicy('test-policy', self.spec)
        kc = mock.Mock()
        kc.validate_regions.return_value = ['R2', 'R4']
        policy._keystoneclient = kc
        ctx = mock.Mock(user='U1', project='P1')

        ex = self.assertRaises(exc.InvalidSpec,
                               policy.validate,
                               ctx, True)

        mock_base_validate.assert_called_once_with(ctx, True)
        kc.validate_regions.assert_called_once_with(['R1', 'R2', 'R3', 'R4'])
        self.assertEqual("The specified regions '['R1', 'R3']' could not "
                         "be found.", six.text_type(ex))

    def test__create_plan(self):
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions

        current = {'R1': 2, 'R2': 2, 'R3': 2, 'R4': 1}
        result = policy._create_plan(current, regions, 5, True)
        expected = {'R1': 4, 'R2': 1}
        self.assertEqual(expected, result)

        current = {'R1': 2, 'R2': 2, 'R3': 0, 'R4': 1}
        plan = policy._create_plan(current, regions, 5, True)
        answer = {'R1': 3, 'R2': 1, 'R3': 1}
        self.assertEqual(answer, plan)

        current = {'R1': 2, 'R2': 2, 'R3': 0, 'R4': 1}
        plan = policy._create_plan(current, regions, 3, False)
        answer = {'R2': 2, 'R4': 1}
        self.assertEqual(answer, plan)

        current = {'R1': 4, 'R2': 2, 'R3': 1, 'R4': 1}
        plan = policy._create_plan(current, regions, 3, False)
        answer = {'R2': 1, 'R3': 1, 'R4': 1}
        self.assertEqual(answer, plan)

    def test__get_count_node_create_no_region(self):
        x_profile = mock.Mock(CONTEXT='context', properties={'context': {}})
        x_node = mock.Mock(rt={'profile': x_profile})
        action = mock.Mock(action=consts.NODE_CREATE, entity=x_node)

        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(1, res)

    def test__get_count_node_create_region_specified(self):
        x_profile = mock.Mock(CONTEXT='context',
                              properties={'context': {'region_name': 'foo'}})
        x_node = mock.Mock(rt={'profile': x_profile})
        action = mock.Mock(action=consts.NODE_CREATE, entity=x_node)

        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(0, res)

    def test__get_count_resize_deletion(self):
        action = mock.Mock(action=consts.CLUSTER_RESIZE,
                           data={'deletion': {'count': 3}})

        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(-3, res)

    def test__get_count_resize_creation(self):
        action = mock.Mock(action=consts.CLUSTER_RESIZE,
                           data={'creation': {'count': 3}})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)

        self.assertEqual(3, res)

    @mock.patch.object(su, 'parse_resize_params')
    def test__get_count_resize_parse_error(self, mock_parse):
        x_cluster = mock.Mock()
        x_cluster.nodes = [mock.Mock(), mock.Mock()]
        action = mock.Mock(action=consts.CLUSTER_RESIZE, data={})
        action.entity = x_cluster
        mock_parse.return_value = (pb.CHECK_ERROR, 'Something wrong.')
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)

        self.assertEqual(0, res)
        self.assertEqual(pb.CHECK_ERROR, action.data['status'])
        mock_parse.assert_called_once_with(action, x_cluster, 2)
        self.assertEqual('Something wrong.', action.data['reason'])

    @mock.patch.object(su, 'parse_resize_params')
    def test__get_count_resize_parse_creation(self, mock_parse):
        def fake_parse(action, cluster, current):
            action.data = {'creation': {'count': 3}}
            return pb.CHECK_OK, ''

        x_cluster = mock.Mock()
        x_cluster.nodes = []
        action = mock.Mock(action=consts.CLUSTER_RESIZE, data={})
        action.entity = x_cluster

        mock_parse.side_effect = fake_parse
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)

        self.assertEqual(3, res)
        mock_parse.assert_called_once_with(action, x_cluster, 0)

    @mock.patch.object(su, 'parse_resize_params')
    def test__get_count_resize_parse_deletion(self, mock_parse):
        def fake_parse(action, cluster, current):
            action.data = {'deletion': {'count': 3}}
            return pb.CHECK_OK, ''

        x_cluster = mock.Mock()
        x_cluster.nodes = [mock.Mock(), mock.Mock(), mock.Mock()]
        action = mock.Mock(action=consts.CLUSTER_RESIZE, data={})
        action.entity = x_cluster

        mock_parse.side_effect = fake_parse
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)

        self.assertEqual(-3, res)
        mock_parse.assert_called_once_with(action, x_cluster, 3)

    def test__get_count_scale_in_with_data(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_IN,
                           data={'deletion': {'count': 3}})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(-3, res)

    def test__get_count_scale_in_with_no_data(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_IN,
                           data={'deletion': {'num': 3}})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(-1, res)

    def test__get_count_scale_in_with_inputs(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_IN, data={},
                           inputs={'count': 3})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(-3, res)

    def test__get_count_scale_in_with_incorrect_inputs(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_IN, data={},
                           inputs={'num': 3})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(-1, res)

    def test__get_count_scale_out_with_data(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_OUT,
                           data={'creation': {'count': 3}})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(3, res)

    def test__get_count_scale_out_with_no_data(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_OUT,
                           data={'creation': {'num': 3}})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(1, res)

    def test__get_count_scale_out_with_inputs(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_OUT, data={},
                           inputs={'count': 3})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(3, res)

    def test__get_count_scale_out_with_incorrect_inputs(self):
        action = mock.Mock(action=consts.CLUSTER_SCALE_OUT, data={},
                           inputs={'num': 3})
        policy = rp.RegionPlacementPolicy('p1', self.spec)

        res = policy._get_count('FOO', action)
        self.assertEqual(1, res)

    @mock.patch.object(cm.Cluster, 'load')
    def test_pre_op(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions

        kc = mock.Mock()
        kc.validate_regions.return_value = regions.keys()
        policy._keystoneclient = kc

        plan = {'R1': 1, 'R3': 2}
        self.patchobject(policy, '_create_plan', return_value=plan)

        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_SCALE_OUT'
        action.inputs = {}
        action.data = {
            'creation': {
                'count': 3,
            }
        }

        cluster = mock.Mock()
        current_dist = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0}
        cluster.get_region_distribution.return_value = current_dist
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)

        self.assertEqual(3, action.data['creation']['count'])
        dist = action.data['creation']['regions']
        self.assertEqual(2, len(dist))
        self.assertEqual(1, dist['R1'])
        self.assertEqual(2, dist['R3'])

        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        kc.validate_regions.assert_called_once_with(regions.keys())
        cluster.get_region_distribution.assert_called_once_with(regions.keys())
        policy._create_plan.assert_called_once_with(
            current_dist, regions, 3, True)

    @mock.patch.object(cm.Cluster, 'load')
    def test_pre_op_count_from_inputs(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions

        kc = mock.Mock()
        kc.validate_regions.return_value = regions.keys()
        policy._keystoneclient = kc

        cluster = mock.Mock()
        current_dist = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0}
        cluster.get_region_distribution.return_value = current_dist
        mock_load.return_value = cluster

        plan = {'R1': 1, 'R3': 2}
        self.patchobject(policy, '_create_plan', return_value=plan)

        action = mock.Mock()
        action.context = self.context
        action.action = 'CLUSTER_SCALE_OUT'
        action.inputs = {'count': 3}
        action.data = {}

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)
        self.assertEqual(3, action.data['creation']['count'])
        dist = action.data['creation']['regions']
        self.assertEqual(2, len(dist))
        self.assertEqual(1, dist['R1'])
        self.assertEqual(2, dist['R3'])

    @mock.patch.object(cm.Cluster, 'load')
    def test_pre_op_no_regions(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        kc = mock.Mock()
        kc.validate_regions.return_value = []
        policy._keystoneclient = kc

        action = mock.Mock()
        action.action = 'CLUSTER_SCALE_OUT'
        action.context = self.context
        action.data = {'creation': {'count': 3}}

        cluster = mock.Mock()
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)
        self.assertEqual('ERROR', action.data['status'])
        self.assertEqual('No region is found usable.', action.data['reason'])

    @mock.patch.object(cm.Cluster, 'load')
    def test_pre_op_no_feasible_plan(self, mock_load):
        # test pre_op method whether returns the correct action.data
        policy = rp.RegionPlacementPolicy('p1', self.spec)
        regions = policy.regions

        kc = mock.Mock()
        kc.validate_regions.return_value = regions.keys()
        policy._keystoneclient = kc

        self.patchobject(policy, '_create_plan', return_value=None)

        action = mock.Mock()
        action.action = 'CLUSTER_SCALE_OUT'
        action.context = self.context
        action.inputs = {}
        action.data = {'creation': {'count': 3}}

        cluster = mock.Mock()
        current_dist = {'R1': 0, 'R2': 0, 'R3': 0, 'R4': 0}
        cluster.get_region_distribution.return_value = current_dist
        mock_load.return_value = cluster

        res = policy.pre_op('FAKE_CLUSTER', action)

        self.assertIsNone(res)

        self.assertEqual('ERROR', action.data['status'])
        self.assertEqual('There is no feasible plan to handle all nodes.',
                         action.data['reason'])

        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER')
        kc.validate_regions.assert_called_once_with(regions.keys())
        cluster.get_region_distribution.assert_called_once_with(regions.keys())
        policy._create_plan.assert_called_once_with(
            current_dist, regions, 3, True)
