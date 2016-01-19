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

from datetime import timedelta
from oslo_utils import timeutils
import six

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import cluster_policy as cpm
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestClusterPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestClusterPolicy, self).setUp()
        self.context = utils.dummy_context()

    def test_cluster_policy_init(self):
        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy('fake-cluster', 'fake-policy', **values)

        self.assertIsNone(cp.id)
        self.assertEqual('fake-cluster', cp.cluster_id)
        self.assertEqual('fake-policy', cp.policy_id)
        self.assertEqual(12, cp.priority)
        self.assertTrue(True, cp.enabled)
        self.assertEqual({}, cp.data)
        self.assertIsNone(cp.last_op)
        self.assertEqual('', cp.cluster_name)
        self.assertEqual('', cp.policy_type)
        self.assertEqual('', cp.policy_name)

    def test_cluster_policy_store(self):
        cluster = self._create_cluster('fake-cluster')
        policy = self._create_policy('fake-policy')
        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy(cluster.id, policy.id, **values)
        self.assertIsNone(cp.id)
        cp_id = cp.store(self.context)
        self.assertIsNotNone(cp_id)

        result = db_api.cluster_policy_get(self.context, 'fake-cluster',
                                           'fake-policy')

        self.assertIsNotNone(result)
        self.assertEqual(12, result.priority)
        self.assertTrue(result.enabled)
        self.assertEqual({}, result.data)
        self.assertIsNone(result.last_op)

        # do an update
        cp.enabled = False
        cp.priority = 60
        cp.data = {'foo': 'bar'}
        timestamp = timeutils.utcnow()
        cp.last_op = timestamp

        new_id = cp.store(self.context)
        self.assertEqual(cp_id, new_id)

        result = db_api.cluster_policy_get(self.context, 'fake-cluster',
                                           'fake-policy')

        self.assertIsNotNone(result)
        self.assertFalse(result.enabled)
        self.assertEqual(60, result.priority)
        self.assertEqual({'foo': 'bar'}, result.data)
        self.assertEqual(timestamp, result.last_op)

    def _create_cluster(self, cluster_id):
        values = {
            'id': cluster_id,
            'profile_id': 'some-profile',
            'name': 'test_cluster',
            'user': 'user',
            'project': 'project'
        }
        return db_api.cluster_create(self.context, values)

    def _create_policy(self, policy_id):
        values = {
            'id': policy_id,
            'type': 'policy-type',
            'user': self.context.user,
            'project': self.context.project,
            'domain': self.context.domain,
            'name': 'test_policy',
        }
        return db_api.policy_create(self.context, values)

    def test_cluster_policy_load(self):
        ex = self.assertRaises(exception.PolicyNotAttached,
                               cpm.ClusterPolicy.load,
                               self.context, 'some-cluster', 'any-policy')
        self.assertEqual('The policy (any-policy) is not attached to the '
                         'specified cluster (some-cluster).',
                         six.text_type(ex))

        cluster = self._create_cluster('CLUSTER_ID')
        policy = self._create_policy('POLICY_ID')

        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy(cluster.id, policy.id, **values)
        cp_id = cp.store(self.context)

        result = cpm.ClusterPolicy.load(self.context, 'CLUSTER_ID',
                                        'POLICY_ID')

        self.assertEqual(cp_id, result.id)
        self.assertEqual(cluster.id, result.cluster_id)
        self.assertEqual(policy.id, result.policy_id)
        self.assertTrue(True, result.enabled)
        self.assertEqual(12, result.priority)
        self.assertEqual({}, result.data)
        self.assertIsNone(result.last_op)
        self.assertEqual('test_cluster', result.cluster_name)
        self.assertEqual('policy-type', result.policy_type)
        self.assertEqual('test_policy', result.policy_name)

    def test_cluster_policy_load_all(self):
        result = cpm.ClusterPolicy.load_all(self.context, 'non-existent')
        self.assertEqual([], result)

        cluster = self._create_cluster('CLUSTER')
        policy1 = self._create_policy('P1')
        policy2 = self._create_policy('P2')

        b1 = cpm.ClusterPolicy(cluster.id, policy1.id, enabled=True)
        b1.store(self.context)
        b2 = cpm.ClusterPolicy(cluster.id, policy2.id, enabled=False)
        b2.store(self.context)

        # NOTE: we don't test all other parameters because the db api tests
        #       already covered that
        result = cpm.ClusterPolicy.load_all(self.context, 'CLUSTER')
        self.assertEqual(2, len(result))

    def test_cluster_policy_to_dict(self):
        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy('fake-cluster', 'fake-policy', **values)
        self.assertIsNone(cp.id)
        expected = {
            'id': None,
            'cluster_id': 'fake-cluster',
            'policy_id': 'fake-policy',
            'enabled': True,
            'data': {},
            'last_op': None,
            'cluster_name': '',
            'policy_type': '',
            'policy_name': '',
        }

        self.assertEqual(expected, cp.to_dict())

    def test_cooldown_inprogress(self):
        values = {
            'enabled': True,
            'last_op': timeutils.utcnow(),
        }
        cp = cpm.ClusterPolicy('fake-cluster', 'fake-policy', **values)
        self.assertTrue(cp.cooldown_inprogress(60))
        cp.last_op -= timedelta(hours=1)
        self.assertFalse(cp.cooldown_inprogress(60))
