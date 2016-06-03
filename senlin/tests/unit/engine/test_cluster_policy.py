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
from senlin.common import utils as common_utils
from senlin.engine import cluster_policy as cpm
from senlin.objects import cluster_policy as cpo
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

CLUSTER_ID = '8d674833-6c0c-4e1c-928b-4bb3a4ebd4ae'
POLICY_ID = 'fa573870-fe44-42aa-84a9-08462f0e6999'
PROFILE_ID = '12abef70-ab31-484a-92aa-02388f0e6ccc'


class TestClusterPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestClusterPolicy, self).setUp()
        self.context = utils.dummy_context()

    def test_cluster_policy_init(self):
        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy(CLUSTER_ID, POLICY_ID, **values)

        self.assertIsNone(cp.id)
        self.assertEqual(CLUSTER_ID, cp.cluster_id)
        self.assertEqual(POLICY_ID, cp.policy_id)
        self.assertEqual(12, cp.priority)
        self.assertTrue(True, cp.enabled)
        self.assertEqual({}, cp.data)
        self.assertIsNone(cp.last_op)
        self.assertEqual('', cp.cluster_name)
        self.assertEqual('', cp.policy_type)
        self.assertEqual('', cp.policy_name)

    def test_cluster_policy_store(self):
        cluster = utils.create_cluster(self.context, CLUSTER_ID, PROFILE_ID)
        policy = utils.create_policy(self.context, POLICY_ID)
        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy(cluster.id, policy.id, **values)
        self.assertIsNone(cp.id)
        cp_id = cp.store(self.context)
        self.assertIsNotNone(cp_id)

        result = cpo.ClusterPolicy.get(self.context, CLUSTER_ID, POLICY_ID)

        self.assertIsNotNone(result)
        self.assertEqual(12, result.priority)
        self.assertTrue(result.enabled)
        self.assertEqual({}, result.data)
        self.assertIsNone(result.last_op)

        # do an update
        cp.enabled = False
        cp.priority = 60
        cp.data = {'foo': 'bar'}
        timestamp = timeutils.utcnow(True)
        cp.last_op = timestamp

        new_id = cp.store(self.context)
        self.assertEqual(cp_id, new_id)

        result = cpo.ClusterPolicy.get(self.context, CLUSTER_ID, POLICY_ID)

        self.assertIsNotNone(result)
        self.assertFalse(result.enabled)
        self.assertEqual(60, result.priority)
        self.assertEqual({'foo': 'bar'}, result.data)
        self.assertEqual(common_utils.isotime(timestamp),
                         common_utils.isotime(result.last_op))

    def test_cluster_policy_load(self):
        ex = self.assertRaises(exception.PolicyNotAttached,
                               cpm.ClusterPolicy.load,
                               self.context, 'some-cluster', 'any-policy')
        self.assertEqual('The policy (any-policy) is not attached to the '
                         'specified cluster (some-cluster).',
                         six.text_type(ex))

        cluster = utils.create_cluster(self.context, CLUSTER_ID, PROFILE_ID)
        policy = utils.create_policy(self.context, POLICY_ID)

        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy(cluster.id, policy.id, **values)
        cp_id = cp.store(self.context)

        result = cpm.ClusterPolicy.load(self.context, CLUSTER_ID, POLICY_ID)

        self.assertEqual(cp_id, result.id)
        self.assertEqual(cluster.id, result.cluster_id)
        self.assertEqual(policy.id, result.policy_id)
        self.assertTrue(True, result.enabled)
        self.assertEqual(12, result.priority)
        self.assertEqual({}, result.data)
        self.assertIsNone(result.last_op)
        self.assertEqual('test-cluster', result.cluster_name)
        self.assertEqual('senlin.policy.dummy-1.0', result.policy_type)
        self.assertEqual('test_policy', result.policy_name)

    def test_cluster_policy_load_all(self):
        result = cpm.ClusterPolicy.load_all(self.context, 'non-existent')
        self.assertEqual([], result)

        cluster = utils.create_cluster(self.context, CLUSTER_ID, PROFILE_ID)
        policy1 = utils.create_policy(self.context,
                                      'd752f3e4-7be5-41a6-8a36-85bbbdbd7d4a')
        policy2 = utils.create_policy(self.context,
                                      '0a2e1240-d34f-4c96-8034-37388cdcdb7b')

        b1 = cpm.ClusterPolicy(cluster.id, policy1.id, enabled=True,
                               priority=10)
        b1.store(self.context)
        b2 = cpm.ClusterPolicy(cluster.id, policy2.id, enabled=False,
                               priority=20)
        b2.store(self.context)

        # NOTE: we don't test all other parameters because the db api tests
        #       already covered that
        result = cpm.ClusterPolicy.load_all(self.context, CLUSTER_ID)
        self.assertEqual(2, len(result))

    def test_cluster_policy_to_dict(self):
        values = {
            'priority': 12,
            'enabled': True,
        }
        cp = cpm.ClusterPolicy(CLUSTER_ID, POLICY_ID, **values)
        self.assertIsNone(cp.id)
        expected = {
            'id': None,
            'cluster_id': CLUSTER_ID,
            'policy_id': POLICY_ID,
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
            'last_op': timeutils.utcnow(True),
        }
        cp = cpm.ClusterPolicy(CLUSTER_ID, POLICY_ID, **values)
        self.assertTrue(cp.cooldown_inprogress(60))
        cp.last_op -= timedelta(hours=1)
        self.assertFalse(cp.cooldown_inprogress(60))
