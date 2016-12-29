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

from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterUpdatePolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterUpdatePolicyTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_do_update_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.update_policy.return_value = True, 'Success.'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {
            'policy_id': 'FAKE_POLICY',
            'foo': 'bar',
        }

        # do it
        res_code, res_msg = action.do_update_policy()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Success.', res_msg)
        cluster.update_policy.assert_called_once_with(
            action.context, 'FAKE_POLICY', foo='bar')

    def test_do_update_policy_failed_update(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.update_policy.return_value = False, 'Something is wrong.'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {
            'policy_id': 'FAKE_POLICY',
            'foo': 'bar',
        }

        # do it
        res_code, res_msg = action.do_update_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Something is wrong.', res_msg)
        cluster.update_policy.assert_called_once_with(
            action.context, 'FAKE_POLICY', foo='bar')

    def test_do_update_policy_missing_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'enabled': True}

        # do it
        res_code, res_msg = action.do_update_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy not specified.', res_msg)
