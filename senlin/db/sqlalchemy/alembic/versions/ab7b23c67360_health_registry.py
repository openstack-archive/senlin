#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""health registry

Revision ID: ab7b23c67360
Revises: c3e2bfa76dea
Create Date: 2023-03-25 14:35:33.776610

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils
from senlin.db.sqlalchemy import types

# revision identifiers, used by Alembic.
revision = 'ab7b23c67360'
down_revision = 'c3e2bfa76dea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(4):
        return

    metadata = sa.MetaData()

    cluster = sa.Table('cluster', metadata, autoload_with=op.get_bind())
    op.create_table(
        'health_registry', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('cluster_id', sa.String(36), sa.ForeignKey(cluster.c.id),
                  nullable=False),
        sa.Column('check_type', sa.String(255)),
        sa.Column('interval', sa.Integer),
        sa.Column('params', types.Dict),
        sa.Column('engine_id', sa.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
