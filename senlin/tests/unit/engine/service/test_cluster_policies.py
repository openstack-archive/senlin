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
from senlin.engine import cluster_policy as cp_mod
from senlin.engine import dispatcher
from senlin.engine import service
from senlin.objects import cluster_policy as cpo
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterPolicyTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterPolicyTest, self).setUp()
        self.ctx = utils.dummy_context(project='cluster_policy_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    def test_cluster_policy_list(self, mock_load, mock_find):
        x_obj = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_obj
        b1 = mock.Mock()
        b1.to_dict.return_value = {'k': 'v1'}
        b2 = mock.Mock()
        b2.to_dict.return_value = {'k': 'v2'}
        mock_load.return_value = [b1, b2]

        result = self.eng.cluster_policy_list(self.ctx, 'CLUSTER')

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                          filters=None, sort=None)

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_policy_list_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_list,
                               self.ctx, 'Bogus')

        self.assertEqual("The cluster (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    def test_cluster_policy_list_empty(self, mock_load, mock_find):
        x_obj = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_obj
        mock_load.return_value = []

        result = self.eng.cluster_policy_list(self.ctx, 'CLUSTER')

        self.assertEqual([], result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                          filters=None, sort=None)

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    def test_cluster_policy_list_with_params(self, mock_load, mock_find):
        x_obj = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_obj
        mock_load.return_value = []

        result = self.eng.cluster_policy_list(self.ctx, 'CLUSTER',
                                              filters='FOO', sort='enabled')

        self.assertEqual([], result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                          filters='FOO', sort='enabled')

    def test_cluster_policy_list_bad_sort(self):

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_list,
                               self.ctx, 'CLUSTER', sort='crazy')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'crazy' specified for 'sort key'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    @mock.patch.object(cp_mod.ClusterPolicy, 'load')
    def test_cluster_policy_get(self, mock_load, mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_policy.return_value = mock.Mock(id='FAKE_POLICY')
        x_binding = mock.Mock()
        x_binding.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_binding

        result = self.eng.cluster_policy_get(self.ctx, 'C1', 'P1')

        self.assertEqual({'foo': 'bar'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_load.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                          'FAKE_POLICY')

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_policy_get_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_get,
                               self.ctx, 'Bogus', 'POLICY')
        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_get_policy_not_found(self, mock_policy,
                                                 mock_cluster):
        mock_cluster.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_policy.side_effect = exc.PolicyNotFound(policy='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_get,
                               self.ctx, 'CLUSTER', 'Bogus')

        self.assertEqual(exc.PolicyNotFound, ex.exc_info[0])
        self.assertEqual("The policy (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_policy.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    @mock.patch.object(cp_mod.ClusterPolicy, 'load')
    def test_cluster_policy_get_binding_not_found(self, mock_load,
                                                  mock_policy, mock_cluster):
        mock_cluster.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_policy.return_value = mock.Mock(id='FAKE_POLICY')
        err = exc.PolicyNotAttached(policy='POLICY', cluster='CLUSTER')
        mock_load.side_effect = err

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_get,
                               self.ctx, 'CLUSTER', 'POLICY')

        self.assertEqual(exc.PolicyBindingNotFound, ex.exc_info[0])
        self.assertEqual("The policy (POLICY) is not found attached to "
                         "the specified cluster (CLUSTER).",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_policy_attach(self, notify, mock_policy, mock_cluster,
                                   mock_action):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')
        mock_action.return_value = 'ACTION_ID'

        res = self.eng.cluster_policy_attach(self.ctx, 'C1', 'P1')

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')

        mock_action.assert_called_once_with(
            self.ctx, '12345678abcd', consts.CLUSTER_ATTACH_POLICY,
            name='attach_policy_12345678',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'policy_id': '87654321abcd', 'enabled': True},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_policy_attach_cluster_not_found(self, mock_cluster):
        mock_cluster.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_attach,
                               self.ctx, 'Bogus', 'POLICY_ID')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_attach_policy_not_found(self, mock_policy,
                                                    mock_cluster):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.side_effect = exc.PolicyNotFound(policy='BOGUS')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_attach,
                               self.ctx, 'FAKE_CLUSTER', 'BOGUS')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified policy "
                         "(BOGUS) is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_policy.assert_called_once_with(self.ctx, 'BOGUS')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_attach_enabled_not_boolean(self, mock_policy,
                                                       mock_cluster):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_attach,
                               self.ctx, 'C1', 'P1',
                               enabled='No')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'No' specified for 'enabled'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_policy_detach(self, notify, mock_policy, mock_cluster,
                                   mock_cp, mock_action):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')
        mock_action.return_value = 'ACTION_ID'
        mock_cp.return_value = mock.Mock()

        result = self.eng.cluster_policy_detach(self.ctx, 'C1', 'P1')

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, '12345678abcd',
                                        '87654321abcd')
        mock_action.assert_called_once_with(
            self.ctx, '12345678abcd', consts.CLUSTER_DETACH_POLICY,
            name='detach_policy_12345678',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'policy_id': '87654321abcd'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_policy_detach_cluster_not_found(self, mock_cluster):
        mock_cluster.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_detach,
                               self.ctx, 'Bogus', 'POLICY_ID')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_detach_policy_not_found(self, mock_policy,
                                                    mock_cluster):
        mock_cluster.return_value = mock.Mock()
        mock_policy.side_effect = exc.PolicyNotFound(policy='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_detach,
                               self.ctx, 'FAKE_CLUSTER', 'Bogus')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified policy "
                         "(Bogus) is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_policy.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_detach_binding_not_found(self, mock_policy,
                                                     mock_cluster, mock_cp):
        mock_cluster.return_value = mock.Mock(id='X_CLUSTER')
        mock_policy.return_value = mock.Mock(id='X_POLICY')
        mock_cp.return_value = None

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_detach,
                               self.ctx, 'C1', 'P1')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The policy (P1) is "
                         "not attached to the specified cluster (C1).",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, 'X_CLUSTER', 'X_POLICY')

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_policy_update(self, notify, mock_policy, mock_cluster,
                                   mock_cp, mock_action):
        mock_cluster.return_value = mock.Mock(id='12345678abcd')
        mock_policy.return_value = mock.Mock(id='87654321abcd')
        mock_action.return_value = 'ACTION_ID'
        mock_cp.return_value = mock.Mock()

        result = self.eng.cluster_policy_update(self.ctx, 'C1', 'P1',
                                                enabled=False)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, '12345678abcd',
                                        '87654321abcd')
        mock_action.assert_called_once_with(
            self.ctx, '12345678abcd', consts.CLUSTER_UPDATE_POLICY,
            name='update_policy_12345678',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'policy_id': '87654321abcd', 'enabled': False},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_policy_update_cluster_not_found(self, mock_cluster):
        mock_cluster.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, 'Bogus', 'P1', enabled=True)

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_update_policy_not_found(self, mock_policy,
                                                    mock_cluster):
        mock_cluster.return_value = mock.Mock()
        mock_policy.side_effect = exc.PolicyNotFound(policy='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, 'C1', 'Bogus', enabled=True)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified policy "
                         "(Bogus) is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_update_binding_not_found(self, mock_policy,
                                                     mock_cluster, mock_cp):
        mock_cluster.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_policy.return_value = mock.Mock(id='FAKE_POLICY')
        mock_cp.return_value = None

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, 'C1', 'P1', enabled=True)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The policy (P1) is "
                         "not attached to the specified cluster (C1).",
                         six.text_type(ex.exc_info[1]))

        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                        'FAKE_POLICY')

    @mock.patch.object(cpo.ClusterPolicy, 'get')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'policy_find')
    def test_cluster_policy_update_param_invalid(self, mock_policy,
                                                 mock_cluster, mock_cp):

        mock_cluster.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_policy.return_value = mock.Mock(id='FAKE_POLICY')
        mock_cp.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_policy_update,
                               self.ctx, 'C1', 'P1', enabled='No')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'No' specified for 'enabled'",
                         six.text_type(ex.exc_info[1]))

        mock_cluster.assert_called_once_with(self.ctx, 'C1')
        mock_policy.assert_called_once_with(self.ctx, 'P1')
        mock_cp.assert_called_once_with(self.ctx, 'FAKE_CLUSTER',
                                        'FAKE_POLICY')
