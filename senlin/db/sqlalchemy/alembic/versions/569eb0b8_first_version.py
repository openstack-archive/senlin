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

"""First version

Revision ID: 569eb0b8
Revises:
Create Date: 2023-03-25 14:35:24.421351

"""
from alembic import op
import sqlalchemy as sa

from senlin.db.sqlalchemy.alembic import legacy_utils
from senlin.db.sqlalchemy import types

# revision identifiers, used by Alembic.
revision = '569eb0b8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if the equivalent legacy migration has already run
    if not legacy_utils.is_migration_needed(1):
        return

    metadata = sa.MetaData()

    op.create_table(
        'profile', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('type', sa.String(255)),
        sa.Column('context', types.Dict),
        sa.Column('spec', types.Dict),
        sa.Column('user', sa.String(32), nullable=False),
        sa.Column('project', sa.String(32), nullable=False),
        sa.Column('domain', sa.String(32)),
        sa.Column('permission', sa.String(32)),
        sa.Column('meta_data', types.Dict),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'cluster', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('profile.id'),
                  nullable=False),
        sa.Column('user', sa.String(32), nullable=False),
        sa.Column('project', sa.String(32), nullable=False),
        sa.Column('domain', sa.String(32)),
        sa.Column('parent', sa.String(36)),
        sa.Column('init_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('min_size', sa.Integer),
        sa.Column('max_size', sa.Integer),
        sa.Column('desired_capacity', sa.Integer),
        sa.Column('next_index', sa.Integer),
        sa.Column('timeout', sa.Integer),
        sa.Column('status', sa.String(255)),
        sa.Column('status_reason', sa.Text),
        sa.Column('meta_data', types.Dict),
        sa.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'node', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('physical_id', sa.String(36)),
        sa.Column('cluster_id', sa.String(36)),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('profile.id'),
                  nullable=False),
        sa.Column('user', sa.String(32)),
        sa.Column('project', sa.String(32)),
        sa.Column('domain', sa.String(32)),
        sa.Column('index', sa.Integer),
        sa.Column('role', sa.String(64)),
        sa.Column('init_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('status', sa.String(255)),
        sa.Column('status_reason', sa.Text),
        sa.Column('meta_data', types.Dict),
        sa.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'cluster_lock', metadata,
        sa.Column('cluster_id', sa.String(36), primary_key=True,
                  nullable=False),
        sa.Column('action_ids', types.List),
        sa.Column('semaphore', sa.Integer),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'node_lock', metadata,
        sa.Column('node_id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('action_id', sa.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'policy', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('type', sa.String(255)),
        sa.Column('user', sa.String(32), nullable=False),
        sa.Column('project', sa.String(32), nullable=False),
        sa.Column('domain', sa.String(32)),
        sa.Column('cooldown', sa.Integer),
        sa.Column('level', sa.Integer),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('spec', types.Dict),
        sa.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'cluster_policy', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('cluster_id', sa.String(36), sa.ForeignKey('cluster.id'),
                  nullable=False),
        sa.Column('policy_id', sa.String(36), sa.ForeignKey('policy.id'),
                  nullable=False),
        sa.Column('cooldown', sa.Integer),
        sa.Column('priority', sa.Integer),
        sa.Column('level', sa.Integer),
        sa.Column('enabled', sa.Boolean),
        sa.Column('data', types.Dict),
        sa.Column('last_op', sa.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'receiver', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('type', sa.String(255)),
        sa.Column('user', sa.String(32)),
        sa.Column('project', sa.String(32)),
        sa.Column('domain', sa.String(32)),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('cluster_id', sa.String(36)),
        sa.Column('actor', types.Dict),
        sa.Column('action', sa.Text),
        sa.Column('params', types.Dict),
        sa.Column('channel', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'credential', metadata,
        sa.Column('user', sa.String(32), primary_key=True, nullable=False),
        sa.Column('project', sa.String(32), primary_key=True, nullable=False),
        sa.Column('cred', types.Dict, nullable=False),
        sa.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'action', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('name', sa.String(63)),
        sa.Column('context', types.Dict),
        sa.Column('target', sa.String(36)),
        sa.Column('action', sa.Text),
        sa.Column('cause', sa.String(255)),
        sa.Column('owner', sa.String(36)),
        sa.Column('interval', sa.Integer),
        # FIXME: Don't specify fixed precision.
        sa.Column('start_time', sa.Float(precision='24,8')),
        sa.Column('end_time', sa.Float(precision='24,8')),
        sa.Column('timeout', sa.Integer),
        sa.Column('control', sa.String(255)),
        sa.Column('status', sa.String(255)),
        sa.Column('status_reason', sa.Text),
        sa.Column('inputs', types.Dict),
        sa.Column('outputs', types.Dict),
        sa.Column('depends_on', types.List),
        sa.Column('depended_by', types.List),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'dependency', metadata,
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('depended', sa.String(36), sa.ForeignKey('action.id'),
                  nullable=False),
        sa.Column('dependent', sa.String(36), sa.ForeignKey('action.id'),
                  nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    op.create_table(
        'event', metadata,
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('obj_id', sa.String(36)),
        sa.Column('obj_name', sa.String(255)),
        sa.Column('obj_type', sa.String(36)),
        sa.Column('cluster_id', sa.String(36)),
        sa.Column('level', sa.String(63)),
        sa.Column('user', sa.String(32)),
        sa.Column('project', sa.String(32)),
        sa.Column('action', sa.String(36)),
        sa.Column('status', sa.String(255)),
        sa.Column('status_reason', sa.Text),
        sa.Column('meta_data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
