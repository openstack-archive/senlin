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

"""event column name

Revision ID: 662f8e74ac6f
Revises: ab7b23c67360
Create Date: 2023-03-25 14:35:44.367382

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils

# revision identifiers, used by Alembic.
revision = '662f8e74ac6f'
down_revision = 'ab7b23c67360'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(5):
        return

    with op.batch_alter_table('event') as batch_op:
        batch_op.alter_column('obj_id', new_column_name='oid',
                              existing_type=sa.String(36))

    with op.batch_alter_table('event') as batch_op:
        batch_op.alter_column('obj_name', new_column_name='oname',
                              existing_type=sa.String(255))

    with op.batch_alter_table('event') as batch_op:
        batch_op.alter_column('obj_type', new_column_name='otype',
                              existing_type=sa.String(36))
