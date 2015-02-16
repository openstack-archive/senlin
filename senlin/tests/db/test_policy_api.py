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
from senlin.engine import parser
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared


class DBAPIPolicyTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIPolicyTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_policy_create(self):
        data = parser.parse_policy(shared.sample_policy)
        policy = db_api.policy_create(self.ctx, data)

        self.assertIsNotNone(policy)
        self.assertEqual(data['name'], policy.name)
        self.assertEqual(data['type'], policy.type)
        self.assertEqual(data['cooldown'], policy.cooldown)
        self.assertEqual(data['level'], policy.level)
        self.assertEqual(data['spec'], policy.spec)
        self.assertEqual(10, policy.spec['max_size'])
        self.assertIsNone(policy.data)

    def test_policy_get(self):
        data = parser.parse_policy(shared.sample_policy)
        policy = db_api.policy_create(self.ctx, data)
        policy = shared.create_policy(self.ctx)
        retobj = db_api.policy_get(self.ctx, policy.id)
        self.assertIsNotNone(retobj)
        self.assertEqual(data['name'], retobj.name)
        self.assertEqual(data['type'], retobj.type)
        self.assertEqual(data['cooldown'], retobj.cooldown)
        self.assertEqual(data['level'], retobj.level)
        self.assertEqual(data['spec'], retobj.spec)
        self.assertEqual(10, retobj.spec['max_size'])
        self.assertIsNone(retobj.data)

    def test_policy_get_all(self):
        specs = [
            {'name': 'policy_short', 'cooldown': '10'},
            {'name': 'policy_long', 'cooldown': '100'},
        ]

        for spec in specs:
            shared.create_policy(self.ctx,
                                 policy=shared.sample_policy,
                                 **spec)

        policies = db_api.policy_get_all(self.ctx)
        self.assertEqual(2, len(policies))
        names = [p.name for p in policies]
        for spec in specs:
            self.assertIn(spec['name'], names)

    def test_policy_update(self):
        another_policy = '''
          name: new_scaling_policy
          type: ScalingPolicy
          cooldown: 11
          level: WARNING
          spec:
            min_size: 1
            max_size: 10
            pause_time: PT10M
        '''
        new_data = parser.parse_policy(another_policy)
        old_policy = shared.create_policy(self.ctx)
        new_policy = db_api.policy_update(self.ctx, old_policy.id, new_data)

        self.assertEqual(old_policy.id, new_policy.id)
        self.assertEqual(new_data['name'], new_policy.name)
        self.assertEqual('new_scaling_policy', new_policy.name)
        self.assertEqual(11, new_policy.cooldown)

    def test_policy_delete(self):
        policy = shared.create_policy(self.ctx)
        self.assertIsNotNone(policy)
        policy_id = policy.id
        db_api.policy_delete(self.ctx, policy.id)

        policy = db_api.policy_get(self.ctx, policy_id)
        self.assertIsNone(policy)
