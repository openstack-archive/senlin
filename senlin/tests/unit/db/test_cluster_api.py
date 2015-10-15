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
        self.assertEqual(self.ctx.user, cluster.user)
        self.assertEqual(self.ctx.project, cluster.project)
        self.assertEqual('unknown', cluster.domain)
        self.assertIsNone(cluster.parent)
        self.assertEqual(1, cluster.next_index)
        self.assertEqual(60, cluster.timeout)
        self.assertEqual(0, cluster.desired_capacity)
        self.assertEqual('INIT', cluster.status)
        self.assertEqual('Just Initialized', cluster.status_reason)
        self.assertIsNone(cluster.created_time)
        self.assertIsNone(cluster.updated_time)
        self.assertIsNone(cluster.deleted_time)
        self.assertIsNotNone(cluster.init_time)
        self.assertEqual({}, cluster.metadata)
        self.assertIsNone(cluster.data)

    def test_cluster_get_returns_a_cluster(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        ret_cluster = db_api.cluster_get(self.ctx, cluster.id,
                                         show_deleted=False)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

    def test_cluster_get_not_found(self):
        cluster = db_api.cluster_get(self.ctx, UUID1, show_deleted=False)
        self.assertIsNone(cluster)

    def test_cluster_get_from_different_project(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        self.ctx.project = 'abc'
        ret_cluster = db_api.cluster_get(self.ctx, cluster.id,
                                         show_deleted=False,
                                         project_safe=False)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

        cluster = db_api.cluster_get(self.ctx, cluster.id, show_deleted=False)
        self.assertIsNone(cluster)

    def test_cluster_get_show_deleted(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        result = db_api.cluster_get(self.ctx, cluster.id)
        self.assertEqual(cluster.id, result.id)

        db_api.cluster_delete(self.ctx, cluster.id)
        result = db_api.cluster_get(self.ctx, cluster.id)
        self.assertIsNone(result)

        result = db_api.cluster_get(self.ctx, cluster.id, show_deleted=True)
        self.assertEqual(cluster.id, result.id)

    def test_cluster_get_show_deleted_context(self):
        cluster = shared.create_cluster(self.ctx, self.profile)

        self.assertFalse(self.ctx.show_deleted)
        result = db_api.cluster_get(self.ctx, cluster.id)
        self.assertEqual(cluster.id, result.id)

        db_api.cluster_delete(self.ctx, cluster.id)
        result = db_api.cluster_get(self.ctx, cluster.id)
        self.assertIsNone(result)

        self.ctx.show_deleted = True
        result = db_api.cluster_get(self.ctx, cluster.id)
        self.assertEqual(cluster.id, result.id)

    def test_cluster_get_by_name(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        ret_cluster = db_api.cluster_get_by_name(self.ctx, cluster.name)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster.id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

        self.assertIsNone(db_api.cluster_get_by_name(self.ctx, 'abc'))

        self.ctx.project = 'abc'
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

        self.ctx.project = UUID3
        self.assertIsNone(db_api.cluster_get_by_name(self.ctx,
                                                     'cluster_A'))

        self.ctx.project = UUID2
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

        self.ctx.project = UUID1
        clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(2, len(clusters))

        self.ctx.project = UUID2
        clusters = db_api.cluster_get_all(self.ctx)
        self.assertEqual(3, len(clusters))

        self.ctx.project = UUID3
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

    def test_cluster_get_all_show_deleted(self):
        clusters = [shared.create_cluster(self.ctx, self.profile)
                    for x in range(3)]

        results = db_api.cluster_get_all(self.ctx)
        self.assertEqual(3, len(results))

        db_api.cluster_delete(self.ctx, clusters[0].id)
        results = db_api.cluster_get_all(self.ctx)
        self.assertEqual(2, len(results))

        results = db_api.cluster_get_all(self.ctx, show_deleted=True)
        self.assertEqual(3, len(results))

    def test_cluster_get_all_show_nested(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster1')
        cluster2 = shared.create_cluster(self.ctx, self.profile,
                                         name='cluster2',
                                         parent=cluster1.id)

        cl_db = db_api.cluster_get_all(self.ctx)
        self.assertEqual(1, len(cl_db))
        self.assertEqual(cluster1.id, cl_db[0].id)

        cl_db = db_api.cluster_get_all(self.ctx, show_nested=True)
        self.assertEqual(2, len(cl_db))
        cl_ids = [s.id for s in cl_db]
        self.assertIn(cluster1.id, cl_ids)
        self.assertIn(cluster2.id, cl_ids)

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
                                          init_time=tu.utcnow())
                    for x in range(3)]

        st_db = db_api.cluster_get_all(self.ctx, sort_dir='asc')
        self.assertEqual(3, len(st_db))
        self.assertEqual(clusters[0].id, st_db[0].id)
        self.assertEqual(clusters[1].id, st_db[1].id)
        self.assertEqual(clusters[2].id, st_db[2].id)

    def test_cluster_get_all_str_sort_keys(self):
        clusters = [shared.create_cluster(self.ctx, self.profile,
                                          created_time=tu.utcnow())
                    for x in range(3)]

        st_db = db_api.cluster_get_all(self.ctx, sort_keys='created_time')
        self.assertEqual(3, len(st_db))
        self.assertEqual(clusters[0].id, st_db[0].id)
        self.assertEqual(clusters[1].id, st_db[1].id)
        self.assertEqual(clusters[2].id, st_db[2].id)

    @mock.patch.object(db_api.utils, 'paginate_query')
    def test_cluster_get_all_filters_sort_keys(self, mock_paginate):
        sort_keys = ['name', 'status', 'created_time',
                     'updated_time', 'parent']
        db_api.cluster_get_all(self.ctx, sort_keys=sort_keys)

        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        expected_keys = set(['name', 'status', 'created_time',
                             'updated_time', 'id'])
        self.assertEqual(expected_keys, used_sort_keys)

    def test_cluster_get_all_marker(self):
        clusters = [shared.create_cluster(self.ctx, self.profile,
                                          created_time=tu.utcnow())
                    for x in range(3)]
        cl_db = db_api.cluster_get_all(self.ctx, marker=clusters[1].id)
        self.assertEqual(1, len(cl_db))
        self.assertEqual(clusters[2].id, cl_db[0].id)

    def test_cluster_get_all_non_existing_marker(self):
        [shared.create_cluster(self.ctx, self.profile) for x in range(3)]
        uuid = "this cluster doesn't exist"
        st_db = db_api.cluster_get_all(self.ctx, marker=uuid)
        self.assertEqual(3, len(st_db))

    def test_cluster_get_all_doesnt_mutate_sort_keys(self):
        [shared.create_cluster(self.ctx, self.profile) for x in range(3)]
        sort_keys = ['id']
        db_api.cluster_get_all(self.ctx, sort_keys=sort_keys)
        self.assertEqual(['id'], sort_keys)

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
        # show deleted
        cl_db = db_api.cluster_count_all(self.ctx, show_deleted=True)
        self.assertEqual(3, cl_db)

        db_api.cluster_delete(self.ctx, clusters[1].id)
        cl_db = db_api.cluster_count_all(self.ctx)
        self.assertEqual(1, cl_db)
        # show deleted
        cl_db = db_api.cluster_count_all(self.ctx, show_deleted=True)
        self.assertEqual(3, cl_db)

    def test_cluster_count_all_with_regular_project(self):
        values = [
            {'project': UUID1},
            {'project': UUID1},
            {'project': UUID2},
            {'project': UUID2},
            {'project': UUID2},
        ]
        [shared.create_cluster(self.ctx, self.profile, **v) for v in values]

        self.ctx.project = UUID1
        self.assertEqual(2, db_api.cluster_count_all(self.ctx))

        self.ctx.project = UUID2
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

    def test_cluster_count_all_show_nested(self):
        cluster1 = shared.create_cluster(self.ctx, self.profile, name='c1')
        shared.create_cluster(self.ctx, self.profile, name='c2',
                              parent=cluster1.id)

        results = db_api.cluster_count_all(self.ctx)
        self.assertEqual(1, results)
        results = db_api.cluster_count_all(self.ctx, show_nested=True)
        self.assertEqual(2, results)

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

        self.assertRaises(exception.ClusterNotFound,
                          db_api.cluster_update, self.ctx, UUID2, values)

    def test_get_sort_keys_returns_empty_list_if_no_keys(self):
        sort_keys = None
        mapping = {}

        filtered_keys = db_api._get_sort_keys(sort_keys, mapping)
        self.assertEqual([], filtered_keys)

    def test_get_sort_keys_whitelists_single_key(self):
        sort_key = 'foo'
        mapping = {'foo': 'Foo'}

        filtered_keys = db_api._get_sort_keys(sort_key, mapping)
        self.assertEqual(['Foo'], filtered_keys)

    def test_get_sort_keys_whitelists_multiple_keys(self):
        sort_keys = ['foo', 'bar', 'nope']
        mapping = {'foo': 'Foo', 'bar': 'Bar'}

        filtered_keys = db_api._get_sort_keys(sort_keys, mapping)
        self.assertIn('Foo', filtered_keys)
        self.assertIn('Bar', filtered_keys)
        self.assertEqual(2, len(filtered_keys))

    @mock.patch.object(db_api.utils, 'paginate_query')
    def test_paginate_query_raises_invalid_sort_key(self, mock_paginate_query):
        query = mock.Mock()
        model = mock.Mock()

        mock_paginate_query.side_effect = db_api.utils.InvalidSortKey()
        self.assertRaises(exception.InvalidParameter, db_api._paginate_query,
                          self.ctx, query, model, sort_keys=['foo'])

    @mock.patch.object(db_api.utils, 'paginate_query')
    @mock.patch.object(db_api, 'model_query')
    def test_paginate_query_gets_model_marker(self, mock_query,
                                              mock_paginate_query):
        query = mock.Mock()
        model = mock.Mock()
        marker = mock.Mock()

        mock_query_object = mock.Mock()
        mock_query_object.get.return_value = 'real_marker'
        mock_query.return_value = mock_query_object

        db_api._paginate_query(self.ctx, query, model, marker=marker)
        mock_query_object.get.assert_called_once_with(marker)
        args, _ = mock_paginate_query.call_args
        self.assertIn('real_marker', args)

    @mock.patch.object(db_api.utils, 'paginate_query')
    def test_paginate_query_default_sorts_dir_by_desc(self,
                                                      mock_paginate_query):
        query = mock.Mock()
        model = mock.Mock()
        db_api._paginate_query(self.ctx, query, model, sort_dir=None)
        args, _ = mock_paginate_query.call_args
        self.assertIn('asc', args)

    @mock.patch.object(db_api.utils, 'paginate_query')
    def test_paginate_query_uses_given_sort_plus_id(self,
                                                    mock_paginate_query):
        query = mock.Mock()
        model = mock.Mock()
        db_api._paginate_query(self.ctx, query, model, sort_keys=['name'])
        args, _ = mock_paginate_query.call_args
        self.assertIn(['name', 'id'], args)

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

    def _deleted_cluster_existance(self, ctx, clusters, existing, deleted):
        for s in existing:
            self.assertIsNotNone(db_api.cluster_get(ctx, clusters[s].id,
                                                    show_deleted=True))
        for s in deleted:
            self.assertIsNone(db_api.cluster_get(ctx, clusters[s].id,
                                                 show_deleted=True))

    def test_cluster_delete(self):
        cluster = shared.create_cluster(self.ctx, self.profile)
        cluster_id = cluster.id
        node = shared.create_node(self.ctx, cluster, self.profile)
        db_api.cluster_delete(self.ctx, cluster_id)

        self.assertIsNone(db_api.cluster_get(self.ctx, cluster_id,
                                             show_deleted=False))
        res = db_api.node_get(self.ctx, node.id)
        self.assertIsNone(res)
        self.assertRaises(exception.ClusterNotFound, db_api.cluster_delete,
                          self.ctx, cluster_id)

        # Testing soft delete
        ret_cluster = db_api.cluster_get(self.ctx, cluster_id,
                                         show_deleted=True)
        self.assertIsNotNone(ret_cluster)
        self.assertEqual(cluster_id, ret_cluster.id)
        self.assertEqual('db_test_cluster_name', ret_cluster.name)

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
            'user': self.ctx.user,
            'project': self.ctx.project,
            'spec': {'foo': 'bar'},
            'level': 50,
            'cooldown': 60,
            'data': None,
        }
        policy = db_api.policy_create(self.ctx, policy_data)
        self.assertIsNotNone(policy)

        # attach policy
        fields = {
            'enabled': True,
            'priority': 77,
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
