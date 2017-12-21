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
import testtools

from senlin.common import consts
from senlin.events import base
from senlin.events import database as DB
from senlin.objects import event as eo
from senlin.tests.unit.common import utils

CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'


class TestDatabase(testtools.TestCase):

    def setUp(self):
        super(TestDatabase, self).setUp()
        self.context = utils.dummy_context()

    @mock.patch.object(base.EventBackend, '_check_entity')
    @mock.patch.object(eo.Event, 'create')
    def test_dump(self, mock_create, mock_check):
        mock_check.return_value = 'CLUSTER'
        entity = mock.Mock(id='CLUSTER_ID')
        entity.name = 'cluster1'
        action = mock.Mock(context=self.context, action='ACTION',
                           entity=entity)

        res = DB.DBEvent.dump('LEVEL', action, phase='STATUS', reason='REASON')

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
                'user': self.context.user_id,
                'project': self.context.project_id,
                'action': 'ACTION',
                'status': 'STATUS',
                'status_reason': 'REASON',
                'meta_data': {}
            })

    @mock.patch.object(base.EventBackend, '_check_entity')
    @mock.patch.object(eo.Event, 'create')
    def test_dump_with_extra_but_no_status_(self, mock_create, mock_check):
        mock_check.return_value = 'NODE'
        entity = mock.Mock(id='NODE_ID', status='S1', status_reason='R1',
                           cluster_id='CLUSTER_ID')
        entity.name = 'node1'

        action = mock.Mock(context=self.context, entity=entity,
                           action='ACTION')

        res = DB.DBEvent.dump('LEVEL', action, timestamp='NOW',
                              extra={'foo': 'bar'})

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
                'user': self.context.user_id,
                'project': self.context.project_id,
                'action': 'ACTION',
                'status': 'S1',
                'status_reason': 'R1',
                'meta_data': {'foo': 'bar'}
            })

    @mock.patch.object(base.EventBackend, '_check_entity')
    @mock.patch.object(eo.Event, 'create')
    def test_dump_operation_action(self, mock_create, mock_check):
        mock_check.return_value = 'CLUSTER'
        entity = mock.Mock(id='CLUSTER_ID')
        entity.name = 'cluster1'
        action = mock.Mock(context=self.context, action=consts.NODE_OPERATION,
                           entity=entity, inputs={'operation': 'dance'})

        res = DB.DBEvent.dump('LEVEL', action, phase='STATUS', reason='REASON')

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
                'user': self.context.user_id,
                'project': self.context.project_id,
                'action': 'dance',
                'status': 'STATUS',
                'status_reason': 'REASON',
                'meta_data': {}
            })
