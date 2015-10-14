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

from senlin.common import consts
from senlin.common.i18n import _
from senlin.db.sqlalchemy import api as db_api
from senlin.policies import base as policy_base
from senlin.policies import scaling_policy as sp
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


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
                }
            }
        }
        self.profile = self._create_profile('PROFILE1')
        self.cluster = self._create_cluster('CLUSTER1',
                                            self.profile['id'])
        self.nodes = self._create_nodes(self.cluster['id'],
                                        self.profile['id'], 3)

    def _create_profile(self, profile_id):
        values = {
            'id': profile_id,
            'type': 'os.heat.stack',
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
            'min_size': 1,
            'max_size': 5,
            'desired_capacity': 3,
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
        policy = sp.ScalingPolicy('p1', self.spec)
        self.assertEqual(False, policy.singleton)

        self.assertIsNone(policy.id)
        self.assertEqual('p1', policy.name)
        self.assertEqual('senlin.policy.scaling-1.0', policy.type)
        self.assertEqual('CLUSTER_SCALE_IN', policy.event)
        adjustment = self.spec['properties']['adjustment']
        self.assertEqual(adjustment['type'], policy.adjustment_type)
        self.assertEqual(adjustment['number'], policy.adjustment_number)
        self.assertEqual(adjustment['min_step'], policy.adjustment_min_step)
        self.assertEqual(adjustment['best_effort'], policy.best_effort)

    def test_policy_init_default_value(self):
        self.spec['properties']['adjustment'] = {}
        policy = sp.ScalingPolicy('p1', self.spec)

        self.assertIsNone(policy.id)
        self.assertEqual('senlin.policy.scaling-1.0', policy.type)
        self.assertEqual('p1', policy.name)
        self.assertEqual(consts.CHANGE_IN_CAPACITY, policy.adjustment_type)
        self.assertEqual(1, policy.adjustment_number)
        self.assertEqual(1, policy.adjustment_min_step)
        self.assertEqual(False, policy.best_effort)

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
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
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
            'status': policy_base.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_action_not_in_event(self):
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_OUT
        action.data = {}

        policy = sp.ScalingPolicy('test-policy', self.spec)
        policy.pre_op(self.cluster['id'], action)
        expected = {
            'reason': 'Scaling request validated.',
            'status': policy_base.CHECK_OK,
        }
        self.assertEqual(expected, action.data)
        action.store.assert_called_with(self.context)

    def test_pre_op_pass_with_input(self):
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {'count': 1}
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
            'status': policy_base.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_fail_negative_count(self):
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.EXACT_CAPACITY
        adjustment['number'] = 5
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)
        reason = _('Count (-2) invalid for action CLUSTER_SCALE_IN.')

        pd = {
            'reason': reason,
            'status': policy_base.CHECK_ERROR,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_fail_below_min_size(self):
        action = mock.Mock()
        action.action = consts.CLUSTER_SCALE_IN
        action.context = self.context
        action.inputs = {}
        adjustment = self.spec['properties']['adjustment']
        adjustment['type'] = consts.CHANGE_IN_CAPACITY
        adjustment['number'] = 3
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)
        reason = _('Attempted scaling below minimum size.')

        pd = {
            'reason': reason,
            'status': policy_base.CHECK_ERROR,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_pass_best_effort(self):
        action = mock.Mock()
        action.context = self.context
        action.action = consts.CLUSTER_SCALE_IN
        action.inputs = {}
        adjustment = self.spec['properties']['adjustment']
        adjustment['best_effort'] = True
        adjustment['type'] = consts.CHANGE_IN_CAPACITY
        adjustment['number'] = 3
        policy = sp.ScalingPolicy('test-policy', self.spec)

        policy.pre_op(self.cluster['id'], action)
        reason = _('Do best effort scaling.')

        pd = {
            'deletion': {
                'count': 2,
            },
            'reason': reason,
            'status': policy_base.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)
