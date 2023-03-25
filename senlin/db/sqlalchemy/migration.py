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
import os
import sys

from alembic import command as alembic_command
from alembic.config import Config
from alembic import migration as alembic_migration
from oslo_config import cfg

from senlin.db.sqlalchemy import api as db_api

CONF = cfg.CONF


def get_alembic_config(db_url=None):
    alembic_dir = os.path.join(os.path.dirname(__file__),
                               os.pardir, 'db/sqlalchemy')
    alembic_cfg = Config(os.path.join(alembic_dir, 'alembic.ini'),
                         stdout=sys.stdout)
    alembic_cfg.set_main_option(
        'script_location', 'senlin.db.sqlalchemy:alembic')
    if db_url:
        alembic_cfg.set_main_option('sqlalchemy.url', db_url)
    else:
        alembic_cfg.set_main_option('sqlalchemy.url',
                                    CONF['database'].connection)
    return alembic_cfg


def db_sync(db_url):
    alembic_command.upgrade(
        get_alembic_config(db_url), 'head'
    )


def db_version():
    engine = db_api.get_engine()
    with engine.connect() as connection:
        m_context = alembic_migration.MigrationContext.configure(connection)
        return m_context.get_current_revision()
