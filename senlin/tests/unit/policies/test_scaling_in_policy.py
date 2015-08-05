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
from senlin.common import exception
from senlin.common.i18n import _
from senlin.db.sqlalchemy import api as db_api
from senlin.policies import base as policy_base
from senlin.policies import scaling_in_policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestScalingInPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestScalingInPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'adjustment': {
                'type': 'CHANGE_IN_CAPACITY',
                'number': 1,
                'min_step': 1,
                'best_effort': False,
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
        kwargs = {
            'spec': self.spec
        }
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('ScalingInPolicy', policy.type)
        adjustment = self.spec['adjustment']
        self.assertEqual(adjustment['type'], policy.adjustment_type)
        self.assertEqual(adjustment['number'],
                         policy.adjustment_number)
        self.assertEqual(adjustment['min_step'],
                         policy.adjustment_min_step)
        self.assertEqual(adjustment['best_effort'], policy.best_effort)

    def test_policy_init_default_value(self):
        kwargs = {
            'spec': {'adjustment': {}}
        }
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('ScalingInPolicy', policy.type)
        self.assertEqual(consts.CHANGE_IN_CAPACITY, policy.adjustment_type)
        self.assertEqual(1, policy.adjustment_number)
        self.assertEqual(1, policy.adjustment_min_step)
        self.assertEqual(False, policy.best_effort)

    def test_policy_validate(self):
        self.spec['adjustment']['number'] = -1
        kwargs = {
            'spec': self.spec
        }
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

        self.assertRaises(exception.InvalidSpec, policy.validate)

    def test_calculate_adjustment_count(self):
        kwargs = {
            'spec': self.spec
        }

        # adjustment_type as EXACT_CAPACITY
        current_size = 3
        self.spec['adjustment']['type'] = consts.EXACT_CAPACITY
        self.spec['adjustment']['number'] = 1
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(2, count)

        # adjustment_type is CHANGE_IN_CAPACITY
        self.spec['adjustment']['type'] = consts.CHANGE_IN_CAPACITY
        self.spec['adjustment']['number'] = 1
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(1, count)

        # adjustment_type is CHANGE_IN_PERCENTAGE
        current_size = 10
        self.spec['adjustment']['type'] = consts.CHANGE_IN_PERCENTAGE
        self.spec['adjustment']['number'] = 50
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(5, count)

        # adjustment_type is CHANGE_IN_PERCENTAGE and min_step is 2
        self.spec['adjustment']['type'] = consts.CHANGE_IN_PERCENTAGE
        self.spec['adjustment']['number'] = 1
        self.spec['adjustment']['min_step'] = 2
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)
        count = policy._calculate_adjustment_count(current_size)
        self.assertEqual(2, count)

    def test_pre_op_pass_without_input(self):
        action = mock.Mock()
        action.context = self.context
        action.inputs = {}
        kwargs = {
            'spec': self.spec
        }
        self.spec['adjustment']['type'] = consts.EXACT_CAPACITY
        self.spec['adjustment']['number'] = 1
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

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

    def test_pre_op_pass_with_input(self):
        action = mock.Mock()
        action.context = self.context
        action.inputs = {'count': 1}
        kwargs = {
            'spec': self.spec
        }
        self.spec['adjustment']['type'] = consts.CHANGE_IN_CAPACITY
        self.spec['adjustment']['number'] = 2
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': action.inputs['count'],
            },
            'reason': 'Scaling request validated.',
            'status': policy_base.CHECK_OK,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_fail_negative_count(self):
        action = mock.Mock()
        action.context = self.context
        action.inputs = {}
        kwargs = {
            'spec': self.spec
        }
        self.spec['adjustment']['type'] = consts.EXACT_CAPACITY
        self.spec['adjustment']['number'] = 5
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

        policy.pre_op(self.cluster['id'], action)
        reason = _('Negative number is invalid for scaling in policy.')

        pd = {
            'deletion': {
                'count': -2,
            },
            'reason': reason,
            'status': policy_base.CHECK_ERROR,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_fail_exceed_min_size(self):
        action = mock.Mock()
        action.context = self.context
        action.inputs = {}
        kwargs = {
            'spec': self.spec
        }
        self.spec['adjustment']['type'] = consts.CHANGE_IN_CAPACITY
        self.spec['adjustment']['number'] = 3
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

        policy.pre_op(self.cluster['id'], action)
        reason = _('Attempted scaling exceeds minimum size.')

        pd = {
            'deletion': {
                'count': 3,
            },
            'reason': reason,
            'status': policy_base.CHECK_ERROR,
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_pass_best_effort(self):
        action = mock.Mock()
        action.context = self.context
        action.inputs = {}
        self.spec['adjustment']['best_effort'] = True
        kwargs = {
            'spec': self.spec
        }
        self.spec['adjustment']['type'] = consts.CHANGE_IN_CAPACITY
        self.spec['adjustment']['number'] = 3
        policy = scaling_in_policy.ScalingInPolicy('ScalingInPolicy',
                                                   'test-policy',
                                                   **kwargs)

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
