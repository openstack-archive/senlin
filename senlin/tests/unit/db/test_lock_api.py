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

from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPILockTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPILockTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)
        self.cluster = shared.create_cluster(self.ctx, self.profile)
        self.node = shared.create_node(self.ctx, self.cluster, self.profile)

    def test_cluster_lock_cluster_scope(self):
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID1, -1)
        self.assertIn(UUID1, observed)
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, -1)
        self.assertNotIn(UUID2, observed)
        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, -1)
        self.assertFalse(observed)
        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, -1)
        self.assertTrue(observed)

    def test_cluster_lock_node_scope(self):
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID1, 1)
        self.assertIn(UUID1, observed)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, 1)
        self.assertIn(UUID1, observed)
        self.assertIn(UUID2, observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, 1)
        self.assertIn(UUID1, observed)
        self.assertIn(UUID2, observed)
        self.assertEqual(2, len(observed))

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, 1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, 1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID3, 1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, 1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, 1)
        self.assertFalse(observed)

    def test_cluster_lock_cluster_lock_first(self):
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID1, -1)
        self.assertIn(UUID1, observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, -1)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, -1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, 1)
        self.assertNotIn(UUID3, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID3, 1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, -1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, -1)
        self.assertIn(UUID2, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, -1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, 1)
        self.assertIn(UUID3, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID3, 1)
        self.assertTrue(observed)

    def test_cluster_lock_node_lock_first(self):
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID1, 1)
        self.assertIn(UUID1, observed)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, 1)
        self.assertIn(UUID1, observed)
        self.assertIn(UUID2, observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, -1)
        self.assertIn(UUID1, observed)
        self.assertIn(UUID2, observed)
        self.assertNotIn(UUID3, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID3, -1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, 1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, -1)
        self.assertNotIn(UUID1, observed)
        self.assertIn(UUID2, observed)
        self.assertNotIn(UUID3, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID3, -1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, 1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, 1)
        self.assertFalse(observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, -1)
        self.assertIn(UUID3, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID3, -1)
        self.assertTrue(observed)

    def test_cluster_lock_steal(self):
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID1, -1)
        self.assertIn(UUID1, observed)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_steal(self.cluster.id, UUID1)
        self.assertIn(UUID1, observed)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_steal(self.cluster.id, UUID2)
        self.assertNotIn(UUID1, observed)
        self.assertIn(UUID2, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID2, -1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_steal(self.cluster.id, UUID1)
        self.assertIn(UUID1, observed)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, -1)
        self.assertTrue(observed)

        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, 1)
        self.assertIn(UUID3, observed)
        self.assertNotIn(UUID1, observed)
        self.assertNotIn(UUID2, observed)

        observed = db_api.cluster_lock_steal(self.cluster.id, UUID1)
        self.assertIn(UUID1, observed)
        self.assertNotIn(UUID3, observed)

        observed = db_api.cluster_lock_release(self.cluster.id, UUID1, -1)
        self.assertTrue(observed)

    def test_node_lock_acquire_release(self):
        observed = db_api.node_lock_acquire(self.node.id, UUID1)
        self.assertEqual(UUID1, observed)

        observed = db_api.node_lock_acquire(self.node.id, UUID2)
        self.assertEqual(UUID1, observed)

        observed = db_api.node_lock_release(self.node.id, UUID2)
        self.assertFalse(observed)

        observed = db_api.node_lock_release(self.node.id, UUID1)
        self.assertTrue(observed)

        observed = db_api.node_lock_release(self.node.id, UUID1)
        self.assertFalse(observed)

        observed = db_api.node_lock_acquire(self.node.id, UUID2)
        self.assertEqual(UUID2, observed)

        observed = db_api.node_lock_release(self.node.id, UUID2)
        self.assertTrue(observed)

    def test_node_lock_steal(self):
        observed = db_api.node_lock_steal(self.node.id, UUID1)
        self.assertEqual(UUID1, observed)

        observed = db_api.node_lock_acquire(self.node.id, UUID2)
        self.assertEqual(UUID1, observed)

        observed = db_api.node_lock_release(self.node.id, UUID2)
        self.assertFalse(observed)

        observed = db_api.node_lock_release(self.node.id, UUID1)
        self.assertTrue(observed)

        observed = db_api.node_lock_acquire(self.node.id, UUID1)
        self.assertEqual(UUID1, observed)

        observed = db_api.node_lock_steal(self.node.id, UUID2)
        self.assertEqual(UUID2, observed)

        observed = db_api.node_lock_release(self.node.id, UUID1)
        self.assertFalse(observed)

        observed = db_api.node_lock_release(self.node.id, UUID2)
        self.assertTrue(observed)
