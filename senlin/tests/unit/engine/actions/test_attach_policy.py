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
class ClusterAttachPolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterAttachPolicyTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_do_attach_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.policies = []
        cluster.attach_policy.return_value = True, 'OK'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {
            'policy_id': 'FAKE_POLICY',
            'FOO': 'BAR'
        }

        # do it
        res_code, res_msg = action.do_attach_policy()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('OK', res_msg)
        cluster.attach_policy.assert_called_once_with(
            action.context, 'FAKE_POLICY', {'FOO': 'BAR'})
        cluster.store.assert_called_once_with(action.context)

    def test_do_attach_policy_missing_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CLID'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {}

        # do it
        res_code, res_msg = action.do_attach_policy()
        # assertion
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy not specified.', res_msg)

    def test_do_detach_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.detach_policy.return_value = True, 'Success'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'policy_id': 'FAKE_POLICY'}

        # do it
        res_code, res_msg = action.do_detach_policy()

        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Success', res_msg)
        cluster.detach_policy.assert_called_once_with(action.context,
                                                      'FAKE_POLICY')
        cluster.store.assert_called_once_with(action.context)

    def test_do_detach_policy_missing_policy(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'CID'
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {}

        # do it
        res_code, res_msg = action.do_detach_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Policy not specified.', res_msg)

    def test_do_detach_policy_failed(self, mock_load):
        cluster = mock.Mock()
        cluster.id = 'FAKE_CLUSTER'
        cluster.detach_policy.return_value = False, 'Failure.'
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.inputs = {'policy_id': 'FAKE_POLICY'}

        # do it
        res_code, res_msg = action.do_detach_policy()

        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failure.', res_msg)
        cluster.detach_policy.assert_called_once_with(action.context,
                                                      'FAKE_POLICY')
