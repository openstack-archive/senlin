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

import json
import six

from oslo_utils import timeutils as tu

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPINodeTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPINodeTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)
        self.cluster = shared.create_cluster(self.ctx, self.profile)

    def test_node_create(self):
        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(0, len(nodes))
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)
        self.assertEqual('test_node_name', node.name)
        self.assertEqual(UUID1, node.physical_id)
        self.assertEqual(1, node.index)
        self.assertIsNone(node.role)
        self.assertIsNone(node.created_time)
        self.assertIsNone(node.updated_time)
        self.assertIsNone(node.deleted_time)
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('create complete', node.status_reason)
        self.assertEqual('{"foo": "123"}', json.dumps(node.metadata))
        self.assertEqual('{"key1": "value1"}', json.dumps(node.data))
        self.assertEqual(self.cluster.id, node.cluster_id)
        self.assertEqual(self.profile.id, node.profile_id)

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(1, len(nodes))

    def test_node_get(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)

        node = db_api.node_get(self.ctx, UUID2)
        self.assertIsNone(node)
        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(1, len(nodes))

    def test_node_get_diff_project(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)

        ctx_new = utils.dummy_context(project='a_different_project')
        node = db_api.node_get(ctx_new, res.id)
        self.assertIsNone(node)
        node = db_api.node_get(ctx_new, res.id, project_safe=False)
        self.assertIsNotNone(node)

    def test_node_get_show_deleted(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node_id = res.id
        node = db_api.node_get(self.ctx, node_id)
        self.assertIsNotNone(node)

        db_api.node_delete(self.ctx, node_id)

        node = db_api.node_get(self.ctx, node_id)
        self.assertIsNone(node)

        node = db_api.node_get(self.ctx, node_id, show_deleted=False)
        self.assertIsNone(node)

        node = db_api.node_get(self.ctx, node_id, show_deleted=True)
        self.assertEqual(node_id, node.id)

    def test_node_get_by_name(self):
        shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get_by_name(self.ctx, 'test_node_name')
        self.assertIsNotNone(node)
        self.assertEqual('test_node_name', node.name)
        self.assertEqual(self.cluster.id, node.cluster_id)

        res = db_api.node_get_by_name(self.ctx, 'BogusName')
        self.assertIsNone(res)

    def test_node_get_by_name_diff_project(self):
        shared.create_node(self.ctx, self.cluster, self.profile)
        res = db_api.node_get_by_name(self.ctx, 'test_node_name')
        self.assertIsNotNone(res)

        ctx_new = utils.dummy_context(project='a_different_project')
        res = db_api.node_get_by_name(ctx_new, 'test_node_name')
        self.assertIsNone(res)
        res = db_api.node_get_by_name(ctx_new, 'test_node_name',
                                      project_safe=False)
        self.assertIsNotNone(res)

    def test_node_get_by_name_show_deleted(self):
        node_name = 'test_node_name'
        shared.create_node(self.ctx, self.cluster, self.profile,
                           name=node_name)
        node = db_api.node_get_by_name(self.ctx, node_name)
        self.assertIsNotNone(node)

        node_id = node.id
        db_api.node_delete(self.ctx, node_id)

        res = db_api.node_get_by_name(self.ctx, node_name)
        self.assertIsNone(res)

        res = db_api.node_get_by_name(self.ctx, node_name, show_deleted=False)
        self.assertIsNone(res)

        res = db_api.node_get_by_name(self.ctx, node_name, show_deleted=True)
        self.assertEqual(node_id, res.id)

    def test_node_get_by_short_id(self):
        node_id1 = 'same-part-unique-part'
        node_id2 = 'same-part-part-unique'
        shared.create_node(self.ctx, None, self.profile,
                           id=node_id1, name='node-1')
        shared.create_node(self.ctx, None, self.profile,
                           id=node_id2, name='node-2')

        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.node_get_by_short_id,
                              self.ctx, node_id1[:x])

        res = db_api.node_get_by_short_id(self.ctx, node_id1[:11])
        self.assertEqual(node_id1, res.id)
        res = db_api.node_get_by_short_id(self.ctx, node_id2[:11])
        self.assertEqual(node_id2, res.id)
        res = db_api.node_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_node_get_by_short_id_diff_project(self):
        node_id = 'same-part-unique-part'
        shared.create_node(self.ctx, None, self.profile,
                           id=node_id, name='node-1')
        res = db_api.node_get_by_short_id(self.ctx, node_id[:11])
        self.assertIsNotNone(res)

        ctx_new = utils.dummy_context(project='a_different_project')
        res = db_api.node_get_by_short_id(ctx_new, node_id[:11])
        self.assertIsNone(res)
        res = db_api.node_get_by_short_id(ctx_new, node_id[:11],
                                          project_safe=False)
        self.assertIsNotNone(res)

    def test_node_get_by_short_id_show_deleted(self):
        node_id = 'this-is-a-unique-id'
        shared.create_node(self.ctx, None, self.profile, id=node_id)

        res = db_api.node_get_by_short_id(self.ctx, node_id[:5])
        self.assertEqual(node_id, res.id)
        res = db_api.node_get_by_short_id(self.ctx, node_id[:7])
        self.assertEqual(node_id, res.id)

        db_api.node_delete(self.ctx, node_id)

        res = db_api.node_get_by_short_id(self.ctx, node_id[:5])
        self.assertIsNone(res)
        res = db_api.node_get_by_short_id(self.ctx, node_id[:5],
                                          show_deleted=False)
        self.assertIsNone(res)
        res = db_api.node_get_by_short_id(self.ctx, node_id[:5],
                                          show_deleted=True)
        self.assertEqual(node_id, res.id)

    def test_node_get_all(self):
        values = [{'name': 'node1'}, {'name': 'node2'}, {'name': 'node3'}]
        [shared.create_node(self.ctx, None, self.profile, **v) for v in values]

        nodes = db_api.node_get_all(self.ctx)
        self.assertEqual(3, len(nodes))

        names = [node.name for node in nodes]
        [self.assertIn(val['name'], names) for val in values]

    def test_node_get_all_with_cluster_id(self):
        values = [{'name': 'node1'}, {'name': 'node2'}, {'name': 'node3'}]
        for v in values:
            shared.create_node(self.ctx, self.cluster, self.profile, **v)
        shared.create_node(self.ctx, None, self.profile, name='node0')

        nodes = db_api.node_get_all(self.ctx, cluster_id=self.cluster.id)
        self.assertEqual(3, len(nodes))

        names = [node.name for node in nodes]
        [self.assertIn(val['name'], names) for val in values]

    def test_node_get_all_show_deleted(self):
        values = [{'id': 'node1'}, {'id': 'node2'}, {'id': 'node3'}]
        for v in values:
            shared.create_node(self.ctx, self.cluster, self.profile, **v)

        db_api.node_delete(self.ctx, 'node2')

        nodes = db_api.node_get_all(self.ctx)
        self.assertEqual(2, len(nodes))

        nodes = db_api.node_get_all(self.ctx, show_deleted=False)
        self.assertEqual(2, len(nodes))

        nodes = db_api.node_get_all(self.ctx, show_deleted=True)
        self.assertEqual(3, len(nodes))

    def test_node_get_all_with_limit_marker(self):
        node_ids = ['node1', 'node2', 'node3']
        for v in node_ids:
            shared.create_node(self.ctx, self.cluster, self.profile,
                               id=v, init_time=tu.utcnow())

        nodes = db_api.node_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(nodes))

        nodes = db_api.node_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(nodes))

        nodes = db_api.node_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(nodes))

        nodes = db_api.node_get_all(self.ctx, marker='node1')
        self.assertEqual(2, len(nodes))

        nodes = db_api.node_get_all(self.ctx, marker='node2')
        self.assertEqual(1, len(nodes))

        nodes = db_api.node_get_all(self.ctx, marker='node3')
        self.assertEqual(0, len(nodes))

        nodes = db_api.node_get_all(self.ctx, limit=1, marker='node1')
        self.assertEqual(1, len(nodes))

    def test_node_get_all_used_sort_keys(self):
        node_ids = ['node1', 'node2', 'node3']
        for v in node_ids:
            shared.create_node(self.ctx, self.cluster, self.profile, id=v)

        mock_paginate = self.patchobject(db_api.utils, 'paginate_query')
        sort_keys = ['index', 'name', 'created_time', 'updated_time',
                     'deleted_time', 'status']

        db_api.node_get_all(self.ctx, sort_keys=sort_keys)
        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        expected_keys = set(['index', 'name', 'created_time', 'updated_time',
                             'deleted_time', 'status', 'id'])
        self.assertEqual(expected_keys, used_sort_keys)

    def test_node_get_all_sort_keys_wont_change(self):
        sort_keys = ['id']
        db_api.node_get_all(self.ctx, sort_keys=sort_keys)
        self.assertEqual(['id'], sort_keys)

    def test_node_get_all_sort_keys_and_dir(self):
        values = [{'id': '001', 'name': 'node1', 'status': 'ACTIVE'},
                  {'id': '002', 'name': 'node3', 'status': 'ERROR'},
                  {'id': '003', 'name': 'node2', 'status': 'UPDATING'}]
        for v in values:
            shared.create_node(self.ctx, self.cluster, self.profile, **v)

        nodes = db_api.node_get_all(self.ctx, sort_keys=['name', 'status'],
                                    sort_dir='asc')
        self.assertEqual(3, len(nodes))
        # Sorted by name
        self.assertEqual('001', nodes[0].id)
        self.assertEqual('003', nodes[1].id)
        self.assertEqual('002', nodes[2].id)

        nodes = db_api.node_get_all(self.ctx, sort_keys=['status', 'name'],
                                    sort_dir='asc')
        self.assertEqual(3, len(nodes))
        # Sorted by statuses (ascending)
        self.assertEqual('001', nodes[0].id)
        self.assertEqual('002', nodes[1].id)
        self.assertEqual('003', nodes[2].id)

        nodes = db_api.node_get_all(self.ctx, sort_keys=['status', 'name'],
                                    sort_dir='desc')
        self.assertEqual(3, len(nodes))
        # Sorted by statuses (descending)
        self.assertEqual('003', nodes[0].id)
        self.assertEqual('002', nodes[1].id)
        self.assertEqual('001', nodes[2].id)

    def test_node_get_all_default_sort_dir(self):
        nodes = [shared.create_node(self.ctx, None, self.profile,
                                    init_time=tu.utcnow())
                 for x in range(3)]

        results = db_api.node_get_all(self.ctx, sort_dir='asc')
        self.assertEqual(3, len(results))
        self.assertEqual(nodes[0].id, results[0].id)
        self.assertEqual(nodes[1].id, results[1].id)
        self.assertEqual(nodes[2].id, results[2].id)

    def test_node_get_all_with_filters(self):
        shared.create_node(self.ctx, None, self.profile, name='node1')
        shared.create_node(self.ctx, None, self.profile, name='node2')

        filters = {'name': ['node1', 'nodex']}
        results = db_api.node_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('node1', results[0]['name'])

        filters = {'name': 'node1'}
        results = db_api.node_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('node1', results[0]['name'])

    def test_node_get_all_with_empty_filters(self):
        shared.create_node(self.ctx, None, self.profile, name='node1')
        shared.create_node(self.ctx, None, self.profile, name='node2')

        filters = None
        results = db_api.node_get_all(self.ctx, filters=filters)
        self.assertEqual(2, len(results))

    def test_node_get_all_with_project_safe(self):
        shared.create_node(self.ctx, None, self.profile, name='node1')
        shared.create_node(self.ctx, None, self.profile, name='node2')

        self.ctx.project = 'a-different-project'
        results = db_api.node_get_all(self.ctx, project_safe=False)
        self.assertEqual(2, len(results))

        self.ctx.project = 'a-different-project'
        results = db_api.node_get_all(self.ctx)
        self.assertEqual(0, len(results))

        results = db_api.node_get_all(self.ctx, project_safe=True)
        self.assertEqual(0, len(results))

    def test_node_get_by_cluster(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)

        node0 = shared.create_node(self.ctx, None, self.profile)
        node1 = shared.create_node(self.ctx, self.cluster, self.profile)
        node2 = shared.create_node(self.ctx, self.cluster, self.profile)
        node3 = shared.create_node(self.ctx, cluster1, self.profile)

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(2, len(nodes))
        self.assertEqual(set([node1.id, node2.id]),
                         set([nodes[0].id, nodes[1].id]))

        nodes = db_api.node_get_all_by_cluster(self.ctx, None)
        self.assertEqual(1, len(nodes))
        self.assertEqual(node0.id, nodes[0].id)

        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(nodes))
        self.assertEqual(node3.id, nodes[0].id)

    def test_node_get_by_cluster_diff_project(self):
        shared.create_cluster(self.ctx, self.profile)

        node1 = shared.create_node(self.ctx, self.cluster, self.profile)
        node2 = shared.create_node(self.ctx, self.cluster, self.profile)

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(2, len(nodes))
        self.assertEqual(set([node1.id, node2.id]),
                         set([nodes[0].id, nodes[1].id]))

        ctx_new = utils.dummy_context(project='a_different_project')
        nodes = db_api.node_get_all_by_cluster(ctx_new, self.cluster.id)
        self.assertEqual(0, len(nodes))
        nodes = db_api.node_get_all_by_cluster(ctx_new, self.cluster.id,
                                               project_safe=False)
        self.assertEqual(2, len(nodes))

    def test_node_get_by_cluster_show_deleted(self):
        node0 = shared.create_node(self.ctx, self.cluster, self.profile)
        node1 = shared.create_node(self.ctx, self.cluster, self.profile)

        nodes = db_api.node_get_all_by_cluster(self.ctx,
                                               self.cluster.id)
        self.assertEqual(2, len(nodes))
        self.assertEqual(set([node0.id, node1.id]),
                         set([nodes[0].id, nodes[1].id]))

        db_api.node_delete(self.ctx, node1.id)
        nodes = db_api.node_get_all_by_cluster(self.ctx,
                                               self.cluster.id)
        self.assertEqual(1, len(nodes))
        self.assertEqual(node0.id, nodes[0].id)

        nodes = db_api.node_get_all_by_cluster(self.ctx,
                                               self.cluster.id,
                                               show_deleted=True)
        self.assertEqual(2, len(nodes))
        self.assertEqual(set([node0.id, node1.id]),
                         set([nodes[0].id, nodes[1].id]))

    def test_node_get_by_name_and_cluster(self):
        node_name = 'test_node_007'
        shared.create_node(self.ctx, self.cluster, self.profile,
                           name=node_name)
        node = db_api.node_get_by_name_and_cluster(self.ctx,
                                                   node_name,
                                                   self.cluster.id)
        self.assertIsNotNone(node)
        self.assertEqual(node_name, node.name)
        self.assertEqual(self.cluster.id, node.cluster_id)

        node = db_api.node_get_by_name_and_cluster(self.ctx, 'not-exist',
                                                   self.cluster.id)
        self.assertIsNone(node)

        node = db_api.node_get_by_name_and_cluster(self.ctx, node_name,
                                                   'BogusClusterID')
        self.assertIsNone(node)

    def test_node_get_by_name_and_cluster_diff_project(self):
        node_name = 'test_node_007'
        shared.create_node(self.ctx, self.cluster, self.profile,
                           name=node_name)
        node = db_api.node_get_by_name_and_cluster(self.ctx,
                                                   node_name,
                                                   self.cluster.id)
        self.assertIsNotNone(node)

        ctx_new = utils.dummy_context(project='a_different_project')
        node = db_api.node_get_by_name_and_cluster(ctx_new,
                                                   node_name,
                                                   self.cluster.id)
        self.assertIsNone(node)
        node = db_api.node_get_by_name_and_cluster(ctx_new,
                                                   node_name,
                                                   self.cluster.id,
                                                   project_safe=False)
        self.assertIsNotNone(node)

    def test_node_get_by_physical_id(self):
        shared.create_node(self.ctx, self.cluster, self.profile,
                           physical_id=UUID1)

        node = db_api.node_get_by_physical_id(self.ctx, UUID1)
        self.assertIsNotNone(node)
        self.assertEqual(UUID1, node.physical_id)

        node = db_api.node_get_by_physical_id(self.ctx, UUID2)
        self.assertIsNone(node)

    def test_node_get_by_physical_id_diff_project(self):
        shared.create_node(self.ctx, self.cluster, self.profile,
                           physical_id=UUID1)

        node = db_api.node_get_by_physical_id(self.ctx, UUID1)
        self.assertIsNotNone(node)
        self.assertEqual(UUID1, node.physical_id)

        ctx_new = utils.dummy_context(project='a_different_project')
        node = db_api.node_get_by_physical_id(ctx_new, UUID1)
        self.assertIsNone(node)
        node = db_api.node_get_by_physical_id(ctx_new, UUID1,
                                              project_safe=False)
        self.assertIsNotNone(node)

    def test_node_update(self):
        node = shared.create_node(self.ctx, self.cluster, self.profile)
        new_attributes = {
            'name': 'new node name',
            'status': 'bad status',
            'role': 'a new role',
        }
        db_api.node_update(self.ctx, node.id, new_attributes)

        node = db_api.node_get(self.ctx, node.id)
        self.assertEqual('new node name', node.name)
        self.assertEqual('bad status', node.status)
        self.assertEqual('a new role', node.role)

    def test_node_update_not_found(self):
        new_attributes = {'name': 'new_name'}
        ex = self.assertRaises(exception.NodeNotFound,
                               db_api.node_update,
                               self.ctx, 'BogusId', new_attributes)
        self.assertEqual('The node (BogusId) could not be found.',
                         six.text_type(ex))

    def test_node_update_cluster_status_updated(self):
        cluster = db_api.cluster_get(self.ctx, self.cluster.id)
        self.assertEqual('INIT', cluster.status)

        node = shared.create_node(self.ctx, self.cluster, self.profile)

        new_attributes = {
            'name': 'new_name',
            'status': 'ERROR',
            'status_reason': 'Something is wrong',
        }

        db_api.node_update(self.ctx, node.id, new_attributes)

        node = db_api.node_get(self.ctx, node.id)
        self.assertEqual('new_name', node.name)
        self.assertEqual('ERROR', node.status)
        self.assertEqual('Something is wrong', node.status_reason)

        cluster = db_api.cluster_get(self.ctx, self.cluster.id)
        self.assertEqual('WARNING', cluster.status)
        reason = 'Node new_name: Something is wrong'
        self.assertEqual(reason, cluster.status_reason)

    def test_node_migrate_from_none(self):
        node_orphan = shared.create_node(self.ctx, None, self.profile)
        timestamp = tu.utcnow()

        node = db_api.node_migrate(self.ctx, node_orphan.id, self.cluster.id,
                                   timestamp)
        cluster = db_api.cluster_get(self.ctx, self.cluster.id)
        self.assertEqual(timestamp, node.updated_time)
        self.assertEqual(self.cluster.id, node.cluster_id)
        self.assertEqual(2, cluster.next_index)
        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(1, len(nodes))

    def test_node_migrate_to_none(self):
        node = shared.create_node(self.ctx, self.cluster, self.profile)
        timestamp = tu.utcnow()

        node_new = db_api.node_migrate(self.ctx, node.id, None, timestamp)
        self.assertEqual(timestamp, node_new.updated_time)
        self.assertIsNone(node_new.cluster_id)
        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(0, len(nodes))

    def test_node_migrate_between_clusters(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)

        node = shared.create_node(self.ctx, cluster1, self.profile)
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(nodes))
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(0, len(nodes))
        self.assertEqual(2, cluster1.next_index)
        self.assertEqual(1, cluster2.next_index)

        timestamp = tu.utcnow()

        node_new = db_api.node_migrate(self.ctx, node.id, cluster2.id,
                                       timestamp)
        cluster1 = db_api.cluster_get(self.ctx, cluster1.id)
        cluster2 = db_api.cluster_get(self.ctx, cluster2.id)
        self.assertEqual(timestamp, node_new.updated_time)
        self.assertEqual(cluster2.id, node_new.cluster_id)
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(nodes))
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(1, len(nodes))
        self.assertEqual(2, cluster1.next_index)
        self.assertEqual(2, cluster2.next_index)

        # Migrate it back!
        timestamp = tu.utcnow()

        node_new = db_api.node_migrate(self.ctx, node.id, cluster1.id,
                                       timestamp)
        cluster1 = db_api.cluster_get(self.ctx, cluster1.id)
        cluster2 = db_api.cluster_get(self.ctx, cluster2.id)
        self.assertEqual(timestamp, node_new.updated_time)
        self.assertEqual(cluster1.id, node_new.cluster_id)
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(nodes))
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(0, len(nodes))
        self.assertEqual(3, cluster1.next_index)
        self.assertEqual(2, cluster2.next_index)

    def test_node_delete(self):
        node = shared.create_node(self.ctx, self.cluster, self.profile)
        node_id = node.id

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(1, len(nodes))

        db_api.node_delete(self.ctx, node_id)
        res = db_api.node_get(self.ctx, node_id)
        self.assertIsNone(res)

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(0, len(nodes))

    def test_node_delete_not_found(self):
        node_id = 'BogusNodeID'
        res = db_api.node_delete(self.ctx, node_id)
        self.assertIsNone(res)

        res = db_api.node_get(self.ctx, node_id)
        self.assertIsNone(res)
