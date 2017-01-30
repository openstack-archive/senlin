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
        self.assertEqual("The policy 'any-policy' is not attached to the "
                         "specified cluster 'some-cluster'.",
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
