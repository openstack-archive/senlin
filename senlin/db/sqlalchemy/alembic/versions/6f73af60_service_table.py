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

"""Service table

Revision ID: 6f73af60
Revises: 569eb0b8
Create Date: 2023-03-25 14:35:25.221356

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils

# revision identifiers, used by Alembic.
revision = '6f73af60'
down_revision = '569eb0b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(2):
        return

    metadata = sa.MetaData()

    op.create_table(
        'service', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('host', sa.String(255)),
        sa.Column('binary', sa.String(255)),
        sa.Column('topic', sa.String(255)),
        sa.Column('disabled', sa.Boolean),
        sa.Column('disabled_reason', sa.String(255)),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
