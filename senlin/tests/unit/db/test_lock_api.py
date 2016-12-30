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


class GCByEngineTest(base.SenlinTestCase):

    def setUp(self):
        super(GCByEngineTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)
        self.cluster = shared.create_cluster(self.ctx, self.profile)
        self.node = shared.create_node(self.ctx, self.cluster, self.profile)

    def test_delete_cluster_lock(self):
        # Test the case that a single cluster-scope clock can be released
        #
        #  (dead-engine) --> Action      --> ClusterLock
        #                    |action|owner|  |cluster|action|scope|
        #                    | A1   | E1  |  |C1     |[A1]  |-1   |

        # preparation
        engine_id = UUID1
        action = shared.create_action(self.ctx, target=self.cluster.id,
                                      status='RUNNING', owner=engine_id,
                                      project=self.ctx.project)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, -1)

        # do it
        db_api.gc_by_engine(self.ctx, engine_id)

        # assertion
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID2, -1)
        self.assertIn(UUID2, observed)
        self.assertNotIn(action.id, observed)

        new_action = db_api.action_get(self.ctx, action.id)
        self.assertEqual('FAILED', new_action.status)
        self.assertEqual("Engine failure", new_action.status_reason)

    def test_delete_cluster_lock_and_node_lock_1(self):
        # Test the case that an action is about node that also locked a
        # cluster and the cluster lock can be released
        #
        #  (dead-engine) --> Action      --> NodeLock
        #                    |action|owner|  |node |action|
        #                    | A1   | E1  |  |N1   |A1    |
        #                                --> ClusterLock
        #                                    |cluster|action|scope|
        #                                    |C1     |[A1]  |1    |
        # preparation
        engine_id = UUID1
        action = shared.create_action(self.ctx, target=self.node.id,
                                      status='RUNNING', owner=engine_id,
                                      project=self.ctx.project)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, 1)
        db_api.node_lock_acquire(self.cluster.id, action.id)

        # do it
        db_api.gc_by_engine(self.ctx, engine_id)

        # assertion
        # even a read lock is okay now
        observed = db_api.cluster_lock_acquire(self.node.id, UUID2, 1)
        self.assertIn(UUID2, observed)
        self.assertNotIn(action.id, observed)

        # node can be locked again
        observed = db_api.node_lock_acquire(self.node.id, UUID2)
        self.assertEqual(UUID2, observed)

        new_action = db_api.action_get(self.ctx, action.id)
        self.assertEqual('FAILED', new_action.status)
        self.assertEqual("Engine failure", new_action.status_reason)

    def test_delete_cluster_lock_and_node_lock_2(self):
        # Test the case that an action is about node that also locked a
        # cluster and the cluster lock will remain locked
        #
        #  (dead-engine) --> Action      --> NodeLock
        #                    |action|owner|  |node |action|
        #                    | A1   | E1  |  |N1   |A1    |
        #                                --> ClusterLock
        #                                    |cluster|action  |scope|
        #                                    |C1     |[A1, A2]|2    |
        # preparation
        engine_id = UUID1
        action = shared.create_action(self.ctx, target=self.node.id,
                                      status='RUNNING', owner=engine_id,
                                      project=self.ctx.project)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, 1)
        db_api.cluster_lock_acquire(self.cluster.id, UUID2, 1)
        db_api.node_lock_acquire(self.node.id, action.id)

        # do it
        db_api.gc_by_engine(self.ctx, engine_id)

        # assertion
        # a read lock is okay now and cluster lock state not broken
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, 1)
        self.assertIn(UUID2, observed)
        self.assertIn(UUID3, observed)
        self.assertNotIn(action.id, observed)

        # node can be locked again
        observed = db_api.node_lock_acquire(self.node.id, UUID2)
        self.assertEqual(UUID2, observed)

        new_action = db_api.action_get(self.ctx, action.id)
        self.assertEqual('FAILED', new_action.status)
        self.assertEqual("Engine failure", new_action.status_reason)
