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
from oslo_db.sqlalchemy import utils as sa_utils
from oslo_serialization import jsonutils
from oslo_utils import timeutils as tu
import six

from senlin.common import consts
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
        res = shared.create_node(self.ctx, self.cluster, self.profile)

        node = db_api.node_get(self.ctx, res.id)

        self.assertIsNotNone(node)
        self.assertEqual('test_node_name', node.name)
        self.assertEqual(UUID1, node.physical_id)
        self.assertEqual(1, node.index)
        self.assertIsNone(node.role)
        self.assertIsNone(node.created_at)
        self.assertIsNone(node.updated_at)
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('create complete', node.status_reason)
        self.assertEqual('{"foo": "123"}', jsonutils.dumps(node.meta_data))
        self.assertEqual('{"key1": "value1"}', jsonutils.dumps(node.data))
        self.assertEqual(self.cluster.id, node.cluster_id)
        self.assertEqual(self.profile.id, node.profile_id)

    def test_node_get(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)

        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)

        node = db_api.node_get(self.ctx, UUID2)
        self.assertIsNone(node)

    def test_node_get_diff_project(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get(self.ctx, res.id)
        self.assertIsNotNone(node)

        ctx_new = utils.dummy_context(project='a_different_project')
        node = db_api.node_get(ctx_new, res.id)
        self.assertIsNone(node)
        node = db_api.node_get(ctx_new, res.id, project_safe=False)
        self.assertIsNotNone(node)

    def test_node_get_with_admin_context(self):
        res = shared.create_node(self.ctx, self.cluster, self.profile)
        admin_ctx = utils.dummy_context(project='a_different_project',
                                        is_admin=True)
        node = db_api.node_get(admin_ctx, res.id, project_safe=True)
        self.assertIsNone(node)
        node = db_api.node_get(admin_ctx, res.id, project_safe=False)
        self.assertIsNotNone(node)

    def test_node_get_by_name(self):
        shared.create_node(self.ctx, self.cluster, self.profile)
        node = db_api.node_get_by_name(self.ctx, 'test_node_name')
        self.assertIsNotNone(node)
        self.assertEqual('test_node_name', node.name)
        self.assertEqual(self.cluster.id, node.cluster_id)

        res = db_api.node_get_by_name(self.ctx, 'BogusName')
        self.assertIsNone(res)

        # duplicated name
        shared.create_node(self.ctx, self.cluster, self.profile)
        self.assertRaises(exception.MultipleChoices,
                          db_api.node_get_by_name,
                          self.ctx, 'test_node_name')

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

    def test_node_get_by_short_id_admin_context(self):
        node_id = 'same-part-unique-part'
        shared.create_node(self.ctx, None, self.profile,
                           id=node_id, name='node-1')

        admin_ctx = utils.dummy_context(project='a_different_project',
                                        is_admin=True)
        res = db_api.node_get_by_short_id(admin_ctx, node_id[:11],
                                          project_safe=True)
        self.assertIsNone(res)
        res = db_api.node_get_by_short_id(admin_ctx, node_id[:11],
                                          project_safe=False)
        self.assertIsNotNone(res)

    def test_node_get_all(self):
        values = [{'name': 'node1'}, {'name': 'node2'}, {'name': 'node3'}]
        [shared.create_node(self.ctx, None, self.profile, **v) for v in values]

        nodes = db_api.node_get_all(self.ctx)
        self.assertEqual(3, len(nodes))

        names = [node.name for node in nodes]
        [self.assertIn(val['name'], names) for val in values]

    def test_node_add_node_dependents(self):
        node_id = 'host_node'
        node = shared.create_node(self.ctx, None, self.profile,
                                  id=node_id, name='node-1')
        db_api.node_add_dependents(self.ctx, node_id, 'NODE1')
        node = db_api.node_get(self.ctx, node_id)
        nodes = node.dependents['nodes']
        self.assertEqual(['NODE1'], nodes)

        db_api.node_add_dependents(self.ctx, node_id, 'NODE2')
        new_node = db_api.node_get(self.ctx, node_id)
        nodes = new_node.dependents['nodes']
        self.assertEqual(['NODE1', 'NODE2'], nodes)

    def test_node_add_profile_dependents(self):
        node_id = 'host_node'
        new_profile = shared.create_profile(self.ctx)
        node = shared.create_node(self.ctx, None, self.profile,
                                  id=node_id, name='node-1')
        db_api.node_add_dependents(self.ctx, node_id, new_profile.id,
                                   'profile')
        node = db_api.node_get(self.ctx, node_id)
        nodes = node.dependents['profiles']
        self.assertEqual([new_profile.id], nodes)

        new_profile_1 = shared.create_profile(self.ctx)
        db_api.node_add_dependents(self.ctx, node_id, new_profile_1.id,
                                   'profile')
        new_node = db_api.node_get(self.ctx, node_id)
        nodes = new_node.dependents['profiles']
        self.assertEqual([new_profile.id, new_profile_1.id], nodes)

    def test_node_remove_node_dependents(self):
        node_id = 'host_node'
        dependents = {'nodes': ['NODE1', 'NODE2']}
        node = shared.create_node(self.ctx, None, self.profile,
                                  id=node_id, dependents=dependents)
        db_api.node_remove_dependents(self.ctx, node_id, 'NODE1')
        node = db_api.node_get(self.ctx, node_id)
        dependents = node.dependents
        self.assertEqual({'nodes': ['NODE2']}, dependents)

        db_api.node_remove_dependents(self.ctx, node_id, 'NODE2', 'node')
        node = db_api.node_get(self.ctx, node_id)
        dependents = node.dependents
        self.assertEqual({}, dependents)

    def test_node_remove_profile_dependents(self):
        node_id = 'host_node'
        dependents = {'profiles': ['P1', 'P2']}
        node = shared.create_node(self.ctx, None, self.profile,
                                  id=node_id, dependents=dependents)
        db_api.node_remove_dependents(self.ctx, node_id, 'P1', 'profile')
        node = db_api.node_get(self.ctx, node_id)
        dependents = node.dependents
        self.assertEqual({'profiles': ['P2']}, dependents)

        db_api.node_remove_dependents(self.ctx, node_id, 'P2', 'profile')
        node = db_api.node_get(self.ctx, node_id)
        dependents = node.dependents
        self.assertEqual({}, dependents)

    def test_node_get_all_with_cluster_id(self):
        values = [{'name': 'node1'}, {'name': 'node2'}, {'name': 'node3'}]
        for v in values:
            shared.create_node(self.ctx, self.cluster, self.profile, **v)
        shared.create_node(self.ctx, None, self.profile, name='node0')

        nodes = db_api.node_get_all(self.ctx, cluster_id=self.cluster.id)
        self.assertEqual(3, len(nodes))

        names = [node.name for node in nodes]
        [self.assertIn(val['name'], names) for val in values]

    def test_node_get_all_with_limit_marker(self):
        node_ids = ['node1', 'node2', 'node3']
        for v in node_ids:
            shared.create_node(self.ctx, self.cluster, self.profile,
                               id=v, init_at=tu.utcnow(True))

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

    @mock.patch.object(sa_utils, 'paginate_query')
    def test_node_get_all_used_sort_keys(self, mock_paginate):
        node_ids = ['node1', 'node2', 'node3']
        for v in node_ids:
            shared.create_node(self.ctx, self.cluster, self.profile, id=v)

        sort = ','.join(consts.NODE_SORT_KEYS)

        db_api.node_get_all(self.ctx, sort=sort)
        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        sort_keys = consts.NODE_SORT_KEYS
        sort_keys.append('id')
        expected_keys = set(sort_keys)
        self.assertEqual(expected_keys, used_sort_keys)

    def test_node_get_all_sorting(self):
        values = [{'id': '001', 'name': 'node1', 'status': 'ACTIVE'},
                  {'id': '002', 'name': 'node3', 'status': 'ERROR'},
                  {'id': '003', 'name': 'node2', 'status': 'UPDATING'}]
        for v in values:
            shared.create_node(self.ctx, self.cluster, self.profile, **v)

        nodes = db_api.node_get_all(self.ctx, sort='name,status')
        self.assertEqual(3, len(nodes))
        # Sorted by name
        self.assertEqual('001', nodes[0].id)
        self.assertEqual('003', nodes[1].id)
        self.assertEqual('002', nodes[2].id)

        nodes = db_api.node_get_all(self.ctx, sort='status,name')
        self.assertEqual(3, len(nodes))
        # Sorted by statuses (ascending)
        self.assertEqual('001', nodes[0].id)
        self.assertEqual('002', nodes[1].id)
        self.assertEqual('003', nodes[2].id)

        nodes = db_api.node_get_all(self.ctx, sort='status:desc,name:desc')
        self.assertEqual(3, len(nodes))
        # Sorted by statuses (descending)
        self.assertEqual('003', nodes[0].id)
        self.assertEqual('002', nodes[1].id)
        self.assertEqual('001', nodes[2].id)

    def test_node_get_all_default_sorting(self):
        nodes = [shared.create_node(self.ctx, None, self.profile,
                                    init_at=tu.utcnow(True))
                 for x in range(3)]

        results = db_api.node_get_all(self.ctx)
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

        self.ctx.project_id = 'a-different-project'
        results = db_api.node_get_all(self.ctx, project_safe=False)
        self.assertEqual(2, len(results))

        self.ctx.project_id = 'a-different-project'
        results = db_api.node_get_all(self.ctx)
        self.assertEqual(0, len(results))

        results = db_api.node_get_all(self.ctx, project_safe=True)
        self.assertEqual(0, len(results))

    def test_node_get_all_with_admin_context(self):
        shared.create_node(self.ctx, None, self.profile, name='node1')
        shared.create_node(self.ctx, None, self.profile, name='node2')

        admin_ctx = utils.dummy_context(project='a_different_project',
                                        is_admin=True)
        results = db_api.node_get_all(admin_ctx, project_safe=True)
        self.assertEqual(0, len(results))
        results = db_api.node_get_all(admin_ctx, project_safe=False)
        self.assertEqual(2, len(results))

    def test_get_all_by_cluster(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)

        node0 = shared.create_node(self.ctx, None, self.profile)
        node1 = shared.create_node(self.ctx, self.cluster, self.profile)
        node2 = shared.create_node(self.ctx, self.cluster, self.profile)
        node3 = shared.create_node(self.ctx, cluster1, self.profile)

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(2, len(nodes))
        self.assertEqual(set([node1.id, node2.id]),
                         set([nodes[0].id, nodes[1].id]))

        # retrieve orphan nodes
        nodes = db_api.node_get_all_by_cluster(self.ctx, '')
        self.assertEqual(1, len(nodes))
        self.assertEqual(node0.id, nodes[0].id)

        # retrieve all nodes
        nodes = db_api.node_get_all_by_cluster(self.ctx, None)
        self.assertEqual(4, len(nodes))
        self.assertEqual(node0.id, nodes[0].id)

        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(1, len(nodes))
        self.assertEqual(node3.id, nodes[0].id)

    def test_get_all_by_cluster_with_filters(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)

        shared.create_node(self.ctx, None, self.profile, role="slave")
        node1 = shared.create_node(self.ctx, self.cluster, self.profile,
                                   role="slave")
        shared.create_node(self.ctx, self.cluster, self.profile, role="master")
        shared.create_node(self.ctx, cluster1, self.profile, role="unknown")

        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id,
                                               filters={"role": ["slave"]})
        self.assertEqual(1, len(nodes))
        self.assertEqual(node1.id, nodes[0].id)

        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id,
                                               filters={"role": "master"})
        self.assertEqual(0, len(nodes))

    def test_get_all_by_cluster_diff_project(self):
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

    def test_get_all_by_cluster_admin_context(self):
        shared.create_cluster(self.ctx, self.profile)

        node1 = shared.create_node(self.ctx, self.cluster, self.profile)
        node2 = shared.create_node(self.ctx, self.cluster, self.profile)

        admin_ctx = utils.dummy_context(project='a_different_project',
                                        is_admin=True)
        nodes = db_api.node_get_all_by_cluster(admin_ctx, self.cluster.id)
        self.assertEqual(0, len(nodes))
        nodes = db_api.node_get_all_by_cluster(admin_ctx, self.cluster.id,
                                               project_safe=False)
        self.assertEqual(2, len(nodes))
        self.assertEqual(set([node1.id, node2.id]),
                         set([nodes[0].id, nodes[1].id]))

    def test_node_count_by_cluster(self):
        shared.create_cluster(self.ctx, self.profile)

        shared.create_node(self.ctx, self.cluster, self.profile)
        shared.create_node(self.ctx, self.cluster, self.profile)

        res = db_api.node_count_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(2, res)

    def test_node_count_by_cluster_with_filters(self):
        shared.create_cluster(self.ctx, self.profile)

        shared.create_node(self.ctx, self.cluster, self.profile,
                           status='ACTIVE')
        shared.create_node(self.ctx, self.cluster, self.profile,
                           status='ERROR')

        res = db_api.node_count_by_cluster(self.ctx, self.cluster.id,
                                           status='ACTIVE')
        self.assertEqual(1, res)
        res = db_api.node_count_by_cluster(self.ctx, self.cluster.id,
                                           status='ERROR')
        self.assertEqual(1, res)

    def test_node_count_by_cluster_diff_project(self):
        ctx_new = utils.dummy_context(project='a_different_project')
        shared.create_cluster(self.ctx, self.profile)

        shared.create_node(self.ctx, self.cluster, self.profile)
        shared.create_node(self.ctx, self.cluster, self.profile)

        res = db_api.node_count_by_cluster(ctx_new, self.cluster.id)
        self.assertEqual(0, res)

        res = db_api.node_count_by_cluster(ctx_new, self.cluster.id,
                                           project_safe=False)
        self.assertEqual(2, res)

    def test_node_count_by_cluster_admin_context(self):
        shared.create_cluster(self.ctx, self.profile)
        shared.create_node(self.ctx, self.cluster, self.profile)
        shared.create_node(self.ctx, self.cluster, self.profile)

        admin_ctx = utils.dummy_context(project='a_different_project',
                                        is_admin=True)
        res = db_api.node_count_by_cluster(admin_ctx, self.cluster.id,
                                           project_safe=True)
        self.assertEqual(0, res)
        res = db_api.node_count_by_cluster(admin_ctx, self.cluster.id,
                                           project_safe=False)
        self.assertEqual(2, res)

    def test_ids_by_cluster(self):
        node0 = shared.create_node(self.ctx, None, self.profile)
        node1 = shared.create_node(self.ctx, self.cluster, self.profile)
        node2 = shared.create_node(self.ctx, self.cluster, self.profile)

        results = db_api.node_ids_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(2, len(results))
        self.assertEqual(set([node1.id, node2.id]), set(results))

        # retrieve orphan nodes
        results = db_api.node_ids_by_cluster(self.ctx, '')
        self.assertEqual(1, len(results))
        self.assertEqual(node0.id, results[0])

    def test_ids_by_cluster_with_filters(self):
        node0 = shared.create_node(self.ctx, None, self.profile,
                                   role='slave')
        node1 = shared.create_node(self.ctx, self.cluster, self.profile,
                                   role='master')
        shared.create_node(self.ctx, self.cluster, self.profile)

        results = db_api.node_ids_by_cluster(self.ctx, self.cluster.id,
                                             filters={'role': 'master'})
        self.assertEqual(1, len(results))
        self.assertEqual(node1.id, results[0])

        # retrieve orphan nodes
        results = db_api.node_ids_by_cluster(self.ctx, '')
        self.assertEqual(1, len(results))
        self.assertEqual(node0.id, results[0])

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
        ex = self.assertRaises(exception.ResourceNotFound,
                               db_api.node_update,
                               self.ctx, 'BogusId', new_attributes)
        self.assertEqual("The node 'BogusId' could not be found.",
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
        timestamp = tu.utcnow(True)

        node = db_api.node_migrate(self.ctx, node_orphan.id, self.cluster.id,
                                   timestamp, 'NEW-ROLE')
        cluster = db_api.cluster_get(self.ctx, self.cluster.id)
        self.assertEqual(timestamp, node.updated_at)
        self.assertEqual(self.cluster.id, node.cluster_id)
        self.assertEqual(2, cluster.next_index)
        nodes = db_api.node_get_all_by_cluster(self.ctx, self.cluster.id)
        self.assertEqual(1, len(nodes))
        self.assertEqual('NEW-ROLE', nodes[0].role)

    def test_node_migrate_to_none(self):
        node = shared.create_node(self.ctx, self.cluster, self.profile)
        timestamp = tu.utcnow(True)

        node_new = db_api.node_migrate(self.ctx, node.id, None, timestamp)
        self.assertEqual(timestamp, node_new.updated_at)
        self.assertEqual('', node_new.cluster_id)
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
        # Refresh cluster1 and cluster2
        cluster1 = db_api.cluster_get(self.ctx, cluster1.id)
        cluster2 = db_api.cluster_get(self.ctx, cluster2.id)
        self.assertEqual(2, cluster1.next_index)
        self.assertEqual(1, cluster2.next_index)

        timestamp = tu.utcnow(True)

        node_new = db_api.node_migrate(self.ctx, node.id, cluster2.id,
                                       timestamp)
        cluster1 = db_api.cluster_get(self.ctx, cluster1.id)
        cluster2 = db_api.cluster_get(self.ctx, cluster2.id)
        self.assertEqual(timestamp, node_new.updated_at)
        self.assertEqual(cluster2.id, node_new.cluster_id)
        self.assertIsNone(node_new.role)
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster1.id)
        self.assertEqual(0, len(nodes))
        nodes = db_api.node_get_all_by_cluster(self.ctx, cluster2.id)
        self.assertEqual(1, len(nodes))
        self.assertEqual(2, cluster1.next_index)
        self.assertEqual(2, cluster2.next_index)

        # Migrate it back!
        timestamp = tu.utcnow(True)

        node_new = db_api.node_migrate(self.ctx, node.id, cluster1.id,
                                       timestamp, 'FAKE-ROLE')
        cluster1 = db_api.cluster_get(self.ctx, cluster1.id)
        cluster2 = db_api.cluster_get(self.ctx, cluster2.id)
        self.assertEqual(timestamp, node_new.updated_at)
        self.assertEqual(cluster1.id, node_new.cluster_id)
        self.assertEqual('FAKE-ROLE', node_new.role)
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
