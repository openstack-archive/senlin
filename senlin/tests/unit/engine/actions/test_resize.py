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
class ClusterResizeTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterResizeTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test__update_cluster_size(self, mock_load):
        cluster = mock.Mock(id='CID', desired_capacity=10, nodes=[])
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_RESIZE', self.ctx,
                                  inputs={'min_size': 1, 'max_size': 20})

        action._update_cluster_size(15)

        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster resize started.',
            desired_capacity=15, min_size=1, max_size=20)

    def test__update_cluster_size_minimum(self, mock_load):
        cluster = mock.Mock(id='CID', desired_capacity=10, nodes=[])
        mock_load.return_value = cluster
        action = ca.ClusterAction(cluster.id, 'CLUSTER_RESIZE', self.ctx,
                                  inputs={})

        action._update_cluster_size(15)

        cluster.set_status.assert_called_once_with(
            action.context, consts.CS_RESIZING, 'Cluster resize started.',
            desired_capacity=15)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test_do_resize_shrink(self, mock_delete, mock_sleep, mock_select,
                              mock_size, mock_count, mock_load):
        cluster = mock.Mock(id='CID', nodes=[], RESIZING='RESIZING')
        for n in range(10):
            node = mock.Mock(id='NODE-ID-%s' % (n + 1))
            cluster.nodes.append(node)
        mock_load.return_value = cluster
        mock_count.return_value = 10
        action = ca.ClusterAction(
            cluster.id, 'CLUSTER_RESIZE', self.ctx,
            data={
                'deletion': {
                    'count': 2,
                    'grace_period': 2,
                    'destroy_after_deletion': True
                }
            }
        )
        mock_delete.return_value = (action.RES_OK, 'All dependents completed.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster resize succeeded.', res_msg)

        mock_select.assert_called_once_with(cluster.nodes, 2)
        mock_size.assert_called_once_with(8)
        mock_sleep.assert_called_once_with(2)
        mock_delete.assert_called_once_with(mock_select.return_value)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(scaleutils, 'nodes_by_random')
    @mock.patch.object(ca.ClusterAction, '_sleep')
    @mock.patch.object(scaleutils, 'parse_resize_params')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test_do_resize_shrink_with_parsing(self, mock_delete, mock_parse,
                                           mock_sleep, mock_select, mock_size,
                                           mock_count, mock_load):

        def fake_parse(*args, **kwargs):
            # side effect
            action.data = {'deletion': {'count': 1}}
            return action.RES_OK, ''

        cluster = mock.Mock(id='CID', nodes=[], RESIZING='RESIZING')
        for n in range(10):
            node = mock.Mock(id='NODE-ID-%s' % (n + 1))
            cluster.nodes.append(node)
        mock_count.return_value = 10
        mock_load.return_value = cluster
        mock_parse.side_effect = fake_parse
        action = ca.ClusterAction(cluster.id, 'CLUSTER_RESIZE', self.ctx,
                                  inputs={'blah': 'blah'}, data={})
        mock_delete.return_value = (action.RES_OK, 'All dependents completed.')

        # deletion policy is attached to the action
        res_code, res_msg = action.do_resize()

        self.assertEqual({'deletion': {'count': 1}}, action.data)
        mock_parse.assert_called_once_with(action, cluster, 10)
        mock_select.assert_called_once_with(cluster.nodes, 1)
        mock_size.assert_called_once_with(9)
        mock_sleep.assert_called_once_with(0)
        mock_delete.assert_called_once_with(mock_select.return_value)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(ca.ClusterAction, '_delete_nodes')
    def test_do_resize_shrink_failed_delete(self, mock_delete, mock_size,
                                            mock_count, mock_load):
        cluster = mock.Mock(id='CLID', nodes=[], RESIZING='RESIZING')
        mock_count.return_value = 3
        mock_load.return_value = cluster
        action = ca.ClusterAction(
            cluster.id, 'CLUSTER_RESIZE', self.ctx,
            data={
                'deletion': {
                    'count': 2,
                    'grace_period': 2,
                    'candidates': ['NODE1', 'NODE2']
                }
            }
        )
        mock_delete.return_value = (action.RES_ERROR, 'Bad things happened.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Bad things happened.', res_msg)

        mock_size.assert_called_once_with(1)
        mock_delete.assert_called_once_with(['NODE1', 'NODE2'])
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test_do_resize_grow(self, mock_create, mock_size, mock_count,
                            mock_load):
        cluster = mock.Mock(id='ID', nodes=[], RESIZING='RESIZING')
        mock_load.return_value = cluster
        mock_count.return_value = 10
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={'creation': {'count': 2}})

        mock_create.return_value = (action.RES_OK, 'All dependents completed.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster resize succeeded.', res_msg)

        mock_size.assert_called_once_with(12)
        mock_create.assert_called_once_with(2)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(scaleutils, 'parse_resize_params')
    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test_do_resize_grow_with_parsing(self, mock_create, mock_parse,
                                         mock_size, mock_count, mock_load):
        def fake_parse(*args, **kwargs):
            action.data = {'creation': {'count': 3}}
            return action.RES_OK, ''

        cluster = mock.Mock(id='ID', nodes=[], RESIZING='RESIZING')
        mock_load.return_value = cluster
        mock_count.return_value = 10
        mock_parse.side_effect = fake_parse
        action = ca.ClusterAction(cluster.id, 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'blah': 'blah'})
        mock_create.return_value = (action.RES_OK, 'All dependents completed.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_OK, res_code)
        self.assertEqual('Cluster resize succeeded.', res_msg)

        mock_parse.assert_called_once_with(action, cluster, 10)
        mock_size.assert_called_once_with(13)
        mock_create.assert_called_once_with(3)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(ca.ClusterAction, '_update_cluster_size')
    @mock.patch.object(ca.ClusterAction, '_create_nodes')
    def test_do_resize_grow_failed_create(self, mock_create, mock_size,
                                          mock_count, mock_load):
        cluster = mock.Mock(id='CLID', nodes=[], RESIZING='RESIZING')
        mock_load.return_value = cluster
        mock_count.return_value = 3
        action = ca.ClusterAction(
            cluster.id, 'CLUSTER_RESIZE', self.ctx,
            data={'creation': {'count': 2}})
        mock_create.return_value = (action.RES_ERROR, 'Bad things happened.')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Bad things happened.', res_msg)

        mock_size.assert_called_once_with(5)
        mock_create.assert_called_once_with(2)
        cluster.eval_status.assert_called_once_with(
            action.context, consts.CLUSTER_RESIZE)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(scaleutils, 'parse_resize_params')
    def test_do_resize_failed_parsing(self, mock_parse, mock_count, mock_load):
        cluster = mock.Mock(RESIZING='RESIZING', nodes=[])
        mock_load.return_value = cluster
        mock_count.return_value = 8
        action = ca.ClusterAction('ID', 'CLUSTER_ACTION', self.ctx,
                                  data={}, inputs={'blah': 'blah'})
        mock_parse.return_value = (action.RES_ERROR, 'Failed parsing')

        # do it
        res_code, res_msg = action.do_resize()

        # assertions
        self.assertEqual(action.RES_ERROR, res_code)
        self.assertEqual('Failed parsing', res_msg)
        mock_parse.assert_called_once_with(action, cluster, 8)
        self.assertEqual(0, cluster.set_status.call_count)
        self.assertEqual(0, cluster.eval_status.call_count)
