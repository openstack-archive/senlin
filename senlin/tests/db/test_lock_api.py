# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.common import base
from senlin.tests.common import utils

UUIDs = (UUID1, UUID2, UUID3) = sorted([str(uuid.uuid4())
                                        for x in range(3)])

sample_profile = '''
  name: my_test_profile
  type: os.heat.stack
  spec:
    template:
      get_file: template_file
    files:
      fname: contents
'''


def create_profile(context, **kwargs):
    data = parser.parse_profile(sample_profile)
    values = {
        'name': 'test_profile_name',
        'type': 'os.heat.stack',
        'spec': {
            'template': {
                'heat_template_version': '2013-05-23',
                'resources': {
                    'myrandom': 'OS::Heat::RandomString',
                }
            },
            'files': {'foo': 'bar'}
        },
        'permission': 'xxxyyy',
    }
    values.update(kwargs)
    return db_api.profile_create(context, values)


def create_cluster(ctx, profile, **kwargs):
    values = {
        'name': 'db_test_cluster_name',
        'profile_id': profile.id,
        'user': ctx.user,
        'project': ctx.tenant_id,
        'domain': 'unknown',
        'parent': None,
        'next_index': 0,
        'timeout': '60',
        'status': 'INIT',
        'status_reason': 'Just Initialized'
    }
    values.update(kwargs)
    return db_api.cluster_create(ctx, values)


class DBAPILockTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPILockTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = create_profile(self.ctx)
        self.cluster = create_cluster(self.ctx, self.profile)

    def test_cluster_lock_create_success(self):
        observed = db_api.cluster_lock_create(self.cluster.id, UUID1)
        self.assertIsNone(observed)

    def test_cluster_lock_create_fail_double_same(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_create(self.cluster.id, UUID1)
        self.assertEqual(UUID1, observed)

    def test_cluster_lock_create_fail_double_different(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_create(self.cluster.id, UUID2)
        self.assertEqual(UUID1, observed)

    def test_cluster_lock_steal_success(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_steal(self.cluster.id, UUID1, UUID2)
        self.assertIsNone(observed)

    def test_cluster_lock_steal_fail_gone(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        db_api.cluster_lock_release(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_steal(self.cluster.id, UUID1, UUID2)
        self.assertTrue(observed)

    def test_cluster_lock_steal_fail_stolen(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)

        # Simulate stolen lock
        db_api.cluster_lock_release(self.cluster.id, UUID1)
        db_api.cluster_lock_create(self.cluster.id, UUID2)

        observed = db_api.cluster_lock_steal(self.cluster.id, UUID3, UUID2)
        self.assertEqual(UUID2, observed)

    def test_cluster_lock_release_success(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_release(self.cluster.id, UUID1)
        self.assertIsNone(observed)

    def test_cluster_lock_release_fail_double(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        db_api.cluster_lock_release(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_release(self.cluster.id, UUID1)
        self.assertTrue(observed)

    def test_cluster_lock_release_fail_wrong_engine_id(self):
        db_api.cluster_lock_create(self.cluster.id, UUID1)
        observed = db_api.cluster_lock_release(self.cluster.id, UUID2)
        self.assertTrue(observed)
