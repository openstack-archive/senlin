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
import json

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared

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
        cluster = db_api.cluster_get(self.ctx, self.cluster.id)
        self.assertEqual(0, cluster.size)
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)
        self.assertEqual('test_node_name', node.name)
        self.assertEqual(UUID1, node.physical_id)
        self.assertEqual(0, node.index)
        self.assertIsNone(node.role)
        self.assertIsNone(node.created_time)
        self.assertIsNone(node.updated_time)
        self.assertIsNone(node.deleted_time)
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('create complete', node.status_reason)
        self.assertEqual('{"foo": "123"}', json.dumps(node.tags))
        self.assertEqual('{"key1": "value1"}', json.dumps(node.data))
        self.assertEqual(self.cluster.id, node.cluster_id)
        self.assertEqual(self.profile.id, node.profile_id)

        cluster = db_api.cluster_get(self.ctx, self.cluster.id)
        self.assertEqual(1, cluster.size)

    def test_node_status_reason_truncate(self):
        node = shared.create_node(self.ctx, self.cluster, self.profile,
                                  status_reason='a' * 1024)
        ret_node = db_api.node_get(self.ctx, node.id)
        self.assertEqual('a' * 255, ret_node.status_reason)

    def test_node_get(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)

        node = db_api.node_get(self.ctx, UUID2)
        self.assertIsNone(node)

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
                               id=v, init_time=datetime.datetime.utcnow())

        nodes = db_api.node_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(nodes))

        nodes = db_api.node_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(nodes))

        nodes = db_api.node_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(nodes))

        nodes = db_api.node_get_all(self.ctx, marker='node1')
        self.assertEqual(0, len(nodes))

        nodes = db_api.node_get_all(self.ctx, marker='node2')
        self.assertEqual(1, len(nodes))

        nodes = db_api.node_get_all(self.ctx, marker='node3')
        self.assertEqual(2, len(nodes))

        nodes = db_api.node_get_all(self.ctx, limit=1, marker='node3')
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
        dt = datetime.datetime
        nodes = [shared.create_node(self.ctx, None, self.profile,
                                    init_time=dt.utcnow())
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

    def test_node_get_by_name_and_cluster(self):
        shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get_by_name_and_cluster(self.ctx,
                                                   'test_node_name',
                                                   self.cluster.id)

        self.assertIsNotNone(node)
        self.assertEqual('test_node_name', node.name)
        self.assertEqual(self.cluster.id, node.cluster_id)

        self.assertIsNone(db_api.node_get_by_name_and_cluster(self.ctx,
                                                              'abc',
                                                              self.cluster.id))

    def test_node_get_by_physical_id(self):
        shared.create_node(self.ctx, self.cluster, self.profile)

        node = db_api.node_get_by_physical_id(self.ctx, UUID1)
        self.assertIsNotNone(node)
        self.assertEqual(UUID1, node.physical_id)

        self.assertIsNone(db_api.node_get_by_physical_id(self.ctx, UUID2))

    def test_node_get_all_by_cluster(self):
        self.cluster1 = shared.create_cluster(self.ctx, self.profile)
        self.cluster2 = shared.create_cluster(self.ctx, self.profile)
        values = [
            {'name': 'node1', 'cluster_id': self.cluster.id},
            {'name': 'node2', 'cluster_id': self.cluster.id},
            {'name': 'node3', 'cluster_id': self.cluster1.id},
        ]
        [shared.create_node(self.ctx, self.cluster, self.profile, **v)
            for v in values]

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(2, len(nodes))
        self.assertEqual('node1', nodes[0].name)
        self.assertEqual('node2', nodes[1].name)

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster2.id)
        self.assertEqual(0, len(nodes))
