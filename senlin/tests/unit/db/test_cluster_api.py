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
from oslo_utils import timeutils as tu

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPIClusterTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIClusterTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)

    def test_cluster_create(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        self.assertIsNotNone(cluster.id)
        self.assertEqual('db_test_cluster_name', cluster.name)
        self.assertEqual(self.profile.id, cluster.profile_id)
        self.assertEqual(self.ctx.user_id, cluster.user)
        self.assertEqual(self.ctx.project_id, cluster.project)
        self.assertEqual('unknown', cluster.domain)
        self.assertIsNone(cluster.parent)
        self.assertEqual(1, cluster.next_index)
        self.assertEqual(60, cluster.timeout)
        self.assertEqual(0, cluster.desired_capacity)
        self.assertEqual('INIT', cluster.status)
        self.assertEqual('Just Initialized', cluster.status_reason)
        self.assertIsNone(cluster.created_at)
        self.assertIsNone(cluster.updated_at)
        self.assertIsNotNone(cluster.init_at)
        self.assertEqual({}, cluster.meta_data)
        self.assertIsNone(cluster.data)
        self.assertEqual({}, cluster.config)

    def test_cluster_get_returns_a_cluster(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        ret_cluster = db_api.cluster_get(self.ctx, cluster.id)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

    def test_cluster_get_not_found(self):
        cluster = db_api.cluster_get(self.ctx, UUID1)
        self.assertIsNone(cluster)

    def test_cluster_get_from_different_project(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        self.ctx.project_id = 'abc'
        ret_cluster = db_api.cluster_get(self.ctx, cluster.id,
                                         project_safe=False)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

        cluster = db_api.cluster_get(self.ctx, cluster.id)
        self.assertIsNone(cluster)

    def test_cluster_get_with_admin_context(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        admin_ctx = utils.dummy_context(project='another-project',
                                        is_admin=True)
        ret_cluster = db_api.cluster_get(admin_ctx, cluster.id,
                                         project_safe=True)
        self.assertIsNone(ret_cluster)
        ret_cluster = db_api.cluster_get(admin_ctx, cluster.id,
                                         project_safe=False)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

    def test_cluster_get_by_name(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        ret_cluster = db_api.cluster_get_by_name(self.ctx, cluster.name)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

        self.assertIsNone(db_api.cluster_get_by_name(self.ctx, 'abc'))

        self.ctx.project_id = 'abc'
        self.assertIsNone(db_api.cluster_get_by_name(self.ctx, cluster.name))

    def test_cluster_get_by_name_diff_project(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster_A',
                                         project=UUID2)

        shared.create_cluster(self.ctx, self.profile, name='cluster_B',
                              project=UUID2)
        shared.create_cluster(self.ctx, self.profile, name='cluster_B',
                              project=UUID2)

        res = db_api.cluster_get_by_name(self.ctx, 'cluster_A')
        self.assertIsNone(res)

        self.ctx.project_id = UUID3
        self.assertIsNone(db_api.cluster_get_by_name(self.ctx,
                                                     'cluster_A'))

        self.ctx.project_id = UUID2
        res = db_api.cluster_get_by_name(self.ctx, 'cluster_A')
        self.assertEqual(cluster1.id, res.id)

        self.assertRaises(exception.MultipleChoices,
                          db_api.cluster_get_by_name,
                          self.ctx, 'cluster_B')

        res = db_api.cluster_get_by_name(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_cluster_get_by_short_id(self):
        cid1 = 'same-part-unique-part'
        cid2 = 'same-part-part-unique'
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         id=cid1,
                                         name='cluster-1')

        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         id=cid2,
                                         name='cluster-2')
        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.cluster_get_by_short_id,
                              self.ctx, cid1[:x])

        res = db_api.cluster_get_by_short_id(self.ctx, cid1[:11])
        self.assertEqual(cluster1.id, res.id)
        res = db_api.cluster_get_by_short_id(self.ctx, cid2[:11])
        self.assertEqual(cluster2.id, res.id)
        res = db_api.cluster_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

        ctx_new = utils.dummy_context(project='different_project_id')
        res = db_api.cluster_get_by_short_id(ctx_new, cid1[:11])
        self.assertIsNone(res)

    def test_cluster_get_by_short_id_diff_project(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         id=UUID1,
                                         name='cluster-1')

        res = db_api.cluster_get_by_short_id(self.ctx, UUID1[:11])
        self.assertEqual(cluster1.id, res.id)

        ctx_new = utils.dummy_context(project='different_project_id')
        res = db_api.cluster_get_by_short_id(ctx_new, UUID1[:11])
        self.assertIsNone(res)

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

    def test_cluster_get_all_with_regular_project(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.ctx.project_id = UUID1
        clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(2, len(clusters))

        self.ctx.project_id = UUID2
        clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(3, len(clusters))

        self.ctx.project_id = UUID3
        self.assertEqual([], db_api.cluster_get_all(self.ctx))

    def test_cluster_get_all_with_project_safe_false(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        clusters = db_api.cluster_get_all(self.ctx, project_safe=False)
        self.assertEqual(5, len(clusters))

    def test_cluster_get_all_with_admin_context(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        admin_ctx = utils.dummy_context(project='another-project',
                                        is_admin=True)
        clusters = db_api.cluster_get_all(admin_ctx, project_safe=True)
        self.assertEqual(0, len(clusters))
        clusters = db_api.cluster_get_all(admin_ctx, project_safe=False)
        self.assertEqual(5, len(clusters))

    def test_cluster_get_all_with_filters(self):
        shared.create_cluster(self.ctx, self.profile, name='foo')
        shared.create_cluster(self.ctx, self.profile, name='bar')

        filters = {'name': ['bar', 'quux']}
        results = db_api.cluster_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('bar', results[0]['name'])

        filters = {'name': 'foo'}
        results = db_api.cluster_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('foo', results[0]['name'])

    def test_cluster_get_all_returns_all_if_no_filters(self):
        shared.create_cluster(self.ctx, self.profile)
        shared.create_cluster(self.ctx, self.profile)

        filters = None
        results = db_api.cluster_get_all(self.ctx, filters=filters)

        self.assertEqual(2, len(results))

    def test_cluster_get_all_default_sort_dir(self):
        clusters = [shared.create_cluster(self.ctx, self.profile,
                                          init_at=tu.utcnow(True))
                    for x in range(3)]

        st_db = db_api.cluster_get_all(self.ctx)
        self.assertEqual(3, len(st_db))
        self.assertEqual(clusters[0].id, st_db[0].id)
        self.assertEqual(clusters[1].id, st_db[1].id)
        self.assertEqual(clusters[2].id, st_db[2].id)

    def test_cluster_get_all_str_sort_keys(self):
        clusters = [shared.create_cluster(self.ctx, self.profile,
                                          created_at=tu.utcnow(True))
                    for x in range(3)]

        st_db = db_api.cluster_get_all(self.ctx, sort='created_at')
        self.assertEqual(3, len(st_db))
        self.assertEqual(clusters[0].id, st_db[0].id)
        self.assertEqual(clusters[1].id, st_db[1].id)
        self.assertEqual(clusters[2].id, st_db[2].id)

    @mock.patch.object(sa_utils, 'paginate_query')
    def test_cluster_get_all_filters_sort_keys(self, mock_paginate):
        sort = 'name,status,created_at,updated_at'
        db_api.cluster_get_all(self.ctx, sort=sort)

        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        expected_keys = set(['name', 'status', 'created_at',
                             'updated_at', 'id'])
        self.assertEqual(expected_keys, used_sort_keys)

    def test_cluster_get_all_marker(self):
        clusters = [shared.create_cluster(self.ctx, self.profile,
                                          created_at=tu.utcnow(True))
                    for x in range(3)]
        cl_db = db_api.cluster_get_all(self.ctx, marker=clusters[1].id)
        self.assertEqual(1, len(cl_db))
        self.assertEqual(clusters[2].id, cl_db[0].id)

    def test_cluster_get_all_non_existing_marker(self):
        [shared.create_cluster(self.ctx, self.profile) for x in range(3)]
        uuid = "this cluster doesn't exist"
        st_db = db_api.cluster_get_all(self.ctx, marker=uuid)
        self.assertEqual(3, len(st_db))

    def test_cluster_next_index(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        cluster_id = cluster.id
        res = db_api.cluster_get(self.ctx, cluster_id)
        self.assertEqual(1, res.next_index)
        res = db_api.cluster_next_index(self.ctx, cluster_id)
        self.assertEqual(1, res)
        res = db_api.cluster_get(self.ctx, cluster_id)
        self.assertEqual(2, res.next_index)
        res = db_api.cluster_next_index(self.ctx, cluster_id)
        self.assertEqual(2, res)
        res = db_api.cluster_get(self.ctx, cluster_id)
        self.assertEqual(3, res.next_index)

    def test_cluster_count_all(self):
        clusters = [shared.create_cluster(self.ctx, self.profile)
                    for i in range(3)]

        cl_db = db_api.cluster_count_all(self.ctx)
        self.assertEqual(3, cl_db)

        db_api.cluster_delete(self.ctx, clusters[0].id)
        cl_db = db_api.cluster_count_all(self.ctx)
        self.assertEqual(2, cl_db)

        db_api.cluster_delete(self.ctx, clusters[1].id)
        cl_db = db_api.cluster_count_all(self.ctx)
        self.assertEqual(1, cl_db)

    def test_cluster_count_all_with_regular_project(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.ctx.project_id = UUID1
        self.assertEqual(2, db_api.cluster_count_all(self.ctx))

        self.ctx.project_id = UUID2
        self.assertEqual(3, db_api.cluster_count_all(self.ctx))

    def test_cluster_count_all_with_project_safe_false(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.assertEqual(5, db_api.cluster_count_all(self.ctx,
                                                     project_safe=False))

    def test_cluster_count_all_with_admin_context(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        admin_ctx = utils.dummy_context(project='another-project',
                                        is_admin=True)
        self.assertEqual(0, db_api.cluster_count_all(admin_ctx,
                                                     project_safe=True))
        self.assertEqual(5, db_api.cluster_count_all(admin_ctx,
                                                     project_safe=False))

    def test_cluster_count_all_with_filters(self):
        shared.create_cluster(self.ctx, self.profile, name='foo')
        shared.create_cluster(self.ctx, self.profile, name='bar')
        shared.create_cluster(self.ctx, self.profile, name='bar')
        filters = {'name': 'bar'}

        cl_db = db_api.cluster_count_all(self.ctx, filters=filters)
        self.assertEqual(2, cl_db)

    def test_cluster_update(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        values = {
            'name': 'db_test_cluster_name2',
            'status': 'ERROR',
            'status_reason': "update failed",
            'timeout': 90,
        }
        db_api.cluster_update(self.ctx, cluster.id, values)
        cluster = db_api.cluster_get(self.ctx, cluster.id)
        self.assertEqual('db_test_cluster_name2', cluster.name)
        self.assertEqual('ERROR', cluster.status)
        self.assertEqual('update failed', cluster.status_reason)
        self.assertEqual(90, cluster.timeout)

        self.assertRaises(exception.ResourceNotFound,
                          db_api.cluster_update, self.ctx, UUID2, values)

    def test_nested_cluster_get_by_name(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster1')
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster2',
                                         parent=cluster1.id)

        result = db_api.cluster_get_by_name(self.ctx, 'cluster2')
        self.assertEqual(cluster2.id, result.id)

        db_api.cluster_delete(self.ctx, cluster2.id)
        result = db_api.cluster_get_by_name(self.ctx, 'cluster2')
        self.assertIsNone(result)

    def test_cluster_delete(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        cluster_id = cluster.id
        node = shared.create_node(self.ctx, cluster, self.profile)
        db_api.cluster_delete(self.ctx, cluster_id)

        self.assertIsNone(db_api.cluster_get(self.ctx, cluster_id))
        res = db_api.node_get(self.ctx, node.id)
        self.assertIsNone(res)
        self.assertRaises(exception.ResourceNotFound, db_api.cluster_delete,
                          self.ctx, cluster_id)

        # Testing child nodes deletion
        res = db_api.node_get(self.ctx, node.id)
        self.assertIsNone(res)

    def test_cluster_delete_policies_deleted(self):
        # create cluster
        cluster = shared.create_cluster(self.ctx, self.profile)
        cluster_id = cluster.id

        # create policy
        policy_data = {
            'name': 'test_policy',
            'type': 'ScalingPolicy',
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'spec': {'foo': 'bar'},
            'data': None,
        }
        policy = db_api.policy_create(self.ctx, policy_data)
        self.assertIsNotNone(policy)

        # attach policy
        fields = {
            'enabled': True,
        }
        db_api.cluster_policy_attach(self.ctx, cluster_id, policy.id, fields)
        binding = db_api.cluster_policy_get(self.ctx, cluster_id, policy.id)
        self.assertIsNotNone(binding)

        # now we delete the cluster
        db_api.cluster_delete(self.ctx, cluster_id)

        res = db_api.cluster_get(self.ctx, cluster_id)
        self.assertIsNone(res)

        # we check the cluster-policy binding
        binding = db_api.cluster_policy_get(self.ctx, cluster_id, policy.id)
        self.assertIsNone(binding)

        # but the policy is not deleted
        result = db_api.policy_get(self.ctx, policy.id)
        self.assertIsNotNone(result)

    def test_cluster_add_dependents(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        profile_id = 'profile1'
        db_api.cluster_add_dependents(self.ctx, cluster.id, profile_id)
        res = db_api.cluster_get(self.ctx, cluster.id)
        self.assertEqual(['profile1'], res.dependents['profiles'])
        deps = {}
        cluster = shared.create_cluster(self.ctx, self.profile,
                                        dependents=deps)
        db_api.cluster_add_dependents(self.ctx, cluster.id, profile_id)
        res = db_api.cluster_get(self.ctx, cluster.id)
        deps = {'profiles': ['profile1']}
        self.assertEqual(deps, res.dependents)
        db_api.cluster_add_dependents(self.ctx, cluster.id, 'profile2')
        res = db_api.cluster_get(self.ctx, cluster.id)
        deps = {'profiles': ['profile1', 'profile2']}
        self.assertEqual(deps, res.dependents)

    def test_cluster_remove_dependents(self):
        deps = {'profiles': ['profile1', 'profile2']}
        cluster = shared.create_cluster(self.ctx, self.profile,
                                        dependents=deps)
        db_api.cluster_remove_dependents(self.ctx, cluster.id, 'profile1')
        res = db_api.cluster_get(self.ctx, cluster.id)
        deps = {'profiles': ['profile2']}
        self.assertEqual(deps, res.dependents)
        db_api.cluster_remove_dependents(self.ctx, cluster.id, 'profile2')
        res = db_api.cluster_get(self.ctx, cluster.id)
        deps = {}
        self.assertEqual(deps, res.dependents)
