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
        entity = mock.Mock()
        mock_get.return_value = 'Cluster'

        res = DB.DBEvent._check_entity(entity)

        self.assertEqual('CLUSTER', res)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch('oslo_utils.reflection.get_class_name')
    def test__check_entity_node(self, mock_get):
        entity = mock.Mock()
        mock_get.return_value = 'Node'

        res = DB.DBEvent._check_entity(entity)

        self.assertEqual('NODE', res)
        mock_get.assert_called_once_with(entity, fully_qualified=False)

    @mock.patch.object(DB.DBEvent, '_check_entity')
    @mock.patch.object(eo.Event, 'create')
    def test_dump(self, mock_create, mock_check):
        mock_check.return_value = 'CLUSTER'
        entity = mock.Mock(id='CLUSTER_ID')
        entity.name = 'cluster1'
        action = mock.Mock(action='ACTION')

        res = DB.DBEvent.dump(self.context, 'LEVEL', entity, action,
                              status='STATUS', reason='REASON')

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_create.assert_called_once_with(
            self.context,
            {
                'level': 'LEVEL',
                'timestamp': mock.ANY,
                'oid': 'CLUSTER_ID',
                'otype': 'CLUSTER',
                'oname': 'cluster1',
                'cluster_id': 'CLUSTER_ID',
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
        mock_check.return_value = 'NODE'
        entity = mock.Mock(id='NODE_ID', status='S1', status_reason='R1',
                           cluster_id='CLUSTER_ID')
        entity.name = 'node1'

        action = mock.Mock(action='ACTION')

        res = DB.DBEvent.dump(self.context, 'LEVEL', entity, action,
                              timestamp='NOW', extra={'foo': 'bar'})

        self.assertIsNone(res)
        mock_check.assert_called_once_with(entity)
        mock_create.assert_called_once_with(
            self.context,
            {
                'level': 'LEVEL',
                'timestamp': 'NOW',
                'oid': 'NODE_ID',
                'otype': 'NODE',
                'oname': 'node1',
                'cluster_id': 'CLUSTER_ID',
                'user': self.context.user,
                'project': self.context.project,
                'action': 'ACTION',
                'status': 'S1',
                'status_reason': 'R1',
                'meta_data': {'foo': 'bar'}
            })
