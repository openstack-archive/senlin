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

import datetime

from senlin.db.sqlalchemy import api as db_api
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPIEventTest(base.SenlinTestCase):

    def setUp(self):
        super(DBAPIEventTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)

    def test_event_create_get(self):
        event = shared.create_event(self.ctx)
        ret_event = db_api.event_get(self.ctx, event.id)
        self.assertIsNotNone(ret_event)
        timestamp = datetime.datetime.strftime(ret_event.timestamp,
                                               '%Y-%m-%d %H:%M:%S.%f')
        self.assertEqual('2014-12-19 11:51:54.670244', timestamp)
        self.assertEqual(50, ret_event.level)
        self.assertEqual(UUID1, ret_event.obj_id)
        self.assertEqual('NODE', ret_event.obj_type)
        self.assertEqual('Server01', ret_event.obj_name)
        self.assertEqual('UPDATE', ret_event.action)
        self.assertEqual('FAILED', ret_event.status)
        self.assertEqual('Server already deleted', ret_event.status_reason)
        self.assertIsNone(ret_event.user)

    def test_event_get_by_short_id(self):
        event = shared.create_event(self.ctx)
        short_id = event.id[:6]
        ret_event = db_api.event_get_by_short_id(self.ctx, short_id)
        self.assertIsNotNone(ret_event)

        short_id = event.id[:8]
        ret_event = db_api.event_get_by_short_id(self.ctx, short_id)
        self.assertIsNotNone(ret_event)

    def test_event_get_all(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         tenant_id='tenant1')
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         tenant_id='tenant2')
        values = [
            {'obj_id': cluster1.id, 'obj_name': 'node1'},
            {'obj_id': cluster1.id, 'obj_name': 'node2'},
            {'obj_id': cluster2.id, 'obj_name': 'node3'},
        ]
        for val in values:
            shared.create_event(self.ctx, **val)

        events = db_api.event_get_all(self.ctx)
        self.assertEqual(3, len(events))

        cluster_ids = [event.obj_id for event in events]
        obj_names = [event.obj_name for event in events]
        for val in values:
            self.assertIn(val['obj_id'], cluster_ids)
            self.assertIn(val['obj_name'], obj_names)

    def test_event_get_all_by_cluster(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         tenant_id='tenant1')
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         tenant_id='tenant2')
        values = [
            {'obj_id': cluster1.id, 'obj_name': 'cluster1',
             'obj_type': 'CLUSTER'},
            {'obj_id': cluster1.id, 'obj_name': 'cluster2',
             'obj_type': 'CLUSTER'},
            {'obj_id': cluster2.id, 'obj_name': 'cluster3',
             'obj_type': 'CLUSTER'},
        ]
        for val in values:
            shared.create_event(self.ctx, **val)

        self.ctx.tenant_id = 'tenant1'
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(2, len(events))

        self.ctx.tenant_id = 'tenant2'
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(1, len(events))

    def test_event_count_all_by_cluster(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        values = [
            {'obj_id': cluster1.id, 'obj_name': 'cluster1',
             'obj_type': 'CLUSTER'},
            {'obj_id': cluster1.id, 'obj_name': 'cluster2',
             'obj_type': 'CLUSTER'},
            {'obj_id': cluster2.id, 'obj_name': 'cluster3',
             'obj_type': 'CLUSTER'},
        ]
        for val in values:
            shared.create_event(self.ctx, **val)

        self.assertEqual(2, db_api.event_count_by_cluster(self.ctx,
                                                          cluster1.id))
        self.assertEqual(1, db_api.event_count_by_cluster(self.ctx,
                                                          cluster2.id))

    def test_event_node_status_reason_truncate(self):
        event = shared.create_event(self.ctx, status_reason='a' * 1024)
        ret_event = db_api.event_get(self.ctx, event.id)
        self.assertEqual('a' * 255, ret_event.status_reason)

    def test_event_get_all_filtered(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        values = [
            {'obj_id': cluster1.id, 'obj_name': 'c1', 'obj_type': 'CLUSTER',
             'status': 'OK'},
            {'obj_id': cluster1.id, 'obj_name': 'c1', 'obj_type': 'CLUSTER',
             'status': 'FAILED'},
            {'obj_id': cluster2.id, 'obj_name': 'c2', 'obj_type': 'CLUSTER',
             'status': 'FAILED'},
            {'obj_id': cluster2.id, 'obj_name': 'c2', 'obj_type': 'CLUSTER',
             'status': 'FAILED'},
            {'obj_id': cluster2.id, 'obj_name': 'c2', 'obj_type': 'CLUSTER',
             'status': 'FAILED'},
        ]
        for val in values:
            shared.create_event(self.ctx, **val)

        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(2, len(events))

        # test filter by status
        filters = {'status': 'FAILED'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 filters=filters)
        self.assertEqual(1, len(events))
        self.assertEqual('FAILED', events[0].status)

        # test filter by name
        filters = {'obj_name': 'c1'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 filters=filters)
        self.assertEqual(2, len(events))
        self.assertEqual('c1', events[0].obj_name)
        self.assertEqual('c1', events[1].obj_name)

        # test filter by node_type
        filters = {'obj_type': 'CLUSTER'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id,
                                                 filters=filters)
        self.assertEqual(3, len(events))
        self.assertEqual('CLUSTER', events[0].obj_type)
        self.assertEqual('CLUSTER', events[1].obj_type)

        filters = {'obj_type': 'CLUSTER'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id,
                                                 filters=filters)
        self.assertEqual(3, len(events))

        # test limit and marker
        events_all = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        marker = events_all[0].id
        expected = events_all[1].id
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 limit=1, marker=marker)
        self.assertEqual(1, len(events))
        self.assertEqual(expected, events[0].id)
