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

"""node cluster dependents column

Revision ID: 9dbb563afc4d
Revises: 662f8e74ac6f
Create Date: 2023-03-25 14:35:52.059731

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils
from senlin.db.sqlalchemy import types

# revision identifiers, used by Alembic.
revision = '9dbb563afc4d'
down_revision = '662f8e74ac6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(6):
        return

    op.add_column('node', sa.Column('dependents', types.Dict()))
    op.add_column('cluster', sa.Column('dependents', types.Dict()))
