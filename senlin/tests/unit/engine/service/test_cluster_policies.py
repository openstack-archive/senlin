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
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import cluster_policy as cpo
from senlin.objects import policy as po
from senlin.objects.requests import cluster_policies as orcp
from senlin.objects.requests import clusters as orco
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterPolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterPolicyTest, self).setUp()
        self.ctx = utils.dummy_context(project='cluster_policy_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    def test_list2(self, mock_get, mock_find):
        x_obj = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_obj
        b1 = mock.Mock()
        b1.to_dict.return_value = {'k': 'v1'}
        b2 = mock.Mock()
        b2.to_dict.return_value = {'k': 'v2'}
        mock_get.return_value = [b1, b2]

        req = orcp.ClusterPolicyListRequest(identity='CLUSTER')
        result = self.eng.cluster_policy_list(
            self.ctx, req.obj_to_primitive())
        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                         filters={}, sort=None)

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    def test_list2_with_param(self, mock_get, mock_find):
        x_obj = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_obj
        mock_get.return_value = []

        params = {
            'identity': 'CLUSTER',
            'policy_name': 'fake_name',
            'policy_type': 'fake_type',
            'enabled': True,
            'sort': 'enabled'
        }

        req = orcp.ClusterPolicyListRequest(**params)

        result = self.eng.cluster_policy_list(
            self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')

    def test_list2_bad_param(self):
        params = {
            'identity': 'CLUSTER',
            'sort': 'bad',
        }

        ex = self.assertRaises(ValueError,
                               orcp.ClusterPolicyListRequest,
                               **params)
        self.assertEqual("Unsupported sort key 'bad' for 'sort'.",
                         six.text_type(ex))

    @mock.patch.object(co.Cluster, 'find')
    def test_list2_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orcp.ClusterPolicyListRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_list,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    @mock.patch.object(cpo.ClusterPolicy, 'get')
    def test_get2(self, mock_get, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock(id='C1')
        mock_policy.return_value = mock.Mock(id='P1')
        x_binding = mock.Mock()
        x_binding.to_dict.return_value = {'foo': 'bar'}
        mock_get.return_value = x_binding

        req = orcp.ClusterPolicyGetRequest(identity='C1',
                                           policy_id='P1')
        result = self.eng.cluster_policy_get(self.ctx,
                                             req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_get.assert_called_once_with(self.ctx, 'C1', 'P1')

    @mock.patch.object(co.Cluster, 'find')
    def test_get2_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='cid')
        req = orcp.ClusterPolicyGetRequest(identity='cid',
                                           policy_id='pid')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_get,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'cid' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'cid')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    def test_get2_policy_not_found(self, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock(id='cid')
        mock_policy.side_effect = exc.ResourceNotFound(type='policy',
                                                       id='pid')
        req = orcp.ClusterPolicyGetRequest(identity='cid',
                                           policy_id='pid')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_get,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The policy 'pid' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'cid')
        mock_policy.assert_called_once_with(self.ctx, 'pid')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    @mock.patch.object(cpo.ClusterPolicy, 'get')
    def test_get2_binding_not_found(self, mock_get, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock(id='cid')
        mock_policy.return_value = mock.Mock(id='pid')
        err = exc.PolicyBindingNotFound(policy='pid', identity='cid')
        mock_get.side_effect = err

        req = orcp.ClusterPolicyGetRequest(identity='cid',
                                           policy_id='pid')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_get,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.PolicyBindingNotFound, ex.exc_info[0])
        self.assertEqual("The policy 'pid' is not found attached to "
                         "the specified cluster 'cid'.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_attach2(self, notify, mock_policy, mock_cluster, mock_action):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterAttachPolicyRequest(identity='C1', policy_id='P1',
                                              enabled=True)

        res = self.eng.cluster_policy_attach(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')

        mock_action.assert_called_once_with(
            self.ctx, '12345678abcd', consts.CLUSTER_ATTACH_POLICY,
            name='attach_policy_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'policy_id': '87654321abcd', 'enabled': True},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_attach2_cluster_not_found(self, mock_cluster):
        mock_cluster.side_effect = exc.ResourceNotFound(type='cluster',
                                                        id='BOGUS')
        req = orco.ClusterAttachPolicyRequest(identity='BOGUS',
                                              policy_id='POLICY_ID')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_attach,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'BOGUS' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'BOGUS')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    def test_attach2_policy_not_found(self, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.side_effect = exc.ResourceNotFound(type='policy',
                                                       id='BOGUS')
        req = orco.ClusterAttachPolicyRequest(identity='CLUSTER',
                                              policy_id='BOGUS')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_attach,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified policy 'BOGUS' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_policy.assert_called_once_with(self.ctx, 'BOGUS')

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_detach2(self, notify, mock_policy, mock_cluster, mock_cp,
                     mock_action):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')
        mock_action.return_value = 'ACTION_ID'
        mock_cp.return_value = mock.Mock()
        req = orco.ClusterDetachPolicyRequest(identity='C1', policy_id='P1')

        res = self.eng.cluster_policy_detach(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, '12345678abcd',
                                        '87654321abcd')
        mock_action.assert_called_once_with(
            self.ctx, '12345678abcd', consts.CLUSTER_DETACH_POLICY,
            name='detach_policy_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'policy_id': '87654321abcd'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_detach2_cluster_not_found(self, mock_cluster):
        mock_cluster.side_effect = exc.ResourceNotFound(type='cluster',
                                                        id='Bogus')
        req = orco.ClusterDetachPolicyRequest(identity='Bogus',
                                              policy_id='POLICY_ID')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_detach,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    def test_detach2_policy_not_found(self, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock()
        mock_policy.side_effect = exc.ResourceNotFound(type='policy',
                                                       id='Bogus')
        req = orco.ClusterDetachPolicyRequest(identity='CLUSTER',
                                              policy_id='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_detach,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified policy 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_policy.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    def test_detach2_binding_not_found(self, mock_policy, mock_cluster,
                                       mock_cp):
        mock_cluster.return_value = mock.Mock(id='X_CLUSTER')
        mock_policy.return_value = mock.Mock(id='X_POLICY')
        mock_cp.return_value = None
        req = orco.ClusterDetachPolicyRequest(identity='C1', policy_id='P1')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_detach,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The policy 'P1' is not attached to "
                         "the specified cluster 'C1'.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, 'X_CLUSTER', 'X_POLICY')

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_update2(self, notify, mock_policy, mock_cluster, mock_cp,
                     mock_action):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')
        mock_action.return_value = 'ACTION_ID'
        mock_cp.return_value = mock.Mock()
        req = orco.ClusterUpdatePolicyRequest(identity='C1', policy_id='P1',
                                              enabled=False)

        res = self.eng.cluster_policy_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, '12345678abcd',
                                        '87654321abcd')
        mock_action.assert_called_once_with(
            self.ctx, '12345678abcd', consts.CLUSTER_UPDATE_POLICY,
            name='update_policy_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'policy_id': '87654321abcd', 'enabled': False},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_update2_cluster_not_found(self, mock_cluster):
        mock_cluster.side_effect = exc.ResourceNotFound(type='cluster',
                                                        id='Bogus')
        req = orco.ClusterUpdatePolicyRequest(identity='Bogus', policy_id='P1',
                                              enabled=True)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    def test_update2_policy_not_found(self, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock()
        mock_policy.side_effect = exc.ResourceNotFound(type='policy',
                                                       id='Bogus')
        req = orco.ClusterUpdatePolicyRequest(identity='C1', policy_id='Bogus',
                                              enabled=True)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified policy 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Policy, 'find')
    def test_update2_binding_not_found(self, mock_policy, mock_cluster,
                                       mock_cp):
        mock_cluster.return_value = mock.Mock(id='CLUSTER_ID1')
        mock_policy.return_value = mock.Mock(id='POLICY_ID1')
        mock_cp.return_value = None
        req = orco.ClusterUpdatePolicyRequest(identity='C1', policy_id='P1',
                                              enabled=True)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The policy 'P1' is not attached to the "
                         "specified cluster 'C1'.",
                         six.text_type(ex.exc_info[1]))

        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, 'CLUSTER_ID1', 'POLICY_ID1')
