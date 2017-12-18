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
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared


class DBAPIClusterPolicyTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIClusterPolicyTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)
        self.cluster = shared.create_cluster(self.ctx, self.profile)

    def create_policy(self, **kwargs):
        data = {
            'name': 'test_policy',
            'type': 'ScalingPolicy',
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id,
            'spec': {
                'min_size': 1,
                'max_size': 10,
                'paust_time': 'PT10M',
            },
            'data': None,
        }

        data.update(kwargs)
        return db_api.policy_create(self.ctx, data)

    def test_policy_attach_detach(self):
        policy = self.create_policy()

        fields = {
            'enabled': True,
        }
        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertTrue(bindings[0].enabled)

        # This will succeed
        db_api.cluster_policy_detach(self.ctx, self.cluster.id, policy.id)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(0, len(bindings))

        # This will fail silently
        res = db_api.cluster_policy_detach(self.ctx, self.cluster.id, 'BOGUS')
        self.assertIsNone(res)

    def test_policy_enable_disable(self):
        policy = self.create_policy()

        fields = {
            'enabled': True,
        }
        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertTrue(bindings[0].enabled)

        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     {'enabled': True})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertTrue(bindings[0].enabled)

        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     {'enabled': False})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertFalse(bindings[0].enabled)

        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     {'enabled': True})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertTrue(bindings[0].enabled)

        # No policy binding found
        res = db_api.cluster_policy_update(self.ctx, self.cluster.id, 'BOGUS',
                                           {})
        self.assertIsNone(res)

    def test_policy_update_with_data(self):
        policy = self.create_policy()

        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id, {})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertIsNone(bindings[0].data)

        fields = {'data': {'foo': 'bar'}}
        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual({'foo': 'bar'}, bindings[0].data)

        fields = {'data': {'foo': 'BAR'}}
        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual({'foo': 'BAR'}, bindings[0].data)

    def test_policy_update_last_op(self):
        policy = self.create_policy()

        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id, {})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertIsNone(bindings[0].last_op)

        timestamp = tu.utcnow(True)
        fields = {'last_op': timestamp}
        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(timestamp, bindings[0].last_op)

    def test_cluster_policy_get(self):
        policy = self.create_policy()

        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id, {})

        binding = db_api.cluster_policy_get(self.ctx, self.cluster.id,
                                            policy.id)
        self.assertIsNotNone(binding)
        self.assertEqual(self.cluster.id, binding.cluster_id)
        self.assertEqual(policy.id, binding.policy_id)

    def test_policy_get_all_with_empty_filters(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid, {})

        filters = None
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

    @mock.patch.object(sa_utils, 'paginate_query')
    def test_policy_get_all_with_sort_key_are_used(self, mock_paginate):
        values = {
            'policy1': {'enabled': True},
            'policy2': {'enabled': True},
            'policy3': {'enabled': True}
        }

        # prepare
        for key in values:
            value = values[key]
            policy_id = self.create_policy(id=key).id
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         value)

        sort = consts.CLUSTER_POLICY_SORT_KEYS
        db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                      sort=','.join(sort))

        # Check sort_keys used
        args = mock_paginate.call_args[0]
        sort.append('id')
        self.assertEqual(set(sort), set(args[3]))

    def test_policy_get_all_with_sorting(self):
        values = {
            'policy1': {'enabled': True},
            'policy2': {'enabled': True},
            'policy3': {'enabled': False}
        }

        # prepare
        for key in values:
            value = values[key]
            policy_id = self.create_policy(id=key).id
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         value)

        # sorted by enabled, the 2nd and 3rd are unpredictable
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort='enabled')
        self.assertEqual('policy3', results[0].policy_id)

    def test_policy_get_all_by_policy_type(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid, {})

        results = db_api.cluster_policy_get_by_type(self.ctx, self.cluster.id,
                                                    'ScalingPolicy')
        self.assertEqual(2, len(results))

        results = db_api.cluster_policy_get_by_type(self.ctx, self.cluster.id,
                                                    'UnknownPolicy')
        self.assertEqual(0, len(results))

    def test_policy_get_all_by_policy_name(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid, {})

        results = db_api.cluster_policy_get_by_name(self.ctx, self.cluster.id,
                                                    'test_policy')
        self.assertEqual(2, len(results))

        results = db_api.cluster_policy_get_by_name(self.ctx, self.cluster.id,
                                                    'unknown_policy')
        self.assertEqual(0, len(results))

    def test_policy_get_all_by_policy_type_with_filter(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid,
                                         {'enabled': True})

        filters = {'enabled': True}
        results = db_api.cluster_policy_get_by_type(self.ctx, self.cluster.id,
                                                    'ScalingPolicy',
                                                    filters=filters)
        self.assertEqual(2, len(results))

        filters = {'enabled': False}
        results = db_api.cluster_policy_get_by_type(self.ctx, self.cluster.id,
                                                    'ScalingPolicy',
                                                    filters=filters)
        self.assertEqual(0, len(results))

    def test_policy_get_all_by_policy_name_with_filter(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid,
                                         {'enabled': True})

        filters = {'enabled': True}
        results = db_api.cluster_policy_get_by_name(self.ctx, self.cluster.id,
                                                    'test_policy',
                                                    filters=filters)
        self.assertEqual(2, len(results))

        filters = {'enabled': False}
        results = db_api.cluster_policy_get_by_name(self.ctx, self.cluster.id,
                                                    'test_policy',
                                                    filters=filters)
        self.assertEqual(0, len(results))

    def test_policy_get_all_with_all_filters(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid,
                                         {'enabled': True})

        filters = {'enabled': True,
                   'policy_name': 'test_policy',
                   'policy_type': 'ScalingPolicy'}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

        filters = {'enabled': True,
                   'policy_type': 'ScalingPolicy'}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

        filters = {'enabled': True,
                   'policy_name': 'test_policy'}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

        filters = {'enabled': True,
                   'policy_name': 'wrong_name',
                   'policy_type': 'wrong_type'}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(0, len(results))

        filters = {'policy_name': 'test_policy'}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

        filters = {'policy_type': 'ScalingPolicy'}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

        filters = {'enabled': False}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(0, len(results))

    def test_cluster_policy_ids_by_cluster(self):
        # prepare
        ids = []
        for i in range(3):
            policy_id = self.create_policy().id
            ids.append(policy_id)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         {'enabled': True})

        # sorted by enabled, the 2nd and 3rd are unpredictable
        results = db_api.cluster_policy_ids_by_cluster(self.ctx,
                                                       self.cluster.id)
        self.assertEqual(set(ids), set(results))
