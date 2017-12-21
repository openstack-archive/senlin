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

from oslo_utils import uuidutils
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
                                      project=self.ctx.project_id)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, -1)

        # do it
        db_api.gc_by_engine(engine_id)

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
                                      project=self.ctx.project_id)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, 1)
        db_api.node_lock_acquire(self.cluster.id, action.id)

        # do it
        db_api.gc_by_engine(engine_id)

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
                                      project=self.ctx.project_id)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, 1)
        db_api.cluster_lock_acquire(self.cluster.id, UUID2, 1)
        db_api.node_lock_acquire(self.node.id, action.id)

        # do it
        db_api.gc_by_engine(engine_id)

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


class DummyGCByEngineTest(base.SenlinTestCase):

    def setUp(self):
        super(DummyGCByEngineTest, self).setUp()
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
                                      project=self.ctx.project_id)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, -1)

        # do it
        db_api.dummy_gc(engine_id)

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
                                      project=self.ctx.project_id)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, 1)
        db_api.node_lock_acquire(self.cluster.id, action.id)

        # do it
        db_api.dummy_gc(engine_id)

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
                                      project=self.ctx.project_id)
        db_api.cluster_lock_acquire(self.cluster.id, action.id, 1)
        db_api.cluster_lock_acquire(self.cluster.id, UUID2, 1)
        db_api.node_lock_acquire(self.node.id, action.id)

        # do it
        db_api.dummy_gc(engine_id)

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

    def test_mult_engine_keep_node_scope_lock(self):
        engine1 = UUID1
        engine2 = UUID2

        node2 = shared.create_node(self.ctx, self.cluster, self.profile)

        c_action = shared.create_action(self.ctx, target=self.cluster.id,
                                        status='WAITING', owner=engine1,
                                        project=self.ctx.project_id)

        n_action_1 = shared.create_action(self.ctx, target=self.node.id,
                                          status='RUNNING', owner=engine1,
                                          project=self.ctx.project_id)

        n_action_2 = shared.create_action(self.ctx, target=node2.id,
                                          status='RUNNING', owner=engine2,
                                          project=self.ctx.project_id)

        db_api.dependency_add(self.ctx, [n_action_1.id, n_action_2.id],
                              c_action.id)

        db_api.cluster_lock_acquire(self.cluster.id, c_action.id, -1)
        db_api.cluster_lock_acquire(self.cluster.id, n_action_1.id, 1)
        db_api.cluster_lock_acquire(self.cluster.id, n_action_2.id, 1)
        db_api.node_lock_acquire(self.node.id, n_action_1.id)
        db_api.node_lock_acquire(node2.id, n_action_2.id)

        # do it
        db_api.dummy_gc(engine1)

        # try to acquire cluster scope lock
        observed = db_api.cluster_lock_acquire(self.cluster.id, UUID3, -1)
        self.assertIn(UUID3, observed)
        self.assertEqual(1, len(observed))

        # try to acquire node scope lock
        UUID4 = uuidutils.generate_uuid()
        observed = db_api.cluster_lock_acquire(self.node.id, UUID4, 1)
        self.assertIn(UUID4, observed)
        self.assertEqual(1, len(observed))

        # node scope lock will be also released
        UUID5 = uuidutils.generate_uuid()
        observed = db_api.cluster_lock_acquire(node2.id, UUID5, 1)
        self.assertIn(UUID5, observed)
        self.assertEqual(1, len(observed))

        # try to acquire node lock
        UUID6 = uuidutils.generate_uuid()
        observed = db_api.node_lock_acquire(self.node.id, UUID6)
        self.assertEqual(UUID6, observed)

        # node locks for actions owned by other engines are still there
        UUID7 = uuidutils.generate_uuid()
        observed = db_api.node_lock_acquire(node2.id, UUID7)
        self.assertNotEqual(UUID7, observed)
        self.assertEqual(n_action_2.id, observed)

        # check dependency
        dependents = db_api.dependency_get_depended(self.ctx, c_action.id)
        self.assertEqual(0, len(dependents))

        # check action status
        new_c_action = db_api.action_get(self.ctx, c_action.id)
        self.assertEqual('FAILED', new_c_action.status)
        self.assertIsNone(new_c_action.owner)

        new_n_action_1 = db_api.action_get(self.ctx, n_action_1.id)
        self.assertEqual('FAILED', new_n_action_1.status)
        self.assertIsNone(new_n_action_1.owner)

        new_n_action_2 = db_api.action_get(self.ctx, n_action_2.id)
        self.assertEqual('FAILED', new_n_action_2.status)
        self.assertIsNone(new_n_action_2.owner)
