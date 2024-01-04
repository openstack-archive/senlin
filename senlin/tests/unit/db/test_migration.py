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
# Based on Nova's test_migrations.py


import os

from alembic import command as alembic_api
from alembic import config as alembic_config
from alembic import script as alembic_script
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures
from oslo_log import log as logging

from senlin.db import sqlalchemy
from senlin.tests.unit.common import base


LOG = logging.getLogger(__name__)
ALEMBIC_PATH = os.path.join(
    os.path.dirname(sqlalchemy.__file__), 'alembic.ini'
)


class SenlinMigrationsWalk(
    test_fixtures.OpportunisticDBTestMixin, base.SenlinTestCase,
):
    # Migrations can take a long time, particularly on underpowered CI nodes.
    # Give them some breathing room.
    TIMEOUT_SCALING_FACTOR = 4

    def setUp(self):
        super().setUp()
        self.engine = enginefacade.writer.get_engine()
        self.config = alembic_config.Config(ALEMBIC_PATH)
        self.init_version = '569eb0b8'

    def _migrate_up(self, connection, revision):
        if revision == self.init_version:  # no tests for the initial revision
            alembic_api.upgrade(self.config, revision)
            return

        self.assertIsNotNone(
            getattr(self, '_check_%s' % revision, None),
            (
                'DB Migration %s does not have a test; you must add one'
            ) % revision,
        )

        pre_upgrade = getattr(self, '_pre_upgrade_%s' % revision, None)
        if pre_upgrade:
            pre_upgrade(connection)

        alembic_api.upgrade(self.config, revision)

        post_upgrade = getattr(self, '_check_%s' % revision, None)
        if post_upgrade:
            post_upgrade(connection)

    def _check_6f73af60(self, connection):
        pass

    def _check_c3e2bfa76dea(self, connection):
        pass

    def _check_ab7b23c67360(self, connection):
        pass

    def _check_662f8e74ac6f(self, connection):
        pass

    def _check_9dbb563afc4d(self, connection):
        pass

    def _check_0c04e812f224(self, connection):
        pass

    def _check_5b7cb185e0a5(self, connection):
        pass

    def _check_3a04debb8cb1(self, connection):
        pass

    def _check_beffe13cf8e5(self, connection):
        pass

    def _check_aaa7e7755feb(self, connection):
        pass

    def _check_004f8202c264(self, connection):
        pass

    def test_single_base_revision(self):
        script = alembic_script.ScriptDirectory.from_config(self.config)
        self.assertEqual(1, len(script.get_bases()))

    def test_walk_versions(self):
        with self.engine.begin() as connection:
            self.config.attributes['connection'] = connection
            script = alembic_script.ScriptDirectory.from_config(self.config)
            revisions = [x.revision for x in script.walk_revisions()]

            # for some reason, 'walk_revisions' gives us the revisions in
            # reverse chronological order, so we have to invert this
            revisions.reverse()
            self.assertEqual(revisions[0], self.init_version)

            for revision in revisions:
                LOG.info('Testing revision %s', revision)
                self._migrate_up(connection, revision)


class TestMigrationsWalkSQLite(
    SenlinMigrationsWalk,
    test_fixtures.OpportunisticDBTestMixin,
):
    pass
