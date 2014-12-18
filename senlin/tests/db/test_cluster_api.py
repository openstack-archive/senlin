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

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPIClusterTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIClusterTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx, 'os.heat.stack')

    def test_cluster_create(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        self.assertIsNotNone(cluster.id)
        self.assertEqual('db_test_cluster_name', cluster.name)
        self.assertEqual(self.profile.id, cluster.profile_id)
        self.assertEqual(self.ctx.username, cluster.user)
        self.assertEqual(self.ctx.tenant_id, cluster.project)
        self.assertEqual('unknown', cluster.domain)
        self.assertIsNone(cluster.parent)
        self.assertEqual(0, cluster.next_index)
        self.assertEqual('60', cluster.timeout)
        self.assertEqual('INIT', cluster.status)
        self.assertEqual('Just Initialized', cluster.status_reason)
        self.assertFalse({}, cluster.tags)

    def test_cluster_delete(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        cluster_id = cluster.id
        node = shared.create_node(self.ctx, cluster, self.profile)
        db_api.cluster_delete(self.ctx, cluster_id)

        self.assertIsNone(db_api.cluster_get(self.ctx, cluster_id,
                                             show_deleted=False))
        self.assertRaises(exception.NotFound, db_api.node_get,
                          self.ctx, node.id)
        self.assertRaises(exception.NotFound, db_api.cluster_delete,
                          self.ctx, cluster_id)

        # Testing soft delete
        ret_cluster = db_api.cluster_get(self.ctx, cluster_id,
                                         show_deleted=True)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster_id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

        # Testing child nodes deletion
        self.assertRaises(exception.NotFound,
                          db_api.node_get, self.ctx, node.id)

    def test_cluster_update(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        values = {
            'name': 'db_test_cluster_name2',
            'status': 'ERROR',
            'status_reason': "update failed",
            'timeout': '90',
        }
        db_api.cluster_update(self.ctx, cluster.id, values)
        cluster = db_api.cluster_get(self.ctx, cluster.id)
        self.assertEqual('db_test_cluster_name2', cluster.name)
        self.assertEqual('ERROR', cluster.status)
        self.assertEqual('update failed', cluster.status_reason)
        self.assertEqual('90', cluster.timeout)

        self.assertRaises(exception.NotFound, db_api.cluster_update, self.ctx,
                          UUID2, values)

    def test_cluster_get_returns_a_cluster(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        ret_cluster = db_api.cluster_get(self.ctx, cluster.id,
                                         show_deleted=False)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

    def test_cluster_get_returns_none_if_cluster_does_not_exist(self):
        cluster = db_api.cluster_get(self.ctx, UUID1, show_deleted=False)
        self.assertIsNone(cluster)

    def test_cluster_get_returns_none_if_tenant_id_does_not_match(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        self.ctx.tenant_id = 'abc'
        cluster = db_api.cluster_get(self.ctx, UUID1, show_deleted=False)
        self.assertIsNone(cluster)

    def test_cluster_get_can_return_a_cluster_from_different_tenant(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        self.ctx.tenant_id = 'abc'
        ret_cluster = db_api.cluster_get(self.ctx, cluster.id,
                                         show_deleted=False, tenant_safe=False)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

    def test_cluster_get_by_name(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        ret_cluster = db_api.cluster_get_by_name(self.ctx, cluster.name)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

        self.assertIsNone(db_api.cluster_get_by_name(self.ctx, 'abc'))

        self.ctx.tenant_id = 'abc'
        self.assertIsNone(db_api.cluster_get_by_name(self.ctx, 'abc'))

    def test_cluster_get_all(self):
        values = [
            {'name': 'cluster1'},
            {'name': 'cluster2'},
            {'name': 'cluster3'},
            {'name': 'cluster4'}
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        ret_clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(4, len(ret_clusters))
        names = [ret_cluster.name for ret_cluster in ret_clusters]
        [self.assertIn(val['name'], names) for val in values]

    def test_cluster_get_all_by_parent(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile)
        cluster2 = shared.create_cluster(self.ctx, self.profile)
        values = [
            {'parent': cluster1.id},
            {'parent': cluster1.id},
            {'parent': cluster2.id},
            {'parent': cluster2.id},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        cluster1_children = db_api.cluster_get_all_by_parent(self.ctx,
                                                             cluster1.id)
        self.assertEqual(2, len(cluster1_children))
        cluster2_children = db_api.cluster_get_all_by_parent(self.ctx,
                                                             cluster2.id)
        self.assertEqual(2, len(cluster2_children))

    def test_cluster_get_all_with_regular_tenant(self):
        values = [
            {'tenant_id': UUID1},
            {'tenant_id': UUID1},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.ctx.tenant_id = UUID1
        clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(2, len(clusters))

        self.ctx.tenant_id = UUID2
        clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(3, len(clusters))

        self.ctx.tenant_id = UUID3
        self.assertEqual([], db_api.cluster_get_all(self.ctx))

    def test_cluster_get_all_with_tenant_safe_false(self):
        values = [
            {'tenant_id': UUID1},
            {'tenant_id': UUID1},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        clusters = db_api.cluster_get_all(self.ctx, tenant_safe=False)
        self.assertEqual(5, len(clusters))

    def test_cluster_count_all_with_regular_tenant(self):
        values = [
            {'tenant_id': UUID1},
            {'tenant_id': UUID1},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.ctx.tenant_id = UUID1
        self.assertEqual(2, db_api.cluster_count_all(self.ctx))

        self.ctx.tenant_id = UUID2
        self.assertEqual(3, db_api.cluster_count_all(self.ctx))

    def test_cluster_count_all_with_tenant_safe_false(self):
        values = [
            {'tenant_id': UUID1},
            {'tenant_id': UUID1},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
            {'tenant_id': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.assertEqual(5, db_api.cluster_count_all(self.ctx,
                                                     tenant_safe=False))

    def _deleted_cluster_existance(self, ctx, clusters, existing, deleted):
        for s in existing:
            self.assertIsNotNone(db_api.cluster_get(ctx, clusters[s].id,
                                                    show_deleted=True))
        for s in deleted:
            self.assertIsNone(db_api.cluster_get(ctx, clusters[s].id,
                                                 show_deleted=True))

    def test_cluster_status_reason_truncate(self):
        cluster = shared.create_cluster(self.ctx, self.profile,
                                        status_reason='a' * 1024)
        self.assertEqual('a' * 255, cluster.status_reason)
