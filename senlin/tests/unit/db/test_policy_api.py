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

from senlin.common import consts
from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

sample_spec = {
    'min_size': 1,
    'max_size': 10,
    'pause_time': 'PT10M',
}


class DBAPIPolicyTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIPolicyTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)
        self.cluster = shared.create_cluster(self.ctx, self.profile)

    def new_policy_data(self, **kwargs):
        data = {
            'name': 'test_policy',
            'type': 'ScalingPolicy',
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id,
            'spec': sample_spec,
            'data': None,
        }

        data.update(kwargs)
        return data

    def test_policy_create(self):
        data = self.new_policy_data()
        policy = db_api.policy_create(self.ctx, data)

        self.assertIsNotNone(policy)
        self.assertEqual(data['name'], policy.name)
        self.assertEqual(data['type'], policy.type)
        self.assertEqual(data['spec'], policy.spec)
        self.assertEqual(10, policy.spec['max_size'])
        self.assertIsNone(policy.data)

    def test_policy_get(self):
        data = self.new_policy_data()
        policy = db_api.policy_create(self.ctx, data)

        retobj = db_api.policy_get(self.ctx, policy.id)
        self.assertIsNotNone(retobj)
        self.assertEqual(data['name'], retobj.name)
        self.assertEqual(data['type'], retobj.type)
        self.assertEqual(data['spec'], retobj.spec)
        self.assertEqual(10, retobj.spec['max_size'])
        self.assertIsNone(retobj.data)

    def test_policy_get_diff_project(self):
        data = self.new_policy_data()
        policy = db_api.policy_create(self.ctx, data)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.policy_get(new_ctx, policy.id)
        self.assertIsNone(res)
        res = db_api.policy_get(new_ctx, policy.id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(policy.id, res.id)

    def test_policy_get_admin_context(self):
        data = self.new_policy_data()
        policy = db_api.policy_create(self.ctx, data)

        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        res = db_api.policy_get(admin_ctx, policy.id, project_safe=True)
        self.assertIsNone(res)
        res = db_api.policy_get(admin_ctx, policy.id, project_safe=False)
        self.assertIsNotNone(res)

    def test_policy_get_not_found(self):
        retobj = db_api.policy_get(self.ctx, 'BogusID')
        self.assertIsNone(retobj)

    def test_policy_get_by_name(self):
        policy_name = 'my_best_policy'
        data = self.new_policy_data(name=policy_name)

        # before creation
        policy = db_api.policy_get_by_name(self.ctx, policy_name)
        self.assertIsNone(policy)

        policy = db_api.policy_create(self.ctx, data)

        # after creation
        retobj = db_api.policy_get_by_name(self.ctx, policy_name)
        self.assertIsNotNone(retobj)
        self.assertEqual(policy_name, retobj.name)

        # bad name
        retobj = db_api.policy_get_by_name(self.ctx, 'non-exist')
        self.assertIsNone(retobj)

        # duplicated name
        db_api.policy_create(self.ctx, data)
        self.assertRaises(exception.MultipleChoices,
                          db_api.policy_get_by_name,
                          self.ctx, policy_name)

    def test_policy_get_by_name_diff_project(self):
        policy_name = 'my_best_policy'
        data = self.new_policy_data(name=policy_name)
        policy = db_api.policy_create(self.ctx, data)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.policy_get_by_name(new_ctx, policy_name)
        self.assertIsNone(res)
        res = db_api.policy_get_by_name(new_ctx, policy_name,
                                        project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(policy.id, res.id)

    def test_policy_get_by_short_id(self):
        policy_ids = ['same-part-unique-part',
                      'same-part-part-unique']

        for pid in policy_ids:
            data = self.new_policy_data(id=pid)
            db_api.policy_create(self.ctx, data)

            # verify creation with set ID
            policy = db_api.policy_get(self.ctx, pid)
            self.assertIsNotNone(policy)
            self.assertEqual(pid, policy.id)

        # too short -> multiple choices
        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.policy_get_by_short_id,
                              self.ctx, policy_ids[0][:x])

        # ids are unique
        policy = db_api.policy_get_by_short_id(self.ctx, policy_ids[0][:11])
        self.assertEqual(policy_ids[0], policy.id)
        policy = db_api.policy_get_by_short_id(self.ctx, policy_ids[1][:11])
        self.assertEqual(policy_ids[1], policy.id)

        # bad ids
        res = db_api.policy_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_policy_get_by_short_id_diff_project(self):
        policy_id = 'same-part-unique-part'
        data = self.new_policy_data(id=policy_id)
        db_api.policy_create(self.ctx, data)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.policy_get_by_short_id(new_ctx, policy_id[0][:11])
        self.assertIsNone(res)
        res = db_api.policy_get_by_short_id(new_ctx, policy_id[0][:11],
                                            project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(policy_id, res.id)

    def test_policy_get_all(self):
        specs = [
            {'name': 'policy_short', 'cooldown': '10'},
            {'name': 'policy_long', 'cooldown': '100'},
        ]

        for spec in specs:
            data = self.new_policy_data(**spec)
            db_api.policy_create(self.ctx, data)

        policies = db_api.policy_get_all(self.ctx)
        self.assertEqual(2, len(policies))
        names = [p.name for p in policies]
        for spec in specs:
            self.assertIn(spec['name'], names)

        db_api.policy_delete(self.ctx, policies[1].id)

        # after delete one of them
        policies = db_api.policy_get_all(self.ctx)
        self.assertEqual(1, len(policies))

        # after delete both policies
        db_api.policy_delete(self.ctx, policies[0].id)

        policies = db_api.policy_get_all(self.ctx)
        self.assertEqual(0, len(policies))

    def test_policy_get_all_diff_project(self):
        specs = [
            {'name': 'policy_short', 'cooldown': '10'},
            {'name': 'policy_long', 'cooldown': '100'},
        ]

        for spec in specs:
            data = self.new_policy_data(**spec)
            db_api.policy_create(self.ctx, data)

        new_ctx = utils.dummy_context(project='a-different-project')
        policies = db_api.policy_get_all(new_ctx)
        self.assertEqual(0, len(policies))
        policies = db_api.policy_get_all(new_ctx, project_safe=False)
        self.assertEqual(2, len(policies))

    def test_policy_get_all_admin_context(self):
        specs = [
            {'name': 'policy_short', 'cooldown': '10'},
            {'name': 'policy_long', 'cooldown': '100'},
        ]

        for spec in specs:
            data = self.new_policy_data(**spec)
            db_api.policy_create(self.ctx, data)

        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        policies = db_api.policy_get_all(admin_ctx, project_safe=True)
        self.assertEqual(0, len(policies))
        policies = db_api.policy_get_all(admin_ctx, project_safe=False)
        self.assertEqual(2, len(policies))

    def test_policy_get_all_with_limit_marker(self):
        ids = ['policy1', 'policy2', 'policy3']
        for pid in ids:
            timestamp = tu.utcnow(True)
            data = self.new_policy_data(id=pid, created_at=timestamp)
            db_api.policy_create(self.ctx, data)

        # different limit settings
        policies = db_api.policy_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(policies))

        policies = db_api.policy_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(policies))

        # a large limit
        policies = db_api.policy_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(policies))

        # use marker here
        policies = db_api.policy_get_all(self.ctx, marker='policy1')
        self.assertEqual(2, len(policies))

        policies = db_api.policy_get_all(self.ctx, marker='policy2')
        self.assertEqual(1, len(policies))

        policies = db_api.policy_get_all(self.ctx, marker='policy3')
        self.assertEqual(0, len(policies))

        policies = db_api.policy_get_all(self.ctx, limit=1, marker='policy1')
        self.assertEqual(1, len(policies))

    @mock.patch.object(sa_utils, 'paginate_query')
    def test_policy_get_all_used_sort_keys(self, mock_paginate):
        ids = ['policy1', 'policy2', 'policy3']
        for pid in ids:
            data = self.new_policy_data(id=pid)
            db_api.policy_create(self.ctx, data)

        sort_keys = consts.POLICY_SORT_KEYS
        db_api.policy_get_all(self.ctx, sort=','.join(sort_keys))

        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        sort_keys.append('id')
        expected_keys = set(sort_keys)
        self.assertEqual(expected_keys, used_sort_keys)

    def test_policy_get_all_sorting(self):
        values = [{'id': '001', 'name': 'policy1'},
                  {'id': '002', 'name': 'policy3'},
                  {'id': '003', 'name': 'policy2'}]

        for v in values:
            v['created_at'] = tu.utcnow(True)
            data = self.new_policy_data(**v)
            db_api.policy_create(self.ctx, data)

        # Sorted by name
        policies = db_api.policy_get_all(self.ctx, sort='name')
        self.assertEqual(3, len(policies))
        self.assertEqual('001', policies[0].id)
        self.assertEqual('003', policies[1].id)
        self.assertEqual('002', policies[2].id)

        # Sorted by created_at and name (ascending)
        policies = db_api.policy_get_all(self.ctx, sort='created_at,name')
        self.assertEqual(3, len(policies))
        self.assertEqual('001', policies[0].id)
        self.assertEqual('002', policies[1].id)
        self.assertEqual('003', policies[2].id)

        # Sorted by name (descending)
        policies = db_api.policy_get_all(self.ctx, sort='name:desc')
        self.assertEqual(3, len(policies))
        self.assertEqual('002', policies[0].id)
        self.assertEqual('003', policies[1].id)
        self.assertEqual('001', policies[2].id)

    def test_policy_get_all_default_sorting(self):
        policies = []
        for x in range(3):
            data = self.new_policy_data(created_at=tu.utcnow(True))
            policies.append(db_api.policy_create(self.ctx, data))

        results = db_api.policy_get_all(self.ctx)
        self.assertEqual(3, len(results))
        self.assertEqual(policies[0].id, results[0].id)
        self.assertEqual(policies[1].id, results[1].id)
        self.assertEqual(policies[2].id, results[2].id)

    def test_policy_get_all_with_filters(self):
        for name in ['policy1', 'policy2']:
            data = self.new_policy_data(name=name)
            db_api.policy_create(self.ctx, data)

        filters = {'name': ['policy1', 'policyx']}
        results = db_api.policy_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('policy1', results[0]['name'])

        filters = {'name': 'policy1'}
        results = db_api.policy_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('policy1', results[0]['name'])

    def test_policy_get_all_with_empty_filters(self):
        for name in ['policy1', 'policy2']:
            data = self.new_policy_data(name=name)
            db_api.policy_create(self.ctx, data)

        filters = None
        results = db_api.policy_get_all(self.ctx, filters=filters)
        self.assertEqual(2, len(results))

    def test_policy_update(self):
        another_policy = {
            'name': 'new_scaling_policy',
            'type': 'ScalingPolicy',
            'spec': {
                'min_size': 5,
                'max_size': 15,
            }
        }
        old_data = self.new_policy_data()
        old_policy = db_api.policy_create(self.ctx, old_data)

        new_data = self.new_policy_data(**another_policy)
        new_policy = db_api.policy_update(self.ctx, old_policy.id, new_data)

        self.assertEqual(old_policy.id, new_policy.id)
        self.assertEqual(new_data['name'], new_policy.name)
        self.assertEqual('new_scaling_policy', new_policy.name)

    def test_policy_update_not_found(self):
        self.assertRaises(exception.ResourceNotFound,
                          db_api.policy_update,
                          self.ctx, 'BogusID', {})

    def test_policy_delete(self):
        policy = db_api.policy_create(self.ctx, self.new_policy_data())
        self.assertIsNotNone(policy)

        policy_id = policy.id
        db_api.policy_delete(self.ctx, policy_id)

        policy = db_api.policy_get(self.ctx, policy_id)
        self.assertIsNone(policy)

        # not found in delete is okay
        res = db_api.policy_delete(self.ctx, policy_id)
        self.assertIsNone(res)

    def test_policy_delete_in_use(self):
        policy = db_api.policy_create(self.ctx, self.new_policy_data())
        self.assertIsNotNone(policy)

        fields = {
            'enabled': True,
        }
        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id,
                                     fields)
        self.assertRaises(exception.EResourceBusy,
                          db_api.policy_delete,
                          self.ctx, policy.id)

        db_api.cluster_policy_detach(self.ctx, self.cluster.id, policy.id)
        db_api.policy_delete(self.ctx, policy.id)
        policy = db_api.policy_get(self.ctx, policy.id)
        self.assertIsNone(policy)
