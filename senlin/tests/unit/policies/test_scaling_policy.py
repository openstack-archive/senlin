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
from senlin.objects import node as no
from senlin.policies import base as pb
from senlin.policies import scaling_policy as sp
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

PROFILE_ID = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'
CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'
CLUSTER_NOMAXSIZE_ID = 'e470c11d-910d-491b-a7c3-93b047a6108d'


class TestScalingPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestScalingPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'senlin.policy.scaling',
            'version': '1.0',
            'properties': {
                'event': 'CLUSTER_SCALE_IN',
                'adjustment': {
                    'type': 'CHANGE_IN_CAPACITY',
                    'number': 1,
                    'min_step': 1,
                    'best_effort': False,
                    'cooldown': 3,
                }
            }
        }
        self.profile = utils.create_profile(self.context, PROFILE_ID)
        self.cluster = utils.create_cluster(self.context, CLUSTER_ID,
                                            PROFILE_ID)
        self.cluster_no_maxsize = utils. \
            create_cluster(self.context, CLUSTER_NOMAXSIZE_ID,
                           PROFILE_ID, max_size=-1)

    def _create_nodes(self, count):
        NODE_IDS = [
            '6eaa45fa-bd2e-426d-ae49-f75db1a4bd73',
            '8bf73953-b57b-4e6b-bdef-83fa9420befb',
            'c3058ea0-5241-466b-89bc-6a85f6050a11',
        ]
        PHYSICAL_IDS = [
            '2417c5d6-9a89-4637-9ba6-82c00b180cb7',
            '374bf2b9-30ba-4a9b-822b-1196f6d4a368',
            '2a1b7e37-de18-4b22-9489-a7a413fdfe48',
        ]

        nodes = []
        for i in range(count):
            node = utils.create_node(self.context, NODE_IDS[i], PROFILE_ID,
                                     CLUSTER_ID, PHYSICAL_IDS[i])
            nodes.append(node)
        return nodes

    def test_policy_init(self):
        policy = sp.ScalingPolicy('p1', self.spec)
        self.assertFalse(policy.singleton)

        self.assertIsNone(policy.id)
        self.assertEqual('p1', policy.name)
        self.assertEqual('senlin.policy.scaling-1.0', policy.type)
        self.assertEqual('CLUSTER_SCALE_IN', policy.event)
        adjustment = self.spec['properties']['adjustment']
        self.assertEqual(adjustment['type'], policy.adjustment_type)
        self.assertEqual(adjustment['number'], policy.adjustment_number)
        self.assertEqual(adjustment['min_step'], policy.adjustment_min_step)
        self.assertEqual(adjustment['best_effort'], policy.best_effort)
        self.assertEqual(adjustment['cooldown'], policy.cooldown)

    def test_policy_init_default_value(self):
        self.spec['properties']['adjustment'] = {}
        policy = sp.ScalingPolicy('p1', self.spec)

        self.assertIsNone(policy.id)
        self.assertEqual('senlin.policy.scaling-1.0', policy.type)
        self.assertEqual('p1', policy.name)
        self.assertEqual(consts.CHANGE_IN_CAPACITY, policy.adjustment_type)
        self.assertEqual(1, policy.adjustment_number)
        self.assertEqual(1, policy.adjustment_min_step)
        self.assertFalse(policy.best_effort)
        self.assertEqual(0, policy.cooldown)

    def test_validate(self):
        self.spec['properties']['adjustment'] = {}
        policy = sp.ScalingPolicy('p1', self.spec)

        policy.validate(self.context)

    def test_validate_bad_number(self):
        self.spec['properties']['adjustment'] = {"number": -1}
        policy = sp.ScalingPolicy('p1', self.spec)

        ex = self.assertRaises(exc.InvalidSpec, policy.validate, self.context)

        self.assertEqual("the 'number' for 'adjustment' must be > 0",
                         six.text_type(ex))

    def test_validate_bad_min_step(self):
        self.spec['properties']['adjustment'] = {"min_step": -1}
        policy = sp.ScalingPolicy('p1', self.spec)

        ex = self.assertRaises(exc.InvalidSpec, policy.validate, self.context)

        self.assertEqual("the 'min_step' for 'adjustment' must be >= 0",
                         six.text_type(ex))

    def test_validate_bad_cooldown(self):
        self.spec['properties']['adjustment'] = {"cooldown": -1}
        policy = sp.ScalingPolicy('p1', self.spec)

        ex = self.assertRaises(exc.InvalidSpec, policy.validate, self.context)

        self.assertEqual("the 'cooldown' for 'adjustment' must be >= 0",
                         six.text_type(ex))

    def test_calculate_adjustment_count(self):
        adjustment = self.spec['properties']['adjustment']
        # adjustment_type as EXACT_CAPACITY and event as cluster_scale_in
        current_size = 3
        adjustment['type'] = consts.EXACT_CAPACITY
        adjustment['number'] = 1
        policy = sp.ScalingPolicy('test-policy', self.spec)
        policy.event = consts.CLUSTER_SCALE_IN
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(2, count)

        # adjustment_type as EXACT_CAPACITY and event as cluster_scale_out
        current_size = 3
        adjustment['type'] = consts.EXACT_CAPACITY
        adjustment['number'] = 1
        policy = sp.ScalingPolicy('test-policy', self.spec)
        policy.event = consts.CLUSTER_SCALE_OUT
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(-2, count)

        # adjustment_type is CHANGE_IN_CAPACITY
        adjustment['type'] = consts.CHANGE_IN_CAPACITY
        adjustment['number'] = 1
        policy = sp.ScalingPolicy('test-policy', self.spec)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(1, count)

        # adjustment_type is CHANGE_IN_PERCENTAGE
        current_size = 10
        adjustment['type'] = consts.CHANGE_IN_PERCENTAGE
        adjustment['number'] = 50
        policy = sp.ScalingPolicy('test-policy', self.spec)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(5, count)

        # adjustment_type is CHANGE_IN_PERCENTAGE and min_step is 2
        adjustment['type'] = consts.CHANGE_IN_PERCENTAGE
        adjustment['number'] = 1
        adjustment['min_step'] = 2
        policy = sp.ScalingPolicy('test-policy', self.spec)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(2, count)

    def test_pre_op_pass_without_input(self):
        nodes = self._create_nodes(3)
        self.cluster.nodes = nodes

        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
        action.entity = self.cluster

        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.EXACT_CAPACITY
        adjustment['number'] = 1
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': 2,
            },
            'reason': 'Scaling request validated.',
            'status': pb.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_pass_with_input(self):
        nodes = self._create_nodes(3)
        self.cluster.nodes = nodes

        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {'count': 1}
        action.entity = self.cluster

        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.CHANGE_IN_CAPACITY
        adjustment['number'] = 2
        policy = sp.ScalingPolicy('p1', self.spec)

        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': 1,
            },
            'reason': 'Scaling request validated.',
            'status': pb.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

        # count value is string rather than integer
        action.inputs = {'count': '1'}
        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': 1,
            },
            'reason': 'Scaling request validated.',
            'status': pb.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)

    @mock.patch.object(sp.ScalingPolicy, '_calculate_adjustment_count')
    def test_pre_op_pass_check_effort(self, mock_adjustmentcount):
        # Cluster with maxsize and best_effort is False
        self.cluster.nodes = [mock.Mock(), mock.Mock()]
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_OUT
        action.inputs = {}
        action.entity = self.cluster

        mock_adjustmentcount.return_value = 1
        policy = sp.ScalingPolicy('test-policy', self.spec)
        policy.event = consts.CLUSTER_SCALE_OUT
        policy.best_effort = True
        policy.pre_op(self.cluster_no_maxsize['id'], action)
        pd = {
            'creation': {
                'count': 1,
            },
            'reason': 'Scaling request validated.',
            'status': pb.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_fail_negative_count(self):
        nodes = self._create_nodes(3)
        self.cluster.nodes = nodes

        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
        action.entity = self.cluster

        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.EXACT_CAPACITY
        adjustment['number'] = 5
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)

        pd = {
            'status': pb.CHECK_ERROR,
            'reason': "Invalid count (-2) for action 'CLUSTER_SCALE_IN'.",
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_fail_below_min_size(self):
        nodes = self._create_nodes(3)
        self.cluster.nodes = nodes

        action = mock.Mock()
        action.action = consts.CLUSTER_SCALE_IN
        action.context = self.context
        action.inputs = {}
        action.entity = self.cluster

        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.CHANGE_IN_CAPACITY
        adjustment['number'] = 3
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)

        pd = {
            'status': pb.CHECK_ERROR,
            'reason': ("The target capacity (0) is less than the cluster's "
                       "min_size (1)."),
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_pass_best_effort(self):
        nodes = self._create_nodes(3)
        self.cluster.nodes = nodes

        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
        action.entity = self.cluster

        adjustment = self.spec['properties']['adjustment']
        adjustment['best_effort'] = True
        adjustment['type'] = consts.CHANGE_IN_CAPACITY
        adjustment['number'] = 3
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)

        pd = {
            'deletion': {
                'count': 2,
            },
            'status': pb.CHECK_OK,
            'reason': 'Scaling request validated.',
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_with_bad_nodes(self):
        nodes = self._create_nodes(3)
        no.Node.update(self.context, nodes[0].id, {'status': 'ERROR'})
        self.cluster.nodes = nodes

        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
        action.entity = self.cluster

        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.EXACT_CAPACITY
        adjustment['number'] = 1
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': 2,
            },
            'reason': 'Scaling request validated.',
            'status': pb.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_need_check_in_event(self):
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.data = {}

        policy = sp.ScalingPolicy('test-policy', self.spec)
        res = policy.need_check('BEFORE', action)
        self.assertTrue(res)

    def test_need_check_not_in_event(self):
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_OUT
        action.data = {}

        policy = sp.ScalingPolicy('test-policy', self.spec)
        res = policy.need_check('BEFORE', action)
        self.assertFalse(res)
