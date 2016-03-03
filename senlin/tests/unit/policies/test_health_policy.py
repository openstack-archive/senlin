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
from senlin.engine import health_manager
from senlin.policies import health_policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestHealthPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestHealthPolicy, self).setUp()
        self.context = utils.dummy_context()

        self.spec = {
            'type': 'senlin.policy.health',
            'version': '1.0',
            'properties': {
                'detection': {
                    'type': 'NODE_STATUS_POLLING',
                    'options': {
                        'interval': 60
                    }
                },
                'recovery': {
                    'fencing': ['COMPUTE'],
                    'actions': ['REBUILD']
                }
            }
        }
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        node = mock.Mock()
        node.status = 'ACTIVE'
        cluster.nodes = [node]
        self.cluster = cluster
        self.patch('senlin.rpc.client.EngineClient')
        self.hp = health_policy.HealthPolicy('test-policy', self.spec)

    def test_policy_init(self):
        self.assertIsNone(self.hp.id)
        self.assertEqual('test-policy', self.hp.name)
        self.assertEqual('senlin.policy.health-1.0', self.hp.type)
        self.assertEqual('NODE_STATUS_POLLING', self.hp.check_type)
        self.assertEqual(60, self.hp.interval)
        self.assertEqual(['REBUILD'], self.hp.recover_actions)

    @mock.patch.object(health_manager, 'register')
    def test_attach(self, mock_hm_reg):

        policy_data = {
            'HealthPolicy': {
                'data': {
                    'check_type': self.hp.check_type,
                    'interval': self.hp.interval},
                'version': '1.0'
            }
        }

        res, data = self.hp.attach(self.cluster)
        self.assertTrue(res)
        self.assertEqual(policy_data, data)
        kwargs = {
            'check_type': self.hp.check_type,
            'interval': self.hp.interval,
            'params': {},
        }
        mock_hm_reg.assert_called_once_with('CLUSTER_ID',
                                            engine_id=None,
                                            **kwargs)

    @mock.patch.object(health_manager, 'unregister')
    def test_detach(self, mock_hm_reg):
        res, data = self.hp.detach(self.cluster)
        self.assertTrue(res)
        self.assertEqual('', data)
        mock_hm_reg.assert_called_once_with('CLUSTER_ID')

    def test_pre_op(self):
        action = mock.Mock()
        action.context = 'action_context'
        action.data = {}
        action.action = consts.CLUSTER_RECOVER
        res = self.hp.pre_op(self.cluster.id, action)
        self.assertTrue(res)
        data = {'health': {'recover_action': 'REBUILD'}}
        self.assertEqual(data, action.data)

    def test_post_op(self):
        action = mock.Mock()
        res = self.hp.post_op(self.cluster.id, action)
        self.assertTrue(res)
