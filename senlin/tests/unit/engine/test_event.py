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
from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.engine import cluster as cluster_mod
from senlin.engine import event as EVENT
from senlin.objects import event as eo
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'


class TestEvent(base.SenlinTestCase):

    def setUp(self):
        super(TestEvent, self).setUp()
        self.context = utils.dummy_context()

    def test_event_init(self):
        timestamp = timeutils.utcnow(True)
        kwargs = {
            'id': 'FAKE-ID',
            'user': 'test-user',
            'project': 'test-project',
            'action': 'fake-action',
            'status': 'ACTIVE',
            'status_reason': 'Weather is clear',
            'oid': 'FAKE-OBJ-ID',
            'otype': 'CLUSTER-TYPE',
            'oname': 'fake-cluster',
            'cluster_id': CLUSTER_ID,
            'metadata': {'foo': 'bar'},
        }

        event = EVENT.Event(timestamp, logging.CRITICAL, **kwargs)

        self.assertEqual(timestamp, event.timestamp)
        self.assertEqual(logging.CRITICAL, event.level)
        self.assertEqual('FAKE-ID', event.id)
        self.assertEqual('test-user', event.user)
        self.assertEqual('test-project', event.project)

        self.assertEqual('fake-action', event.action)
        self.assertEqual('ACTIVE', event.status)
        self.assertEqual('Weather is clear', event.status_reason)

        self.assertEqual('FAKE-OBJ-ID', event.oid)
        self.assertEqual('CLUSTER-TYPE', event.otype)
        self.assertEqual('fake-cluster', event.oname)
        self.assertEqual(CLUSTER_ID, event.cluster_id)
        self.assertEqual({'foo': 'bar'}, event.metadata)

    def test_event_init_with_entity(self):
        timestamp = timeutils.utcnow(True)
        x_cluster = cluster_mod.Cluster('fake-cluster', 0, 'fake-profile',
                                        id='FAKE_CLUSTER')

        event = EVENT.Event(timestamp, logging.CRITICAL, x_cluster,
                            action="FAKE_ACTION", status="ACTIVE",
                            status_reason="Recovered just now",
                            user=self.context.user,
                            project=self.context.project)

        self.assertEqual(timestamp, event.timestamp)
        self.assertIsNone(event.id)
        self.assertEqual(logging.CRITICAL, event.level)
        self.assertEqual(self.context.user, event.user)
        self.assertEqual(self.context.project, event.project)
        self.assertEqual('FAKE_ACTION', event.action)
        self.assertEqual('ACTIVE', event.status)
        self.assertEqual('Recovered just now', event.status_reason)

        self.assertEqual('FAKE_CLUSTER', event.oid)
        self.assertEqual('fake-cluster', event.oname)
        self.assertEqual('FAKE_CLUSTER', event.cluster_id)
        self.assertEqual('CLUSTER', event.otype)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test_event__infer_entity_data_cluster(self, mock_get):
        entity = mock.Mock(id='obj-id', status='fake-status',
                           status_reason='fake-reason', target='fake-target',
                           cluster_id='cluster-id')
        entity.name = 'obj-name'
        mock_get.return_value = 'Cluster'

        event = EVENT.Event('timestamp', 'level', entity)

        self.assertEqual('timestamp', event.timestamp)
        self.assertEqual('level', event.level)
        self.assertEqual('obj-name', event.oname)
        self.assertEqual('fake-status', event.status)
        self.assertEqual('fake-reason', event.status_reason)
        self.assertEqual('CLUSTER', event.otype)
        self.assertEqual('obj-id', event.oid)
        self.assertEqual('obj-id', event.cluster_id)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test_event__infer_entity_data_node(self, mock_get):
        entity = mock.Mock(id='obj-id', status='fake-status',
                           status_reason='fake-reason', target='fake-target',
                           cluster_id='cluster-id')
        entity.name = 'obj-name'
        mock_get.return_value = 'Node'

        event = EVENT.Event('timestamp', 'level', entity)

        self.assertEqual('timestamp', event.timestamp)
        self.assertEqual('level', event.level)
        self.assertEqual('obj-name', event.oname)
        self.assertEqual('fake-status', event.status)
        self.assertEqual('fake-reason', event.status_reason)
        self.assertEqual('NODE', event.otype)
        self.assertEqual('obj-id', event.oid)
        self.assertEqual('cluster-id', event.cluster_id)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test_event__infer_entity_data_clusteraction(self, mock_get):
        entity = mock.Mock(status='fake-status', status_reason='fake-reason',
                           target=CLUSTER_ID)
        entity.cluster = mock.Mock()
        entity.cluster.name = 'obj-name'
        mock_get.return_value = 'ClusterAction'

        event = EVENT.Event('timestamp', 'level', entity)

        self.assertEqual('timestamp', event.timestamp)
        self.assertEqual('level', event.level)
        self.assertEqual('obj-name', event.oname)
        self.assertEqual('fake-status', event.status)
        self.assertEqual('fake-reason', event.status_reason)
        self.assertEqual('CLUSTER', event.otype)
        self.assertEqual(CLUSTER_ID, event.oid)
        self.assertEqual(CLUSTER_ID, event.cluster_id)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test_event__infer_entity_data_nodeaction(self, mock_get):
        entity = mock.Mock(status='fake-status', status_reason='fake-reason',
                           target='fake-node')
        entity.node = mock.Mock()
        entity.node.name = 'obj-name'
        entity.node.cluster_id = CLUSTER_ID
        mock_get.return_value = 'NodeAction'

        event = EVENT.Event('timestamp', 'level', entity)

        self.assertEqual('timestamp', event.timestamp)
        self.assertEqual('level', event.level)
        self.assertEqual('obj-name', event.oname)
        self.assertEqual('fake-status', event.status)
        self.assertEqual('fake-reason', event.status_reason)
        self.assertEqual('NODE', event.otype)
        self.assertEqual('fake-node', event.oid)
        self.assertEqual(CLUSTER_ID, event.cluster_id)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    def test_event_store(self):
        timestamp = timeutils.utcnow(True)
        kwargs = {
            'user': self.context.user,
            'project': self.context.project,
            'action': 'fake-action',
            'status': 'ACTIVE',
            'status_reason': 'Weather is clear',
            'oid': CLUSTER_ID,
            'otype': 'CLUSTER TYPE',
            'oname': 'fake-cluster',
            'cluster_id': CLUSTER_ID,
            'metadata': {'foo': 'bar'},
        }

        event = EVENT.Event(timestamp, logging.CRITICAL, **kwargs)
        self.assertIsNone(event.id)

        event_id = event.store(self.context)

        self.assertIsNotNone(event_id)
        self.assertEqual(event_id, event.id)

        result = eo.Event.get(self.context, event_id)

        self.assertIsNotNone(result)
        self.assertEqual(event_id, result.id)
        self.assertEqual(timestamp, result.timestamp)
        self.assertEqual(event.level, int(result.level))
        self.assertEqual(event.user, result.user)
        self.assertEqual(event.project, result.project)
        self.assertEqual(event.action, result.action)
        self.assertEqual(event.status, result.status)
        self.assertEqual(event.status_reason, result.status_reason)
        self.assertEqual(event.oid, result.oid)
        self.assertEqual(event.otype, result.otype)
        self.assertEqual(event.oname, result.oname)
        self.assertEqual(event.cluster_id, result.cluster_id)
        self.assertEqual(event.metadata, result.meta_data)
