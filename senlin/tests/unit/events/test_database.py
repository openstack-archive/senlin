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

from senlin.events import database as DB
from senlin.objects import event as eo
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'


class TestDatabase(base.SenlinTestCase):

    def setUp(self):
        super(TestDatabase, self).setUp()
        self.context = utils.dummy_context()

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test__check_entity_cluster(self, mock_get):
        entity = mock.Mock(id='obj-id')
        entity.name = 'obj-name'
        mock_get.return_value = 'Cluster'

        res = DB.DBEvent._check_entity(entity)

        self.assertEqual(('obj-id', 'obj-id', 'obj-name', 'CLUSTER'), res)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test__check_entity_node(self, mock_get):
        entity = mock.Mock(id='obj-id', cluster_id='cluster-id')
        entity.name = 'obj-name'
        mock_get.return_value = 'Node'

        res = DB.DBEvent._check_entity(entity)

        self.assertEqual(('obj-id', 'cluster-id', 'obj-name', 'NODE'), res)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test__check_entity_clusteraction(self, mock_get):
        entity = mock.Mock(target=CLUSTER_ID)
        entity.cluster = mock.Mock()
        entity.cluster.name = 'obj-name'
        mock_get.return_value = 'ClusterAction'

        res = DB.DBEvent._check_entity(entity)

        self.assertEqual((CLUSTER_ID, CLUSTER_ID, 'obj-name', 'CLUSTER'), res)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test__check_entity_nodeaction(self, mock_get):
        entity = mock.Mock(target='FAKE_ID')
        entity.node = mock.Mock()
        entity.node.name = 'node-name'
        entity.node.cluster_id = CLUSTER_ID
        mock_get.return_value = 'NodeAction'

        res = DB.DBEvent._check_entity(entity)

        self.assertEqual(('FAKE_ID', CLUSTER_ID, 'node-name', 'NODE'), res)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch.object(DB.DBEvent, '_check_entity')
    @mock.patch.object(eo.Event, 'create')
    def test_dump(self, mock_create, mock_check):
        mock_check.return_value = ('1', '2', '3', '4')
        entity = mock.Mock()

        res = DB.DBEvent.dump(self.context, 'LEVEL', entity, 'ACTION',
                              'STATUS', 'REASON')

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_create.assert_called_once_with(
            self.context,
            {
                'level': 'LEVEL',
                'timestamp': mock.ANY,
                'oid': '1',
                'otype': '4',
                'oname': '3',
                'cluster_id': '2',
                'user': self.context.user,
                'project': self.context.project,
                'action': 'ACTION',
                'status': 'STATUS',
                'status_reason': 'REASON',
                'meta_data': {}
            })

    @mock.patch.object(DB.DBEvent, '_check_entity')
    @mock.patch.object(eo.Event, 'create')
    def test_dump_with_extra_but_no_status_(self, mock_create, mock_check):
        mock_check.return_value = ('1', '2', '3', '4')
        entity = mock.Mock(status='S1', status_reason='R1')

        res = DB.DBEvent.dump(self.context, 'LEVEL', entity, 'ACTION',
                              timestamp='NOW', extra={'foo': 'bar'})

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_create.assert_called_once_with(
            self.context,
            {
                'level': 'LEVEL',
                'timestamp': 'NOW',
                'oid': '1',
                'otype': '4',
                'oname': '3',
                'cluster_id': '2',
                'user': self.context.user,
                'project': self.context.project,
                'action': 'ACTION',
                'status': 'S1',
                'status_reason': 'R1',
                'meta_data': {'foo': 'bar'}
            })
