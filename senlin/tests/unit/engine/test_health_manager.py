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

'''
Health Manager class.

Health Manager is responsible for monitoring the health of the clusters and
take corresponding actions to recover the clusters based on the pre-defined
health policies.
'''
import mock

from senlin.common import consts
from senlin.common import messaging as rpc_messaging
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import health_manager
from senlin.rpc import client as rpc_client
from senlin.tests.unit.common import base


class TestHealthManager(base.SenlinTestCase):

    def setUp(self):
        super(TestHealthManager, self).setUp()

        mock_eng = mock.Mock()
        mock_eng.engine_id = 'ENGINE_ID'
        topic = consts.ENGINE_HEALTH_MGR_TOPIC
        version = consts.RPC_API_VERSION
        self.hm = health_manager.HealthManager(mock_eng, topic, version)

    def test_init(self):
        self.assertEqual('ENGINE_ID', self.hm.engine_id)
        self.assertIsNotNone(self.hm.TG)
        self.assertIsNotNone(self.hm.rpc_client)
        self.assertEqual(consts.ENGINE_HEALTH_MGR_TOPIC, self.hm.topic)
        self.assertEqual(consts.RPC_API_VERSION, self.hm.version)
        self.assertEqual(60, self.hm.periodic_interval_max)
        self.assertEqual(0, len(self.hm.rt['registries']))

    @mock.patch.object(db_api, 'registry_claim')
    def test__load_runtime_registry(self, mock_reg_claim):
        mock_reg_claim.return_value = [
            mock.Mock(engine_id='ENGINE_ID'),
            mock.Mock(engine_id='ENGINE_ID')
        ]

        self.hm._load_runtime_registry()
        self.assertEqual(2, len(self.hm.registries))

    @mock.patch.object(rpc_client.EngineClient, 'cluster_check')
    def test_periodic_check(self, mock_check):
        self.hm._periodic_check(cluster_id='CLUSTER_ID')
        mock_check.assert_called_once_with(self.hm.ctx, 'CLUSTER_ID')

    @mock.patch.object(db_api, 'registry_create')
    def test_register_cluster(self, mock_reg_create):
        ctx = mock.Mock()
        matched_type = 'NODE_STATUS_POLLING'
        timer = mock.Mock()
        mock_add_tm = self.patchobject(self.hm.TG, 'add_timer',
                                       return_value=timer)
        mock_check = self.patchobject(self.hm, '_periodic_check',
                                      return_value=mock.Mock())

        self.hm.register_cluster(ctx,
                                 cluster_id='CLUSTER_ID',
                                 check_type=matched_type,
                                 interval=50)

        mock_reg_create.assert_called_once_with(ctx,
                                                cluster_id='CLUSTER_ID',
                                                check_type=matched_type,
                                                engine_id='ENGINE_ID',
                                                interval=50,
                                                params={})
        mock_add_tm.assert_called_with(50, mock_check, None, 'CLUSTER_ID')
        self.assertEqual(1, len(self.hm.registries))

    @mock.patch.object(db_api, 'registry_delete')
    def test_unregister_cluster(self, mock_reg_delete):
        ctx = mock.Mock()
        timer = mock.Mock()
        registry = {
            'cluster_id': 'CLUSTER_ID',
            'check_type': 'NODE_STATUS_POLLING',
            'interval': 50,
            'params': {},
            'timer': timer
        }
        self.hm.rt['registries'] = [registry]
        mock_tm_done = self.patchobject(self.hm.TG, 'timer_done',
                                        return_value=mock.Mock())
        self.hm.unregister_cluster(ctx, cluster_id='CLUSTER_ID')
        mock_tm_done.assert_called_with(timer)
        self.assertEqual(0, len(self.hm.registries))
        mock_reg_delete.assert_called_once_with(ctx, 'CLUSTER_ID')

    @mock.patch.object(db_api, 'registry_claim')
    @mock.patch('oslo_messaging.Target')
    def test_start(self, mock_target, mock_reg_claim):
        tg = mock.Mock()
        self.hm.TG = tg
        target = mock.Mock()
        mock_target.return_value = target
        registry = {
            'cluster_id': 'CLUSTER_ID',
            'check_type': 'NODE_STATUS_POLLING',
            'interval': 50,
            'params': {},
        }
        rpc_server = mock.Mock()
        mock_st = self.patchobject(rpc_messaging, 'get_rpc_server',
                                   return_value=rpc_server)
        self.patchobject(self.hm, '_load_runtime_registry',
                         return_value=mock.Mock)
        self.hm.rt['registries'] = [registry]
        timer = mock.Mock()
        mock_add_tm = self.patchobject(self.hm.TG, 'add_timer',
                                       return_value=timer)
        mock_check = self.patchobject(self.hm, '_periodic_check',
                                      return_value=mock.Mock())
        self.hm.start()
        mock_target.assert_called_once_with(server='ENGINE_ID',
                                            topic='engine-health-mgr',
                                            version='1.0')
        mock_st.assert_called_once_with(target, self.hm)
        rpc_server.start.assert_called_once_with()
        mock_add_tm.assert_called_with(50, mock_check, None, 'CLUSTER_ID')
