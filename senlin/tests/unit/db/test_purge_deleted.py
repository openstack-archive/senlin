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

import datetime

from oslo_utils import timeutils

from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared


class DBAPIPurgeTest(base.SenlinTestCase):

    def setUp(self):
        super(DBAPIPurgeTest, self).setUp()
        self.ctx = utils.dummy_context()

    def create_objects(self, deleted_time=None):
        profile = shared.create_profile(self.ctx,
                                        deleted_time=deleted_time)
        cluster = shared.create_cluster(self.ctx, profile,
                                        deleted_time=deleted_time)
        shared.create_node(self.ctx, cluster, profile,
                           deleted_time=deleted_time)
        shared.create_policy(self.ctx, deleted_time=deleted_time)
        shared.create_action(self.ctx, deleted_time=deleted_time)
        shared.create_event(self.ctx, deleted_time=deleted_time)

    def verify_left(self, count):
        profiles = db_api.profile_get_all(self.ctx, show_deleted=True)
        self.assertEqual(count, len(profiles))
        clusters = db_api.cluster_get_all(self.ctx, show_deleted=True)
        self.assertEqual(count, len(clusters))
        nodes = db_api.node_get_all(self.ctx, show_deleted=True)
        self.assertEqual(count, len(nodes))
        policies = db_api.policy_get_all(self.ctx, show_deleted=True)
        self.assertEqual(count, len(policies))
        actions = db_api.action_get_all(self.ctx, show_deleted=True)
        self.assertEqual(count, len(actions))
        events = db_api.event_get_all(self.ctx, show_deleted=True)
        self.assertEqual(count, len(events))

    def test_purge_deleted(self):
        now = timeutils.utcnow()
        delta = datetime.timedelta(seconds=3600 * 9)
        for i in range(1, 7):
            deleted_at = now - delta * i
            self.create_objects(deleted_at)

        self.verify_left(6)

        db_api.purge_deleted(age=2, unit='days')
        self.verify_left(5)

        db_api.purge_deleted(age=44, unit='hours')
        self.verify_left(4)

        # 35 hours
        db_api.purge_deleted(age=35, unit='hours')
        self.verify_left(3)

        # 25 hours
        db_api.purge_deleted(age=1500, unit='minutes')
        self.verify_left(2)

        # 15 hours
        db_api.purge_deleted(age=900, unit='minutes')
        self.verify_left(1)

        # 5 hours
        db_api.purge_deleted(age=18000, unit='seconds')
        self.verify_left(0)
