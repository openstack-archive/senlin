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

"""action clusterid

Revision ID: 004f8202c264
Revises: aaa7e7755feb
Create Date: 2023-03-25 14:36:31.844399

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils

# revision identifiers, used by Alembic.
revision = '004f8202c264'
down_revision = 'aaa7e7755feb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(15):
        return

    op.add_column('action', sa.Column('cluster_id', sa.String(36), default=''))
