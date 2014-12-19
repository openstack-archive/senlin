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

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared

UUID1=shared.UUID1
UUID2=shared.UUID2
UUID3=shared.UUID3


class DBAPINodeTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPINodeTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx, 'os.heat.stack')
        self.cluster = shared.create_cluster(self.ctx, self.profile)

    def test_node_create(self):
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

    def test_node_get(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)

        self.assertRaises(exception.NotFound, db_api.node_get,
                          self.ctx, UUID2)

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

    def test_node_get_all(self):
        values = [
            {'name': 'res1'},
            {'name': 'res2'},
            {'name': 'res3'},
        ]
        [shared.create_node(self.ctx, self.cluster, self.profile, **v)
            for v in values]

        nodes = db_api.node_get_all(self.ctx)
        self.assertEqual(3, len(nodes))

        names = [node.name for node in nodes]
        [self.assertIn(val['name'], names) for val in values]

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
        self.assertEqual('node1', nodes.get('node1').name)
        self.assertEqual('node2', nodes.get('node2').name)

        self.assertRaises(exception.NotFound, db_api.node_get_all_by_cluster,
                          self.ctx, self.cluster2.id)

    def test_node_status_reason_truncate(self):
        node = shared.create_node(self.ctx, self.cluster, self.profile,
                                  status_reason='a' * 1024)
        ret_node = db_api.node_get(self.ctx, node.id)
        self.assertEqual('a' * 255, ret_node.status_reason)
