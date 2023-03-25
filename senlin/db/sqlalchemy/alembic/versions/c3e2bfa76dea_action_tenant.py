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

"""action tenant

Revision ID: c3e2bfa76dea
Revises: 6f73af60
Create Date: 2023-03-25 14:35:26.721352

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils

# revision identifiers, used by Alembic.
revision = 'c3e2bfa76dea'
down_revision = '6f73af60'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(3):
        return

    op.add_column('action', sa.Column('user', sa.String(32)))
    op.add_column('action', sa.Column('project', sa.String(32)))
    op.add_column('action', sa.Column('domain', sa.String(32)))
