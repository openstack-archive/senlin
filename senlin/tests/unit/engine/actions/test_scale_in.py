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

from senlin.common import consts
from senlin.common import scaleutils
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterScaleInTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterScaleInTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_no_pd_no_count(self, mock_count, mock_delete,
                                        mock_select, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={})
        mock_count.return_value = 10
        mock_delete.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # deleting 1 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_delete.assert_called_once_with(mock.ANY)
        mock_select.assert_called_once_with(cluster.nodes, 1)
        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster scale in started.',
            desired_capacity=9)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_SCALE_IN)

    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_with_pd_no_input(self, mock_count, mock_delete,
                                          mock_sleep, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx)
        action.data = {
            'deletion': {
                'count': 2,
                'grace_period': 2,
                'candidates': ['NODE_ID_3', 'NODE_ID_4'],
            }
        }
        action.inputs = {}
        mock_count.return_value = 5
        mock_delete.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # deleting 2 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_delete.assert_called_once_with(mock.ANY)
        self.assertEqual(2, len(mock_delete.call_args[0][0]))
        self.assertIn('NODE_ID_3', mock_delete.call_args[0][0])
        self.assertIn('NODE_ID_4', mock_delete.call_args[0][0])
        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster scale in started.',
            desired_capacity=3)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_SCALE_IN)
        mock_sleep.assert_called_once_with(2)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_no_pd_with_input(self, mock_count, mock_delete,
                                          mock_select, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 3})
        mock_count.return_value = 11
        mock_delete.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # deleting 3 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_delete.assert_called_once_with(mock.ANY)
        mock_select.assert_called_once_with(cluster.nodes, 3)
        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster scale in started.',
            desired_capacity=8)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_SCALE_IN)

    def test_do_scale_in_negative_count(self, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': -3})

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (-3) for scaling in.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    def test_do_scale_in_invalid_count(self, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 'tt'})

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (tt) for scaling in.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_failed_check(self, mock_count, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 3})
        mock_count.return_value = 3

        # do it
        res_code, res_msg = action.do_scale_in()

        # assertions
        mock_count.assert_called_once_with(action.context, 'CID')
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("The target capacity (0) is less than the cluster's "
                         "min_size (1).", res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_in_failed_delete_nodes(self, mock_count, mock_delete,
                                             mock_select, mock_load):

        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 5

        # Error cases
        for result in (action.RES_ERROR, action.RES_CANCEL,
                       action.RES_TIMEOUT, action.RES_RETRY):
            mock_delete.return_value = result, 'Too cold to work!'
            # do it
            res_code, res_msg = action.do_scale_in()
            # assertions
            self.assertEqual(result, res_code)
            self.assertEqual('Too cold to work!', res_msg)
            cluster.set_status.assert_called_once_with(
                action.context, consts.CS_RESIZING,
                'Cluster scale in started.',
                desired_capacity=3)
            cluster.eval_status.assert_called_once_with(
                action.context, consts.CLUSTER_SCALE_IN)
            cluster.set_status.reset_mock()
            cluster.eval_status.reset_mock()
            mock_delete.assert_called_once_with(mock.ANY)
            mock_delete.reset_mock()
