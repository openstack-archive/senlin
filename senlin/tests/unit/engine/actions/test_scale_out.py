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
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(cm.Cluster, 'load')
class ClusterScaleOutTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterScaleOutTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_no_pd_no_inputs(self, mock_count, mock_create,
                                          mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={})
        mock_count.return_value = 5
        mock_create.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        mock_count.assert_called_once_with(action.context, 'CID')
        mock_create.assert_called_once_with(1)
        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster scale out started.',
            desired_capacity=6)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_SCALE_OUT)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_with_pd_no_inputs(self, mock_count, mock_create,
                                            mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={'creation': {'count': 3}}, inputs={})
        mock_count.return_value = 7
        mock_create.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # creating 3 nodes
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_create.assert_called_once_with(3)
        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster scale out started.',
            desired_capacity=10)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_SCALE_OUT)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_no_pd_with_inputs(self, mock_count, mock_create,
                                            mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 8
        mock_create.return_value = (action.RES_OK, 'Life is beautiful.')

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster scaling succeeded.', res_msg)

        # creating 2 nodes, given that the cluster is empty now
        mock_count.assert_called_once_with(action.context, 'CID')
        mock_create.assert_called_once_with(2)
        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster scale out started.',
            desired_capacity=10)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_SCALE_OUT)

    def test_do_scale_out_count_negative(self, mock_load):
        cluster = mock.Mock(id='CID')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': -2})

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (-2) for scaling out.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    def test_do_scale_out_count_invalid(self, mock_load):
        cluster = mock.Mock(id='CID')
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 'tt'})

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Invalid count (tt) for scaling out.', res_msg)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_failed_checking(self, mock_count, mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=4)
        mock_load.return_value = cluster

        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 3

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual("The target capacity (5) is greater than the "
                         "cluster's max_size (4).", res_msg)
        mock_count.assert_called_once_with(action.context, 'CID')
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)

    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    @mock.patch.object(no.Node, 'count_by_cluster')
    def test_do_scale_out_failed_create_nodes(self, mock_count, mock_create,
                                              mock_load):
        cluster = mock.Mock(id='CID', min_size=1, max_size=-1)
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'count': 2})
        mock_count.return_value = 4

        # Error cases
        for result in (action.RES_ERROR, action.RES_CANCEL,
                       action.RES_TIMEOUT):
            mock_create.return_value = result, 'Too hot to work!'

            # do it
            res_code, res_msg = action.do_scale_out()

            # assertions
            self.assertEqual(result, res_code)
            self.assertEqual('Too hot to work!', res_msg)

            cluster.set_status.assert_called_once_with(
                action.context, consts.CS_RESIZING,
                'Cluster scale out started.',
                desired_capacity=6)
            cluster.set_status.reset_mock()
            cluster.eval_status.assert_called_once_with(
                action.context, consts.CLUSTER_SCALE_OUT)
            cluster.eval_status.reset_mock()
            mock_create.assert_called_once_with(2)
            mock_create.reset_mock()

        # Timeout case
        mock_create.return_value = action.RES_RETRY, 'Not good time!'

        # do it
        res_code, res_msg = action.do_scale_out()

        # assertions
        self.assertEqual(action.RES_RETRY, res_code)
        self.assertEqual('Not good time!', res_msg)
        self.assertEqual(1, cluster.set_status.call_count)
        self.assertEqual(1, cluster.eval_status.call_count)
        mock_create.assert_called_once_with(2)
