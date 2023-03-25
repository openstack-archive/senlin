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

"""action starttime endtime type

Revision ID: beffe13cf8e5
Revises: 3a04debb8cb1
Create Date: 2023-03-25 14:36:21.522415

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils

# revision identifiers, used by Alembic.
revision = 'beffe13cf8e5'
down_revision = '3a04debb8cb1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(13):
        return

    with op.batch_alter_table('action') as batch_op:
        batch_op.alter_column('start_time', type_=sa.Numeric('18,6'),
                              existing_type=sa.Numeric('24,8'))

    with op.batch_alter_table('action') as batch_op:
        batch_op.alter_column('end_time', type_=sa.Numeric('18,6'),
                              existing_type=sa.Numeric('24,8'))
