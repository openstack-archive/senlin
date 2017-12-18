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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
import testtools

from senlin.engine.actions import base as action_base
from senlin.engine import cluster
from senlin.engine import node
from senlin.events import base
from senlin.events import message as MSG
from senlin.objects import notification as nobj
from senlin.tests.unit.common import utils

CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'


class TestMessageEvent(testtools.TestCase):

    def setUp(self):
        super(TestMessageEvent, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(nobj.NotificationBase, '_emit')
    def test__notify_cluster_action(self, mock_emit):
        cluster_id = uuidutils.generate_uuid()
        profile_id = uuidutils.generate_uuid()
        cluster_init = timeutils.utcnow(True)
        action_id = uuidutils.generate_uuid()
        cluster_params = {
            'id': cluster_id,
            'init_at': cluster_init,
            'min_size': 1,
            'max_size': 10,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        c1 = cluster.Cluster('fake_name', 5, profile_id, **cluster_params)
        action_params = {
            'id': action_id,
            'name': 'fake_name',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        action = action_base.Action(cluster_id, 'CLUSTER_CREATE', self.ctx,
                                    **action_params)
        publisher_id = 'senlin-engine:%s' % cfg.CONF.host
        expected_payload = {
            'senlin_object.data': {
                'action': {
                    'senlin_object.data': {
                        'action': 'CLUSTER_CREATE',
                        'created_at': None,
                        'data': '{}',
                        'end_time': None,
                        'id': action_id,
                        'inputs': '{}',
                        'name': 'fake_name',
                        'outputs': '{}',
                        'project': self.ctx.project_id,
                        'start_time': 1.23,
                        'status': 'RUNNING',
                        'status_reason': 'Good',
                        'target': cluster_id,
                        'timeout': 3600,
                        'user': self.ctx.user_id,
                    },
                    'senlin_object.name': 'ActionPayload',
                    'senlin_object.namespace': 'senlin',
                    'senlin_object.version': '1.0'
                },
                'cluster': {
                    'senlin_object.data': {
                        'created_at': None,
                        'data': '{}',
                        'dependents': '{}',
                        'desired_capacity': 5,
                        'domain': '',
                        'id': cluster_id,
                        'init_at': mock.ANY,
                        'max_size': 10,
                        'metadata': '{}',
                        'min_size': 1,
                        'name': 'fake_name',
                        'profile_id': profile_id,
                        'project': u'project1',
                        'status': u'ACTIVE',
                        'status_reason': u'Good',
                        'timeout': 4,
                        'updated_at': None,
                        'user': u'user1'
                    },
                    'senlin_object.name': 'ClusterPayload',
                    'senlin_object.namespace': 'senlin',
                    'senlin_object.version': '1.0'
                },
                'exception': None
            },
            'senlin_object.name': 'ClusterActionPayload',
            'senlin_object.namespace': 'senlin',
            'senlin_object.version': '1.0'
        }

        res = MSG.MessageEvent._notify_cluster_action(
            self.ctx, logging.INFO, c1, action, phase='start')

        self.assertIsNone(res)

        mock_emit.assert_called_once_with(
            self.ctx, 'cluster.create.start', publisher_id, mock.ANY)
        payload = mock_emit.call_args[0][3]
        self.assertEqual(expected_payload, payload)

    @mock.patch.object(nobj.NotificationBase, '_emit')
    def test__notify_node_action(self, mock_emit):
        node_id = uuidutils.generate_uuid()
        profile_id = uuidutils.generate_uuid()
        node_init = timeutils.utcnow(True)
        action_id = uuidutils.generate_uuid()
        node_params = {
            'id': node_id,
            'cluster_id': '',
            'index': -1,
            'init_at': node_init,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        n1 = node.Node('fake_name', profile_id, **node_params)
        action_params = {
            'id': action_id,
            'name': 'fake_name',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
        }
        action = action_base.Action(node_id, 'NODE_CREATE', self.ctx,
                                    **action_params)
        publisher_id = 'senlin-engine:%s' % cfg.CONF.host
        expected_payload = {
            'senlin_object.data': {
                'action': {
                    'senlin_object.data': {
                        'action': 'NODE_CREATE',
                        'created_at': None,
                        'data': '{}',
                        'end_time': None,
                        'id': action_id,
                        'inputs': '{}',
                        'name': 'fake_name',
                        'outputs': '{}',
                        'project': self.ctx.project_id,
                        'start_time': 1.23,
                        'status': 'RUNNING',
                        'status_reason': 'Good',
                        'target': node_id,
                        'timeout': 3600,
                        'user': self.ctx.user_id,
                    },
                    'senlin_object.name': 'ActionPayload',
                    'senlin_object.namespace': 'senlin',
                    'senlin_object.version': '1.0'
                },
                'node': {
                    'senlin_object.data': {
                        'cluster_id': '',
                        'created_at': None,
                        'data': '{}',
                        'dependents': '{}',
                        'domain': '',
                        'id': node_id,
                        'index': -1,
                        'init_at': mock.ANY,
                        'metadata': '{}',
                        'name': 'fake_name',
                        'physical_id': None,
                        'profile_id': profile_id,
                        'project': 'project1',
                        'role': '',
                        'status': 'ACTIVE',
                        'status_reason': 'Good',
                        'updated_at': None,
                        'user': 'user1',
                    },
                    'senlin_object.name': 'NodePayload',
                    'senlin_object.namespace': 'senlin',
                    'senlin_object.version': '1.0'
                },
                'exception': None
            },
            'senlin_object.name': 'NodeActionPayload',
            'senlin_object.namespace': 'senlin',
            'senlin_object.version': '1.0'
        }

        res = MSG.MessageEvent._notify_node_action(
            self.ctx, logging.INFO, n1, action, phase='start')

        self.assertIsNone(res)

        mock_emit.assert_called_once_with(
            self.ctx, 'node.create.start', publisher_id, mock.ANY)
        payload = mock_emit.call_args[0][3]
        self.assertEqual(expected_payload, payload)

    @mock.patch.object(MSG.MessageEvent, '_notify_cluster_action')
    @mock.patch.object(base.EventBackend, '_check_entity')
    def test_dump_cluster_action_event(self, mock_check, mock_notify):
        mock_check.return_value = 'CLUSTER'
        entity = mock.Mock()
        action = mock.Mock(context=self.ctx, entity=entity)

        res = MSG.MessageEvent.dump(logging.INFO, action)

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_notify.assert_called_once_with(self.ctx, logging.INFO, entity,
                                            action)

    @mock.patch.object(MSG.MessageEvent, '_notify_cluster_action')
    @mock.patch.object(base.EventBackend, '_check_entity')
    def test_dump_cluster_action_event_warn(self, mock_check, mock_notify):
        mock_check.return_value = 'CLUSTER'
        entity = mock.Mock()
        action = mock.Mock(context=self.ctx, entity=entity)

        res = MSG.MessageEvent.dump(logging.WARNING, action)

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_notify.assert_called_once_with(self.ctx, logging.WARNING,
                                            entity, action)

    @mock.patch.object(MSG.MessageEvent, '_notify_node_action')
    @mock.patch.object(base.EventBackend, '_check_entity')
    def test_dump_node_action_event(self, mock_check, mock_notify):
        mock_check.return_value = 'NODE'
        entity = mock.Mock()
        action = mock.Mock(context=self.ctx, entity=entity)

        res = MSG.MessageEvent.dump(logging.INFO, action)

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_notify.assert_called_once_with(self.ctx, logging.INFO, entity,
                                            action)
