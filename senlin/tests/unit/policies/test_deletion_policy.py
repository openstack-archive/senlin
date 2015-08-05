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
from senlin.policies import deletion_policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestDeletionPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestDeletionPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'criteria': 'OLDEST_FIRST',
            'destroy_after_deletion': True,
            'grace_period': 60,
            'reduce_desired_capacity': False
        }
        self.profile1 = self._create_profile('PROFILE1')
        self.profile2 = self._create_profile('PROFILE2')
        self.cluster = self._create_cluster('CLUSTER1',
                                            self.profile1['id'])
        self.nodes_p1 = self._create_nodes(self.cluster['id'],
                                           self.profile1['id'], 3)
        self.nodes_p2 = self._create_nodes(self.cluster['id'],
                                           self.profile2['id'], 3)

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
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('DeletionPolicy', policy.type)
        self.assertEqual(self.spec['criteria'], policy.criteria)
        self.assertEqual(self.spec['destroy_after_deletion'],
                         policy.destroy_after_deletion)
        self.assertEqual(self.spec['grace_period'], policy.grace_period)
        self.assertEqual(self.spec['reduce_desired_capacity'],
                         policy.reduce_desired_capacity)

    def test_select_candidates_oldest_first(self):
        self.spec['criteria'] = deletion_policy.DeletionPolicy.OLDEST_FIRST
        kwargs = {
            'spec': self.spec
        }
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        nodes = policy._select_candidates(self.context, self.cluster['id'], 1)
        self.assertEqual(1, len(nodes))
        self.assertEqual(self.nodes_p1[0], nodes[0])

        nodes = policy._select_candidates(self.context, self.cluster['id'], 2)
        self.assertEqual(2, len(nodes))
        self.assertEqual(self.nodes_p1[0], nodes[0])
        self.assertEqual(self.nodes_p1[1], nodes[1])

    def test_select_candidates_youngest_first(self):
        self.spec['criteria'] = deletion_policy.DeletionPolicy.YOUNGEST_FIRST
        kwargs = {
            'spec': self.spec
        }
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        nodes = policy._select_candidates(self.context, self.cluster['id'], 1)
        self.assertEqual(1, len(nodes))
        self.assertEqual(self.nodes_p2[2], nodes[0])

        nodes = policy._select_candidates(self.context, self.cluster['id'], 2)
        self.assertEqual(2, len(nodes))
        self.assertEqual(self.nodes_p2[2], nodes[0])
        self.assertEqual(self.nodes_p2[1], nodes[1])

    def test_select_candidates_oldest_profile_first(self):
        criteria = deletion_policy.DeletionPolicy.OLDEST_PROFILE_FIRST
        self.spec['criteria'] = criteria
        kwargs = {
            'spec': self.spec
        }
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        nodes = policy._select_candidates(self.context, self.cluster['id'], 1)
        self.assertEqual(1, len(nodes))
        self.assertEqual(self.nodes_p1[0], nodes[0])

        nodes = policy._select_candidates(self.context, self.cluster['id'], 2)
        self.assertEqual(2, len(nodes))
        self.assertEqual(self.nodes_p1[0], nodes[0])
        self.assertEqual(self.nodes_p1[1], nodes[1])

    def test_select_candidates_random(self):
        self.spec['criteria'] = deletion_policy.DeletionPolicy.RANDOM
        kwargs = {
            'spec': self.spec
        }
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        nodes = policy._select_candidates(self.context, self.cluster['id'], 1)
        self.assertEqual(1, len(nodes))
        nodes = policy._select_candidates(self.context, self.cluster['id'], 3)
        self.assertEqual(3, len(nodes))
        nodes = policy._select_candidates(self.context, self.cluster['id'], 10)
        self.assertEqual(6, len(nodes))

    def test_pre_op(self):
        action = mock.Mock()
        action.context = self.context
        kwargs = {
            'spec': self.spec
        }
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        # action data doesn't have 'deletion' field
        action.data.get.return_value = None
        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'candidates': [self.nodes_p1[0]],
                'destroy_after_deletion': True,
                'grace_period': 60,
            }
        }
        action.data.update.assert_called_with(pd)

        # action data has 'deletion' field, but 'count' is not provided
        action.data.get.return_value = {'abc': 123}
        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'abc': 123,
                'candidates': [self.nodes_p1[0]],
                'destroy_after_deletion': True,
                'grace_period': 60,
            }
        }
        action.data.update.assert_called_with(pd)

        # 'count' is provided in deletion field of action data
        action.data.get.return_value = {'count': 2}
        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': 2,
                'candidates': [self.nodes_p1[0], self.nodes_p1[1]],
                'destroy_after_deletion': True,
                'grace_period': 60,
            }
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)

    def test_pre_op_candidates_provided(self):
        action = mock.Mock()
        action.context = self.context
        kwargs = {
            'spec': self.spec
        }
        policy = deletion_policy.DeletionPolicy('DeletionPolicy',
                                                'test-policy',
                                                **kwargs)

        # Both 'count' and 'candidates' are provided in deletion
        # field of action data
        action.data.get.return_value = {
            'count': 2,
            'candidates': [
                self.nodes_p1[0],
                self.nodes_p2[2],
            ],
        }
        policy.pre_op(self.cluster['id'], action)
        pd = {
            'deletion': {
                'count': 2,
                'candidates': [self.nodes_p1[0], self.nodes_p2[2]],
                'destroy_after_deletion': True,
                'grace_period': 60,
            }
        }
        action.data.update.assert_called_with(pd)
        action.store.assert_called_with(self.context)
