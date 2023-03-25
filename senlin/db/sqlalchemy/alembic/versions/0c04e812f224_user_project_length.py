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

"""user project length

Revision ID: 0c04e812f224
Revises: 9dbb563afc4d
Create Date: 2023-03-25 14:36:03.881164

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils

# revision identifiers, used by Alembic.
revision = '0c04e812f224'
down_revision = '9dbb563afc4d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(10):
        return

    for table_name in ['profile', 'policy', 'cluster', 'credential']:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                'user', type_=sa.String(64),
                nullabe=False,
                existing_nullable=False,
                existing_type=sa.String(32)
            )

        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                'project', type_=sa.String(64),
                nullabe=False,
                existing_nullable=False,
                existing_type=sa.String(32)
            )

    for table_name in ['node', 'receiver', 'action', 'event']:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                'user', type_=sa.String(64), existing_type=sa.String(32)
            )

        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                'project', type_=sa.String(64), existing_type=sa.String(32)
            )

    for table_name in ['profile', 'policy', 'cluster', 'node', 'receiver',
                       'action']:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                'domain', type_=sa.String(64), existing_type=sa.String(32)
            )
