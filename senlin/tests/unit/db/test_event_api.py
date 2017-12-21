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

from oslo_log import log as logging
from oslo_utils import reflection
from oslo_utils import timeutils as tu

from senlin.common import utils as common_utils
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPIEventTest(base.SenlinTestCase):

    def setUp(self):
        super(DBAPIEventTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)

    def create_event(self, ctx, timestamp=None, level=logging.INFO,
                     entity=None, action=None, status=None,
                     status_reason=None):

        fake_timestamp = tu.parse_strtime(
            '2014-12-19 11:51:54.670244', '%Y-%m-%d %H:%M:%S.%f')

        if entity:
            e_name = reflection.get_class_name(entity, fully_qualified=False)
            type_name = e_name.upper()
            if type_name == 'CLUSTER':
                cluster_id = entity.id
            elif type_name == 'NODE':
                cluster_id = entity.cluster_id
            else:
                cluster_id = ''
        else:
            type_name = ''
            cluster_id = ''

        values = {
            'timestamp': timestamp or fake_timestamp,
            'level': level,
            'oid': entity.id if entity else '',
            'oname': entity.name if entity else '',
            'otype': type_name,
            'cluster_id': cluster_id,
            'action': action or '',
            'status': status or '',
            'status_reason': status_reason or '',
            'user': ctx.user_id,
            'project': ctx.project_id,
        }

        # Make sure all fields can be customized
        return db_api.event_create(ctx, values)

    def test_event_create_get(self):
        event = self.create_event(self.ctx)
        ret_event = db_api.event_get(self.ctx, event.id)
        self.assertIsNotNone(ret_event)
        tst_timestamp = tu.parse_strtime('2014-12-19 11:51:54.670244',
                                         '%Y-%m-%d %H:%M:%S.%f')

        self.assertEqual(common_utils.isotime(tst_timestamp),
                         common_utils.isotime(ret_event.timestamp))
        self.assertEqual('20', ret_event.level)
        self.assertEqual('', ret_event.oid)
        self.assertEqual('', ret_event.otype)
        self.assertEqual('', ret_event.oname)
        self.assertEqual('', ret_event.action)
        self.assertEqual('', ret_event.status)
        self.assertEqual('', ret_event.status_reason)
        self.assertEqual(self.ctx.user_id, ret_event.user)
        self.assertEqual(self.ctx.project_id, ret_event.project)

    def test_event_get_diff_project(self):
        event = self.create_event(self.ctx)
        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.event_get(new_ctx, event.id)
        self.assertIsNone(res)
        res = db_api.event_get(new_ctx, event.id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(event.id, res.id)

    def test_event_get_admin_context(self):
        event = self.create_event(self.ctx)
        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        res = db_api.event_get(admin_ctx, event.id, project_safe=True)
        self.assertIsNone(res)
        res = db_api.event_get(admin_ctx, event.id, project_safe=False)
        self.assertIsNotNone(res)

    def test_event_get_by_short_id(self):
        event = self.create_event(self.ctx)
        short_id = event.id[:6]
        ret_event = db_api.event_get_by_short_id(self.ctx, short_id)
        self.assertIsNotNone(ret_event)

        short_id = event.id[:8]
        ret_event = db_api.event_get_by_short_id(self.ctx, short_id)
        self.assertIsNotNone(ret_event)

        ret_event = db_api.event_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(ret_event)

    def test_event_get_by_short_id_diff_project(self):
        event = self.create_event(self.ctx)

        new_ctx = utils.dummy_context(project='a-different-project')
        short_id = event.id[:8]
        res = db_api.event_get_by_short_id(new_ctx, short_id)
        self.assertIsNone(res)
        res = db_api.event_get_by_short_id(new_ctx, short_id,
                                           project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(event.id, res.id)

    def test_event_get_all(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)

        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster2)

        # Default project_safe
        events = db_api.event_get_all(self.ctx)
        self.assertEqual(3, len(events))

        cluster_ids = [event.oid for event in events]
        onames = [event.oname for event in events]

        self.assertIn(cluster1.id, cluster_ids)
        self.assertIn(cluster1.name, onames)
        self.assertIn(cluster2.id, cluster_ids)
        self.assertIn(cluster2.name, onames)

    def test_event_get_all_with_limit(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)

        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)

        events = db_api.event_get_all(self.ctx)
        self.assertEqual(3, len(events))

        events = db_api.event_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(events))

        events = db_api.event_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(events))

    def test_event_get_all_with_limit_and_marker(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)

        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)

        events_all = db_api.event_get_all(self.ctx)
        self.assertEqual(3, len(events_all))

        marker = events_all[0].id
        event1_id = events_all[1].id
        event2_id = events_all[2].id
        events = db_api.event_get_all(self.ctx, limit=1, marker=marker)
        self.assertEqual(1, len(events))
        self.assertEqual(event1_id, events[0].id)

        events = db_api.event_get_all(self.ctx, limit=2, marker=marker)
        self.assertEqual(2, len(events))
        self.assertEqual(event1_id, events[0].id)
        self.assertEqual(event2_id, events[1].id)

        marker = event1_id
        events = db_api.event_get_all(self.ctx, limit=1, marker=marker)
        self.assertEqual(1, len(events))
        self.assertEqual(event2_id, events[0].id)

    def test_event_get_all_with_sorting(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)

        event1 = self.create_event(self.ctx, entity=cluster1,
                                   timestamp=tu.utcnow(True),
                                   action='action2')
        event2 = self.create_event(self.ctx, entity=cluster1,
                                   timestamp=tu.utcnow(True),
                                   action='action3')
        event3 = self.create_event(self.ctx, entity=cluster1,
                                   timestamp=tu.utcnow(True),
                                   action='action1')

        events = db_api.event_get_all(self.ctx, sort='timestamp')
        self.assertEqual(event1.id, events[0].id)
        self.assertEqual(event2.id, events[1].id)
        self.assertEqual(event3.id, events[2].id)

        events = db_api.event_get_all(self.ctx, sort='timestamp:desc')
        self.assertEqual(event1.id, events[2].id)
        self.assertEqual(event2.id, events[1].id)
        self.assertEqual(event3.id, events[0].id)

        events = db_api.event_get_all(self.ctx, sort='action')
        self.assertEqual(event1.id, events[1].id)
        self.assertEqual(event2.id, events[2].id)
        self.assertEqual(event3.id, events[0].id)

        events = db_api.event_get_all(self.ctx, sort='action:desc')
        self.assertEqual(event1.id, events[1].id)
        self.assertEqual(event2.id, events[0].id)
        self.assertEqual(event3.id, events[2].id)

    def test_event_get_all_project_safe(self):
        self.ctx.project_id = 'project_1'
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster1')
        self.create_event(self.ctx, entity=cluster1)
        self.ctx.project_id = 'project_2'
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster2')
        self.create_event(self.ctx, entity=cluster2, action='CLUSTER_CREATE')
        self.create_event(self.ctx, entity=cluster2, action='CLUSTER_DELETE')

        # Default project_safe to true, only the last two events are visible
        events = db_api.event_get_all(self.ctx)
        self.assertEqual(2, len(events))

        oids = [event.oid for event in events]
        onames = [event.oname for event in events]
        self.assertNotIn(cluster1.id, oids)
        self.assertNotIn(cluster1.name, onames)
        self.assertIn(cluster2.id, oids)
        self.assertIn(cluster2.name, onames)

        # Set project_safe to false, we should get all three events
        events = db_api.event_get_all(self.ctx, project_safe=False)
        self.assertEqual(3, len(events))

        oids = [event.oid for event in events]
        onames = [event.oname for event in events]
        self.assertIn(cluster1.id, oids)
        self.assertIn(cluster1.name, onames)
        self.assertIn(cluster2.id, oids)
        self.assertIn(cluster2.name, onames)

    def test_event_get_all_admin_context(self):
        self.ctx.project_id = 'project_1'
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster1')
        self.create_event(self.ctx, entity=cluster1)
        self.ctx.project_id = 'project_2'
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster2')
        self.create_event(self.ctx, entity=cluster2, action='CLUSTER_CREATE')
        self.create_event(self.ctx, entity=cluster2, action='CLUSTER_DELETE')

        admin_ctx = utils.dummy_context(project='another-project',
                                        is_admin=True)
        events = db_api.event_get_all(admin_ctx, project_safe=True)
        self.assertEqual(0, len(events))
        events = db_api.event_get_all(admin_ctx, project_safe=False)
        self.assertEqual(3, len(events))

    def test_event_get_all_by_cluster(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        node1_1 = shared.create_node(self.ctx, cluster1, self.profile)
        node1_2 = shared.create_node(self.ctx, cluster1, self.profile)
        node2_1 = shared.create_node(self.ctx, cluster2, self.profile)
        node_orphan = shared.create_node(self.ctx, None, self.profile)

        # 1 event for cluster 1
        self.create_event(self.ctx, entity=cluster1)
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(events))
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(0, len(events))

        # two more events for cluster 1, with one for an orphan node
        self.create_event(self.ctx, entity=node1_1)
        self.create_event(self.ctx, entity=node1_2)
        self.create_event(self.ctx, entity=node_orphan)

        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(3, len(events))
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(0, len(events))

        # one more events for cluster 2, with one for an orphan node
        self.create_event(self.ctx, entity=cluster2)
        self.create_event(self.ctx, entity=node_orphan)

        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(3, len(events))
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(1, len(events))

        # two more events for cluster 2, with one for an orphan node
        self.create_event(self.ctx, entity=node2_1)
        self.create_event(self.ctx, entity=node2_1)
        self.create_event(self.ctx, entity=node_orphan)

        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(3, len(events))
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(3, len(events))

        # two more events for cluster 1, with one for an orphan node
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=node1_1)
        self.create_event(self.ctx, entity=node_orphan)

        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(5, len(events))
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(3, len(events))

    def test_event_get_all_by_cluster_diff_project(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster2)

        new_ctx = utils.dummy_context(project='a-different-project')
        events = db_api.event_get_all_by_cluster(new_ctx, cluster1.id)
        self.assertEqual(0, len(events))
        events = db_api.event_get_all_by_cluster(new_ctx, cluster1.id,
                                                 project_safe=False)
        self.assertEqual(1, len(events))

    def test_event_get_all_by_cluster_admin_context(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)

        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        events = db_api.event_get_all_by_cluster(admin_ctx, cluster1.id,
                                                 project_safe=True)
        self.assertEqual(0, len(events))
        events = db_api.event_get_all_by_cluster(admin_ctx, cluster1.id,
                                                 project_safe=False)
        self.assertEqual(2, len(events))

    def test_event_count_all_by_cluster(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        node1_1 = shared.create_node(self.ctx, cluster1, self.profile)
        node_orphan = shared.create_node(self.ctx, None, self.profile)

        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)

        self.assertEqual(2, db_api.event_count_by_cluster(self.ctx,
                                                          cluster1.id))
        self.assertEqual(0, db_api.event_count_by_cluster(self.ctx,
                                                          cluster2.id))

        # No change if event is not related to a cluster
        self.create_event(self.ctx, entity=self.profile)

        self.assertEqual(2, db_api.event_count_by_cluster(self.ctx,
                                                          cluster1.id))
        self.assertEqual(0, db_api.event_count_by_cluster(self.ctx,
                                                          cluster2.id))

        # Node level events account to cluster
        self.create_event(self.ctx, entity=node1_1)
        self.assertEqual(3, db_api.event_count_by_cluster(self.ctx,
                                                          cluster1.id))
        self.assertEqual(0, db_api.event_count_by_cluster(self.ctx,
                                                          cluster2.id))

        # Node level events account to cluster, but not for orphan nodes
        self.create_event(self.ctx, entity=node_orphan)
        self.assertEqual(3, db_api.event_count_by_cluster(self.ctx,
                                                          cluster1.id))
        self.assertEqual(0, db_api.event_count_by_cluster(self.ctx,
                                                          cluster2.id))
        # Another cluster
        self.create_event(self.ctx, entity=cluster2)
        self.assertEqual(3, db_api.event_count_by_cluster(self.ctx,
                                                          cluster1.id))
        self.assertEqual(1, db_api.event_count_by_cluster(self.ctx,
                                                          cluster2.id))

    def test_event_count_all_by_cluster_diff_project(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster2)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.event_count_by_cluster(new_ctx, cluster1.id)
        self.assertEqual(0, res)
        res = db_api.event_count_by_cluster(new_ctx, cluster1.id,
                                            project_safe=False)
        self.assertEqual(1, res)

    def test_event_count_all_by_cluster_admin_context(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        self.create_event(self.ctx, entity=cluster1)

        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)

        res = db_api.event_count_by_cluster(admin_ctx, cluster1.id,
                                            project_safe=True)
        self.assertEqual(0, res)
        res = db_api.event_count_by_cluster(admin_ctx, cluster1.id,
                                            project_safe=False)
        self.assertEqual(1, res)

    def test_event_get_all_filtered(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster1')
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster2')

        self.create_event(self.ctx, entity=cluster1, action='CLUSTER_CREATE')
        self.create_event(self.ctx, entity=cluster1, action='CLUSTER_DELETE')
        self.create_event(self.ctx, entity=cluster2, action='CLUSTER_CREATE')

        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(2, len(events))

        # test filter by action
        filters = {'action': 'CLUSTER_CREATE'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 filters=filters)
        self.assertEqual(1, len(events))
        self.assertEqual('CLUSTER_CREATE', events[0].action)

        filters = {'action': 'CLUSTER_UPDATE'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 filters=filters)
        self.assertEqual(0, len(events))

        # test filter by oname
        filters = {'oname': 'cluster1'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 filters=filters)
        self.assertEqual(2, len(events))
        self.assertEqual('cluster1', events[0].oname)
        self.assertEqual('cluster1', events[1].oname)

        filters = {'oname': 'cluster3'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 filters=filters)
        self.assertEqual(0, len(events))

        # test filter by otype
        filters = {'otype': 'CLUSTER'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id,
                                                 filters=filters)
        self.assertEqual(1, len(events))
        self.assertEqual('CLUSTER', events[0].otype)

        filters = {'otype': 'NODE'}
        events = db_api.event_get_all_by_cluster(self.ctx, cluster2.id,
                                                 filters=filters)
        self.assertEqual(0, len(events))

        # test limit and marker
        events_all = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        marker = events_all[0].id
        expected = events_all[1].id
        events = db_api.event_get_all_by_cluster(self.ctx, cluster1.id,
                                                 limit=1, marker=marker)
        self.assertEqual(1, len(events))
        self.assertEqual(expected, events[0].id)

    def test_event_prune(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        node1_1 = shared.create_node(self.ctx, cluster1, self.profile)
        node_orphan = shared.create_node(self.ctx, None, self.profile)

        # prune 1: cluster events
        self.create_event(self.ctx, entity=cluster1)
        self.create_event(self.ctx, entity=cluster1)

        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(2, len(res))
        db_api.event_prune(self.ctx, cluster1.id)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(res))

        # prune 2: Node level events account to cluster
        self.create_event(self.ctx, entity=node1_1)

        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(res))
        db_api.event_prune(self.ctx, cluster1.id)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(res))

        # prune 3: Events related to orphan nodes
        # no impact here and no error given
        self.create_event(self.ctx, entity=node_orphan)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(res))
        db_api.event_prune(self.ctx, cluster1.id)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(res))

        # prune 4: Another cluster
        # no impact here and no error given
        self.create_event(self.ctx, entity=cluster2)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(res))
        db_api.event_prune(self.ctx, cluster1.id)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(res))

    def test_event_purge(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        node1_1 = shared.create_node(self.ctx, cluster1, self.profile)
        node1_2 = shared.create_node(self.ctx, cluster1, self.profile)

        self.create_event(self.ctx, entity=cluster1, status='start')
        self.create_event(self.ctx, entity=cluster1, status='end')
        self.create_event(self.ctx, entity=node1_1, status='start')
        self.create_event(self.ctx, entity=node1_1, status='end')
        timestamp = tu.utcnow()
        self.create_event(self.ctx, timestamp=timestamp,
                          entity=node1_2, status='start')

        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(5, len(res))
        db_api.event_purge(project=None, granularity='days', age=5)
        res = db_api.event_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(res))
