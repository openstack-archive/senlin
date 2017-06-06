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

import copy
import mock

from senlin.common import consts
from senlin.common import scaleutils as su
from senlin.policies import deletion_policy as dp
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestDeletionPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestDeletionPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.deletion',
            'version': '1.0',
            'properties': {
                'criteria': 'OLDEST_FIRST',
                'destroy_after_deletion': True,
                'grace_period': 60,
                'reduce_desired_capacity': False
            }
        }

    def test_policy_init(self):
        policy = dp.DeletionPolicy('test-policy', self.spec)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.deletion-1.0', policy.type)
        self.assertEqual('OLDEST_FIRST', policy.criteria)
        self.assertTrue(policy.destroy_after_deletion)
        self.assertEqual(60, policy.grace_period)
        self.assertFalse(policy.reduce_desired_capacity)

    @mock.patch.object(su, 'nodes_by_random')
    def test__victims_by_regions_random(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_region.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['2', '3']]

        self.spec['properties']['criteria'] = 'RANDOM'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_regions(cluster, {'R1': 1, 'R2': 2})
        self.assertEqual(['1', '2', '3'], res)
        mock_select.assert_has_calls([
            mock.call([node1], 1),
            mock.call([node2, node3], 2)
        ])
        cluster.nodes_by_region.assert_has_calls([
            mock.call('R1'), mock.call('R2')])

    @mock.patch.object(su, 'nodes_by_profile_age')
    def test__victims_by_regions_profile_age(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_region.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['2', '3']]

        self.spec['properties']['criteria'] = 'OLDEST_PROFILE_FIRST'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_regions(cluster, {'R1': 1, 'R2': 2})
        self.assertEqual(['1', '2', '3'], res)
        mock_select.assert_has_calls([
            mock.call([node1], 1),
            mock.call([node2, node3], 2)
        ])
        cluster.nodes_by_region.assert_has_calls([
            mock.call('R1'), mock.call('R2')])

    @mock.patch.object(su, 'nodes_by_age')
    def test__victims_by_regions_age_oldest(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_region.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['2', '3']]

        self.spec['properties']['criteria'] = 'OLDEST_FIRST'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_regions(cluster, {'R1': 1, 'R2': 2})
        self.assertEqual(['1', '2', '3'], res)
        mock_select.assert_has_calls([
            mock.call([node1], 1, True),
            mock.call([node2, node3], 2, True)
        ])
        cluster.nodes_by_region.assert_has_calls([
            mock.call('R1'), mock.call('R2')])

    @mock.patch.object(su, 'nodes_by_age')
    def test__victims_by_regions_age_youngest(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_region.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['2', '3']]

        self.spec['properties']['criteria'] = 'YOUNGEST_FIRST'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_regions(cluster, {'R1': 1, 'R2': 2})
        self.assertEqual(['1', '2', '3'], res)
        mock_select.assert_has_calls([
            mock.call([node1], 1, False),
            mock.call([node2, node3], 2, False)
        ])
        cluster.nodes_by_region.assert_has_calls([
            mock.call('R1'), mock.call('R2')])

    @mock.patch.object(su, 'nodes_by_random')
    def test__victims_by_zones_random(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_zone.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['3']]

        self.spec['properties']['criteria'] = 'RANDOM'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_zones(cluster, {'AZ1': 1, 'AZ2': 1})
        self.assertEqual(['1', '3'], res)
        mock_select.assert_has_calls([
            mock.call([node1], 1),
            mock.call([node2, node3], 1)
        ])
        cluster.nodes_by_zone.assert_has_calls(
            [mock.call('AZ1'), mock.call('AZ2')],
        )

    @mock.patch.object(su, 'nodes_by_profile_age')
    def test__victims_by_zones_profile_age(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_zone.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['2']]

        self.spec['properties']['criteria'] = 'OLDEST_PROFILE_FIRST'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_zones(cluster, {'AZ1': 1, 'AZ2': 1})
        self.assertEqual(['1', '2'], res)
        mock_select.assert_has_calls(
            [
                mock.call([node1], 1),
                mock.call([node2, node3], 1)
            ],
        )
        cluster.nodes_by_zone.assert_has_calls(
            [mock.call('AZ1'), mock.call('AZ2')],
        )

    @mock.patch.object(su, 'nodes_by_age')
    def test__victims_by_zones_age_oldest(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=2)
        node3 = mock.Mock(id=3)
        cluster.nodes_by_zone.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['3']]

        self.spec['properties']['criteria'] = 'OLDEST_FIRST'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_zones(cluster, {'AZ1': 1, 'AZ8': 1})
        self.assertEqual(['1', '3'], res)
        mock_select.assert_has_calls([
            mock.call([node1], 1, True),
            mock.call([node2, node3], 1, True)
        ])
        cluster.nodes_by_zone.assert_has_calls(
            [mock.call('AZ1'), mock.call('AZ8')],
        )

    @mock.patch.object(su, 'nodes_by_age')
    def test__victims_by_zones_age_youngest(self, mock_select):
        cluster = mock.Mock()
        node1 = mock.Mock(id=1)
        node2 = mock.Mock(id=3)
        node3 = mock.Mock(id=5)
        cluster.nodes_by_zone.side_effect = [
            [node1], [node2, node3]
        ]

        mock_select.side_effect = [['1'], ['3', '5']]

        self.spec['properties']['criteria'] = 'YOUNGEST_FIRST'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        res = policy._victims_by_zones(cluster, {'AZ5': 1, 'AZ6': 2})
        self.assertEqual(['1', '3', '5'], res)
        mock_select.assert_has_calls(
            [
                mock.call([node1], 1, False),
                mock.call([node2, node3], 2, False)
            ],
        )
        cluster.nodes_by_zone.assert_has_calls(
            [mock.call('AZ5'), mock.call('AZ6')],
        )

    def test__update_action_clean(self):
        action = mock.Mock()
        action.data = {}

        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy._update_action(action, ['N1', 'N2'])

        pd = {
            'status': 'OK',
            'reason': 'Candidates generated',
            'deletion': {
                'count': 2,
                'candidates': ['N1', 'N2'],
                'destroy_after_deletion': True,
                'grace_period': 60,
                'reduce_desired_capacity': False,
            }
        }
        self.assertEqual(pd, action.data)
        action.store.assert_called_with(action.context)

    def test__update_action_override(self):
        action = mock.Mock()
        action.data = {
            'deletion': {
                'count': 3,
            }
        }

        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy._update_action(action, ['N1', 'N2'])

        pd = {
            'status': 'OK',
            'reason': 'Candidates generated',
            'deletion': {
                'count': 2,
                'candidates': ['N1', 'N2'],
                'destroy_after_deletion': True,
                'grace_period': 60,
                'reduce_desired_capacity': False,
            }
        }
        self.assertEqual(pd, action.data)
        action.store.assert_called_with(action.context)

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    def test_pre_op_del_nodes(self, mock_update):
        action = mock.Mock()
        action.context = self.context
        action.inputs = {
            'count': 2,
            'candidates': ['N1', 'N2'],
        }
        action.data = {}
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['N1', 'N2'])

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    def test_pre_op_node_delete(self, mock_update):
        action = mock.Mock(action=consts.NODE_DELETE, context=self.context,
                           inputs={}, data={}, entity=mock.Mock(id='NODE_ID'))
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['NODE_ID'])

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_age')
    def test_pre_op_with_count_decisions(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={},
                           data={'deletion': {'count': 2}})
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        mock_select.return_value = ['NODE1', 'NODE2']
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])
        mock_select.assert_called_once_with(cluster.nodes, 2, True)

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(dp.DeletionPolicy, '_victims_by_regions')
    def test_pre_op_with_region_decisions(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={})
        action.data = {
            'deletion': {
                'count': 2,
                'regions': {
                    'R1': 1,
                    'R2': 1
                }
            }
        }
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        mock_select.return_value = ['NODE1', 'NODE2']
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])
        mock_select.assert_called_once_with(cluster, {'R1': 1, 'R2': 1})

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(dp.DeletionPolicy, '_victims_by_zones')
    def test_pre_op_with_zone_decisions(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={})
        action.data = {
            'deletion': {
                'count': 2,
                'zones': {
                    'AZ1': 1,
                    'AZ2': 1
                }
            }
        }
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        mock_select.return_value = ['NODE1', 'NODE2']
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])
        mock_select.assert_called_once_with(cluster, {'AZ1': 1, 'AZ2': 1})

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_age')
    def test_pre_op_scale_in_with_count(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, data={}, inputs={'count': 2},
                           action=consts.CLUSTER_SCALE_IN)
        cluster = mock.Mock(nodes=[mock.Mock()])
        action.entity = cluster
        mock_select.return_value = ['NODE_ID']
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['NODE_ID'])
        # the following was invoked with 1 because the input count is
        # greater than the cluster size
        mock_select.assert_called_once_with(cluster.nodes, 1, True)

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_age')
    def test_pre_op_scale_in_without_count(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, data={}, inputs={},
                           action=consts.CLUSTER_SCALE_IN)
        cluster = mock.Mock(nodes=[mock.Mock()])
        action.entity = cluster
        mock_select.return_value = ['NODE_ID']
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_update.assert_called_once_with(action, ['NODE_ID'])
        # the following was invoked with 1 because the input count is
        # not specified so 1 becomes the default
        mock_select.assert_called_once_with(cluster.nodes, 1, True)

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'parse_resize_params')
    def test_pre_op_resize_failed_parse(self, mock_parse, mock_update):
        action = mock.Mock(context=self.context, inputs={}, data={},
                           action=consts.CLUSTER_RESIZE)
        cluster = mock.Mock(nodes=[mock.Mock(), mock.Mock()])
        action.entity = cluster
        mock_parse.return_value = 'ERROR', 'Failed parsing.'
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        self.assertEqual('ERROR', action.data['status'])
        self.assertEqual('Failed parsing.', action.data['reason'])
        mock_parse.assert_called_once_with(action, cluster, 2)
        self.assertEqual(0, mock_update.call_count)

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'parse_resize_params')
    def test_pre_op_resize_not_deletion(self, mock_parse, mock_update):
        def fake_parse(action, cluster, current):
            action.data = {}
            return 'OK', 'cool'

        action = mock.Mock(context=self.context, inputs={},
                           action=consts.CLUSTER_RESIZE)
        cluster = mock.Mock(nodes=[mock.Mock(), mock.Mock()])
        action.entity = cluster
        mock_parse.side_effect = fake_parse
        policy = dp.DeletionPolicy('test-policy', self.spec)
        # a simulation of non-deletion RESZIE
        action.data = {}

        policy.pre_op('FAKE_ID', action)

        mock_parse.assert_called_once_with(action, cluster, 2)
        self.assertEqual(0, mock_update.call_count)

    @mock.patch.object(su, 'parse_resize_params')
    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_age')
    def test_pre_op_resize_with_count(self, mock_select, mock_update,
                                      mock_parse):
        def fake_parse(a, cluster, current):
            a.data = {
                'deletion': {
                    'count': 2
                }
            }
            return 'OK', 'cool'

        action = mock.Mock(context=self.context, inputs={}, data={},
                           action=consts.CLUSTER_RESIZE)
        cluster = mock.Mock(nodes=[mock.Mock(), mock.Mock()])
        action.entity = cluster
        mock_parse.side_effect = fake_parse
        mock_select.return_value = ['NID']
        policy = dp.DeletionPolicy('test-policy', self.spec)

        policy.pre_op('FAKE_ID', action)

        mock_parse.assert_called_once_with(action, cluster, 2)
        mock_update.assert_called_once_with(action, ['NID'])

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_random')
    def test_pre_op_do_random(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={},
                           data={'deletion': {'count': 2}})
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        mock_select.return_value = ['NODE1', 'NODE2']
        spec = copy.deepcopy(self.spec)
        spec['properties']['criteria'] = 'RANDOM'
        policy = dp.DeletionPolicy('test-policy', spec)

        policy.pre_op('FAKE_ID', action)

        mock_select.assert_called_once_with(cluster.nodes, 2)
        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_profile_age')
    def test_pre_op_do_oldest_profile(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={},
                           data={'deletion': {'count': 2}})
        mock_select.return_value = ['NODE1', 'NODE2']
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        spec = copy.deepcopy(self.spec)
        spec['properties']['criteria'] = 'OLDEST_PROFILE_FIRST'
        policy = dp.DeletionPolicy('test-policy', spec)

        policy.pre_op('FAKE_ID', action)

        mock_select.assert_called_once_with(cluster.nodes, 2)
        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_age')
    def test_pre_op_do_oldest_first(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={},
                           data={'deletion': {'count': 2}})
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        mock_select.return_value = ['NODE1', 'NODE2']
        spec = copy.deepcopy(self.spec)
        spec['properties']['criteria'] = 'OLDEST_FIRST'
        policy = dp.DeletionPolicy('test-policy', spec)

        policy.pre_op('FAKE_ID', action)

        mock_select.assert_called_once_with(cluster.nodes, 2, True)
        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])

    @mock.patch.object(dp.DeletionPolicy, '_update_action')
    @mock.patch.object(su, 'nodes_by_age')
    def test_pre_op_do_youngest_first(self, mock_select, mock_update):
        action = mock.Mock(context=self.context, inputs={},
                           data={'deletion': {'count': 2}})
        cluster = mock.Mock(nodes=['a', 'b', 'c'])
        action.entity = cluster
        mock_select.return_value = ['NODE1', 'NODE2']
        spec = copy.deepcopy(self.spec)
        spec['properties']['criteria'] = 'YOUNGEST_FIRST'
        policy = dp.DeletionPolicy('test-policy', spec)

        policy.pre_op('FAKE_ID', action)

        mock_select.assert_called_once_with(cluster.nodes, 2, False)
        mock_update.assert_called_once_with(action, ['NODE1', 'NODE2'])
