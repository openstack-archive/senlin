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
from oslo_messaging.rpc import dispatcher as rpc
import six

from senlin.common import consts
from senlin.common import exception as exc
from senlin.engine.actions import base as am
from senlin.engine import cluster as cm
from senlin.engine import dispatcher
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import node as no
from senlin.objects.requests import clusters as orco
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterOpTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterOpTest, self).setUp()

        self.ctx = utils.dummy_context(project='cluster_op_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(no.Node, 'ids_by_cluster')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op(self, mock_find, mock_cluster, mock_nodes, mock_action,
                        mock_start):
        x_db_cluster = mock.Mock()
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_cluster = mock.Mock(id='12345678AB')
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        params = {'style': 'tango'}
        filters = {'role': 'slave'}
        mock_nodes.return_value = ['NODE1', 'NODE2']
        req = orco.ClusterOperationRequest(identity='FAKE_CLUSTER',
                                           operation='dance',
                                           params=params,
                                           filters=filters)

        result = self.eng.cluster_op(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)
        x_schema.validate.assert_called_once_with({'style': 'tango'})
        mock_nodes.assert_called_once_with(self.ctx, '12345678AB',
                                           filters={'role': 'slave'})
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.CLUSTER_OPERATION,
            name='cluster_dance_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                'operation': 'dance',
                'params': {'style': 'tango'},
                'nodes': ['NODE1', 'NODE2']
            }
        )
        mock_start.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(
            type='cluster', id='Bogus')
        req = orco.ClusterOperationRequest(identity='Bogus', operation='dance')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_unsupported_operation(self, mock_find, mock_cluster):
        x_db_cluster = mock.Mock(id='12345678AB')
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema}, type='cow')
        x_cluster = mock.Mock()
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        req = orco.ClusterOperationRequest(identity='node1', operation='swim')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The requested operation 'swim' is not supported "
                         "by the profile type 'cow'.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'node1')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_bad_parameters(self, mock_find, mock_cluster):
        x_db_cluster = mock.Mock(id='12345678AB')
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_schema.validate.side_effect = exc.ESchema(message='Boom')
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_cluster = mock.Mock()
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        req = orco.ClusterOperationRequest(identity='node1', operation='dance',
                                           params={'style': 'tango'})

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Boom.", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'node1')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)
        x_schema.validate.assert_called_once_with({'style': 'tango'})

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(no.Node, 'ids_by_cluster')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_no_parameters(self, mock_find, mock_cluster,
                                      mock_nodes, mock_action, mock_start):
        x_db_cluster = mock.Mock()
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_cluster = mock.Mock(id='12345678AB')
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        filters = {'role': 'slave'}
        mock_nodes.return_value = ['NODE1', 'NODE2']
        req = orco.ClusterOperationRequest(identity='FAKE_CLUSTER',
                                           operation='dance',
                                           filters=filters)

        result = self.eng.cluster_op(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)
        self.assertEqual(0, x_schema.validate.call_count)
        mock_nodes.assert_called_once_with(self.ctx, '12345678AB',
                                           filters={'role': 'slave'})
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.CLUSTER_OPERATION,
            name='cluster_dance_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                'operation': 'dance',
                'params': {},
                'nodes': ['NODE1', 'NODE2']
            }
        )
        mock_start.assert_called_once_with()

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(no.Node, 'ids_by_cluster')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_no_filters(self, mock_find, mock_cluster,
                                   mock_nodes, mock_action, mock_start):
        x_db_cluster = mock.Mock()
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_cluster = mock.Mock(id='12345678AB')
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        mock_nodes.return_value = ['NODE1', 'NODE2']
        req = orco.ClusterOperationRequest(identity='FAKE_CLUSTER',
                                           operation='dance')

        result = self.eng.cluster_op(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)
        self.assertEqual(0, x_schema.validate.call_count)
        mock_nodes.assert_called_once_with(self.ctx, '12345678AB')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.CLUSTER_OPERATION,
            name='cluster_dance_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                'operation': 'dance',
                'params': {},
                'nodes': ['NODE1', 'NODE2']
            }
        )
        mock_start.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(no.Node, 'ids_by_cluster')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_bad_filters(self, mock_find, mock_cluster,
                                    mock_nodes, mock_action):
        x_db_cluster = mock.Mock()
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_cluster = mock.Mock(id='12345678AB')
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        mock_nodes.return_value = ['NODE1', 'NODE2']
        filters = {'shape': 'round'}
        req = orco.ClusterOperationRequest(identity='FAKE_CLUSTER',
                                           operation='dance',
                                           filters=filters)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Filter key 'shape' is unsupported.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)
        self.assertEqual(0, x_schema.validate.call_count)
        self.assertEqual(0, mock_nodes.call_count)
        self.assertEqual(0, mock_action.call_count)

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(no.Node, 'ids_by_cluster')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_op_no_nodes_found(self, mock_find, mock_cluster,
                                       mock_nodes, mock_action):
        x_db_cluster = mock.Mock()
        mock_find.return_value = x_db_cluster
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_cluster = mock.Mock(id='12345678AB')
        x_cluster.rt = {'profile': x_profile}
        mock_cluster.return_value = x_cluster
        mock_nodes.return_value = []
        mock_action.return_value = 'ACTION_ID'
        filters = {'role': 'slave'}
        req = orco.ClusterOperationRequest(identity='FAKE_CLUSTER',
                                           operation='dance', filters=filters)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("No node (matching the filter) could be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_cluster.assert_called_once_with(self.ctx, dbcluster=x_db_cluster)
        mock_nodes.assert_called_once_with(self.ctx, '12345678AB',
                                           filters={'role': 'slave'})
        self.assertEqual(0, mock_action.call_count)
