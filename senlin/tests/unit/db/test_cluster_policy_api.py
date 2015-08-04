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

from oslo_utils import timeutils as tu

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
            'user': self.ctx.user,
            'project': self.ctx.project,
            'domain': self.ctx.domain,
            'spec': {
                'min_size': 1,
                'max_size': 10,
                'paust_time': 'PT10M',
            },
            'level': 50,
            'cooldown': 60,
            'data': None,
        }

        data.update(kwargs)
        return db_api.policy_create(self.ctx, data)

    def test_policy_attach_detach(self):
        policy = self.create_policy()

        fields = {
            'enabled': True,
            'level': 50
        }
        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

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
            'level': 50
        }
        db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     {'enabled': True})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     {'enabled': False})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(False, bindings[0].enabled)

        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     {'enabled': True})
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

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

        timestamp = tu.utcnow()
        fields = {'last_op': timestamp}
        db_api.cluster_policy_update(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(timestamp, bindings[0].last_op)

    def test_policy_get_all_prioritized(self):
        policy = self.create_policy()

        fields = {'enabled': True, 'level': 50, 'priority': 20}
        binding1 = db_api.cluster_policy_attach(self.ctx, self.cluster.id,
                                                policy.id, fields)

        fields = {'enabled': True, 'level': 50, 'priority': 40}
        binding2 = db_api.cluster_policy_attach(self.ctx, self.cluster.id,
                                                policy.id, fields)

        bindings = db_api.cluster_policy_get_all(self.ctx, self.cluster.id)

        self.assertEqual(binding1.id, bindings[1].id)
        self.assertEqual(binding2.id, bindings[0].id)

    def test_policy_get_all_with_filters(self):
        values = {'policy1': {'level': 40, 'priority': 40},
                  'policy2': {'level': 30, 'priority': 60}}

        for key in values:
            value = values[key]
            policy_id = self.create_policy(id=key).id
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         value)

        filters = {'policy_id': ['policy1', 'policyx']}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('policy1', results[0].policy_id)

        filters = {'priority': 60}
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('policy2', results[0].policy_id)

    def test_policy_get_all_with_empty_filters(self):
        for pid in ['policy1', 'policy2']:
            self.create_policy(id=pid)
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, pid, {})

        filters = None
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))

    def test_policy_get_all_with_sort_key_are_used(self):
        values = {
            'policy1': {'level': 40, 'priority': 40, 'cooldown': 1,
                        'enabled': True},
            'policy2': {'level': 30, 'priority': 60, 'cooldown': 2,
                        'enabled': True},
            'policy3': {'level': 50, 'priority': 10, 'cooldown': 3,
                        'enabled': True}
        }

        # prepare
        for key in values:
            value = values[key]
            policy_id = self.create_policy(id=key).id
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         value)

        mock_paginate = self.patchobject(db_api.utils, 'paginate_query')

        sort_keys = ['level', 'priority', 'cooldown', 'enabled']
        db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                      sort_keys=sort_keys)

        # Check sort_keys used
        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        expected_keys = set(['id', 'level', 'priority', 'cooldown',
                             'enabled'])
        self.assertEqual(expected_keys, used_sort_keys)

    def test_policy_get_all_with_sort_key_and_dir(self):
        values = {
            'policy1': {'level': 40, 'priority': 40, 'cooldown': 10,
                        'enabled': True},
            'policy2': {'level': 30, 'priority': 60, 'cooldown': 20,
                        'enabled': True},
            'policy3': {'level': 50, 'priority': 10, 'cooldown': 30,
                        'enabled': False}
        }

        # prepare
        for key in values:
            value = values[key]
            policy_id = self.create_policy(id=key).id
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         value)

        # sorted by level
        sort_keys = ['level']
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort_keys=sort_keys)
        self.assertEqual('policy2', results[0].policy_id)
        self.assertEqual('policy1', results[1].policy_id)
        self.assertEqual('policy3', results[2].policy_id)

        # sorted by priority
        sort_keys = ['priority']
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort_keys=sort_keys)
        self.assertEqual('policy3', results[0].policy_id)
        self.assertEqual('policy1', results[1].policy_id)
        self.assertEqual('policy2', results[2].policy_id)

        # sorted by cooldown
        sort_keys = ['cooldown']
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort_keys=sort_keys)
        self.assertEqual('policy1', results[0].policy_id)
        self.assertEqual('policy2', results[1].policy_id)
        self.assertEqual('policy3', results[2].policy_id)

        # sorted by enabled, the 2nd and 3rd are unpredictable
        sort_keys = ['enabled']
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort_keys=sort_keys)
        self.assertEqual('policy3', results[0].policy_id)

        # sorted by enabled, the 2nd and 3rd are ordered by priority
        sort_keys = ['enabled', 'priority']
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort_keys=sort_keys)
        self.assertEqual('policy3', results[0].policy_id)
        self.assertEqual('policy1', results[1].policy_id)
        self.assertEqual('policy2', results[2].policy_id)

        # sorted by cooldown, descending
        sort_keys = ['cooldown']
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                sort_keys=sort_keys,
                                                sort_dir='desc')
        self.assertEqual('policy3', results[0].policy_id)
        self.assertEqual('policy2', results[1].policy_id)
        self.assertEqual('policy1', results[2].policy_id)

    def test_policy_get_all_with_default_sort_keys(self):
        values = {'policy1': {'level': 40, 'priority': 40},
                  'policy2': {'level': 30, 'priority': 60}}

        for key in values:
            value = values[key]
            policy_id = self.create_policy(id=key).id
            db_api.cluster_policy_attach(self.ctx, self.cluster.id, policy_id,
                                         value)

        filters = None
        results = db_api.cluster_policy_get_all(self.ctx, self.cluster.id,
                                                filters=filters)
        self.assertEqual(2, len(results))
