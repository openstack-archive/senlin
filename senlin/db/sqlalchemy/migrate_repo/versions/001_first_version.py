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

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey
from sqlalchemy import Integer, MetaData, String, Table, Text
from senlin.db.sqlalchemy import types


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    profile = Table(
        'profile', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('name', String(255)),
        Column('type', String(255)),
        Column('context', types.Dict),
        Column('spec', types.Dict),
        Column('user', String(32), nullable=False),
        Column('project', String(32), nullable=False),
        Column('domain', String(32)),
        Column('permission', String(32)),
        Column('meta_data', types.Dict),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster = Table(
        'cluster', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('name', String(255), nullable=False),
        Column('profile_id', String(36), ForeignKey('profile.id'),
               nullable=False),
        Column('user', String(32), nullable=False),
        Column('project', String(32), nullable=False),
        Column('domain', String(32)),
        Column('parent', String(36)),
        Column('init_at', DateTime),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('min_size', Integer),
        Column('max_size', Integer),
        Column('desired_capacity', Integer),
        Column('next_index', Integer),
        Column('timeout', Integer),
        Column('status', String(255)),
        Column('status_reason', Text),
        Column('meta_data', types.Dict),
        Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    node = Table(
        'node', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('name', String(255)),
        Column('physical_id', String(36)),
        Column('cluster_id', String(36)),
        Column('profile_id', String(36), ForeignKey('profile.id'),
               nullable=False),
        Column('user', String(32)),
        Column('project', String(32)),
        Column('domain', String(32)),
        Column('index', Integer),
        Column('role', String(64)),
        Column('init_at', DateTime),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('status', String(255)),
        Column('status_reason', Text),
        Column('meta_data', types.Dict),
        Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster_lock = Table(
        'cluster_lock', meta,
        Column('cluster_id', String(36), primary_key=True, nullable=False),
        Column('action_ids', types.List),
        Column('semaphore', Integer),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    node_lock = Table(
        'node_lock', meta,
        Column('node_id', String(36), primary_key=True, nullable=False),
        Column('action_id', String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    policy = Table(
        'policy', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('name', String(255)),
        Column('type', String(255)),
        Column('user', String(32), nullable=False),
        Column('project', String(32), nullable=False),
        Column('domain', String(32)),
        Column('cooldown', Integer),
        Column('level', Integer),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('spec', types.Dict),
        Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster_policy = Table(
        'cluster_policy', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('cluster_id', String(36), ForeignKey('cluster.id'),
               nullable=False),
        Column('policy_id', String(36), ForeignKey('policy.id'),
               nullable=False),
        Column('cooldown', Integer),
        Column('priority', Integer),
        Column('level', Integer),
        Column('enabled', Boolean),
        Column('data', types.Dict),
        Column('last_op', DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    receiver = Table(
        'receiver', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('name', String(255)),
        Column('type', String(255)),
        Column('user', String(32)),
        Column('project', String(32)),
        Column('domain', String(32)),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('cluster_id', String(36)),
        Column('actor', types.Dict),
        Column('action', Text),
        Column('params', types.Dict),
        Column('channel', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    credential = Table(
        'credential', meta,
        Column('user', String(32), primary_key=True, nullable=False),
        Column('project', String(32), primary_key=True, nullable=False),
        Column('cred', types.Dict, nullable=False),
        Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    action = Table(
        'action', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('name', String(63)),
        Column('context', types.Dict),
        Column('target', String(36)),
        Column('action', Text),
        Column('cause', String(255)),
        Column('owner', String(36)),
        Column('interval', Integer),
        # FIXME: Don't specify fixed precision.
        Column('start_time', Float(precision='24,8')),
        Column('end_time', Float(precision='24,8')),
        Column('timeout', Integer),
        Column('control', String(255)),
        Column('status', String(255)),
        Column('status_reason', Text),
        Column('inputs', types.Dict),
        Column('outputs', types.Dict),
        Column('depends_on', types.List),
        Column('depended_by', types.List),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    dependency = Table(
        'dependency', meta,
        Column('id', String(36), nullable=False, primary_key=True),
        Column('depended', String(36), ForeignKey('action.id'),
               nullable=False),
        Column('dependent', String(36), ForeignKey('action.id'),
               nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    event = Table(
        'event', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('timestamp', DateTime, nullable=False),
        Column('obj_id', String(36)),
        Column('obj_name', String(255)),
        Column('obj_type', String(36)),
        Column('cluster_id', String(36)),
        Column('level', String(63)),
        Column('user', String(32)),
        Column('project', String(32)),
        Column('action', String(36)),
        Column('status', String(255)),
        Column('status_reason', Text),
        Column('meta_data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    tables = (
        profile,
        cluster,
        node,
        cluster_lock,
        node_lock,
        policy,
        cluster_policy,
        credential,
        action,
        dependency,
        receiver,
        event,
    )

    for index, table in enumerate(tables):
        try:
            table.create()
        except Exception:
            # If an error occurs, drop all tables created so far to return
            # to the previously existing state.
            meta.drop_all(tables=tables[:index])
            raise


def downgrade(migrate_engine):
    raise NotImplementedError('Database downgrade not supported - '
                              'would drop all tables')
