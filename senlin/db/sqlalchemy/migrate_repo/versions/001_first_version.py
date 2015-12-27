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

import sqlalchemy

from senlin.db.sqlalchemy import types


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine

    profile = sqlalchemy.Table(
        'profile', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('type', sqlalchemy.String(255)),
        sqlalchemy.Column('context', types.Dict),
        sqlalchemy.Column('spec', types.Dict),
        sqlalchemy.Column('user', sqlalchemy.String(32), nullable=False),
        sqlalchemy.Column('project', sqlalchemy.String(32), nullable=False),
        sqlalchemy.Column('domain', sqlalchemy.String(32)),
        sqlalchemy.Column('permission', sqlalchemy.String(32)),
        sqlalchemy.Column('meta_data', types.Dict),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster = sqlalchemy.Table(
        'cluster', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255),
                          nullable=False),
        sqlalchemy.Column('profile_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('profile.id'),
                          nullable=False),
        sqlalchemy.Column('user', sqlalchemy.String(32), nullable=False),
        sqlalchemy.Column('project', sqlalchemy.String(32), nullable=False),
        sqlalchemy.Column('domain', sqlalchemy.String(32)),
        sqlalchemy.Column('parent', sqlalchemy.String(36)),
        sqlalchemy.Column('init_time', sqlalchemy.DateTime),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('min_size', sqlalchemy.Integer),
        sqlalchemy.Column('max_size', sqlalchemy.Integer),
        sqlalchemy.Column('desired_capacity', sqlalchemy.Integer),
        sqlalchemy.Column('next_index', sqlalchemy.Integer),
        sqlalchemy.Column('timeout', sqlalchemy.Integer),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('meta_data', types.Dict),
        sqlalchemy.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    node = sqlalchemy.Table(
        'node', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('physical_id', sqlalchemy.String(36)),
        sqlalchemy.Column('cluster_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('cluster.id')),
        sqlalchemy.Column('profile_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('profile.id'),
                          nullable=False),
        sqlalchemy.Column('user', sqlalchemy.String(32)),
        sqlalchemy.Column('project', sqlalchemy.String(32)),
        sqlalchemy.Column('domain', sqlalchemy.String(32)),
        sqlalchemy.Column('index', sqlalchemy.Integer),
        sqlalchemy.Column('role', sqlalchemy.String(64)),
        sqlalchemy.Column('init_time', sqlalchemy.DateTime),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('meta_data', types.Dict),
        sqlalchemy.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster_lock = sqlalchemy.Table(
        'cluster_lock', meta,
        sqlalchemy.Column('cluster_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('cluster.id'),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('action_ids', types.List),
        sqlalchemy.Column('semaphore', sqlalchemy.Integer),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    node_lock = sqlalchemy.Table(
        'node_lock', meta,
        sqlalchemy.Column('node_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('node.id'),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('action_id', sqlalchemy.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    policy = sqlalchemy.Table(
        'policy', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('type', sqlalchemy.String(255)),
        sqlalchemy.Column('user', sqlalchemy.String(32), nullable=False),
        sqlalchemy.Column('project', sqlalchemy.String(32), nullable=False),
        sqlalchemy.Column('domain', sqlalchemy.String(32)),
        sqlalchemy.Column('cooldown', sqlalchemy.Integer),
        sqlalchemy.Column('level', sqlalchemy.Integer),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('spec', types.Dict),
        sqlalchemy.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster_policy = sqlalchemy.Table(
        'cluster_policy', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('cluster_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('cluster.id'),
                          nullable=False),
        sqlalchemy.Column('policy_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('policy.id'),
                          nullable=False),
        sqlalchemy.Column('cooldown', sqlalchemy.Integer),
        sqlalchemy.Column('priority', sqlalchemy.Integer),
        sqlalchemy.Column('level', sqlalchemy.Integer),
        sqlalchemy.Column('enabled', sqlalchemy.Boolean),
        sqlalchemy.Column('data', types.Dict),
        sqlalchemy.Column('last_op', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    receiver = sqlalchemy.Table(
        'receiver', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('type', sqlalchemy.String(255)),
        sqlalchemy.Column('user', sqlalchemy.String(32)),
        sqlalchemy.Column('project', sqlalchemy.String(32)),
        sqlalchemy.Column('domain', sqlalchemy.String(32)),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('cluster_id', sqlalchemy.String(36)),
        sqlalchemy.Column('actor', types.Dict),
        sqlalchemy.Column('action', sqlalchemy.Text),
        sqlalchemy.Column('params', types.Dict),
        sqlalchemy.Column('channel', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    credential = sqlalchemy.Table(
        'credential', meta,
        sqlalchemy.Column('user', sqlalchemy.String(32), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('project', sqlalchemy.String(32), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('cred', types.Dict, nullable=False),
        sqlalchemy.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    action = sqlalchemy.Table(
        'action', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(63)),
        sqlalchemy.Column('context', types.Dict),
        sqlalchemy.Column('target', sqlalchemy.String(36)),
        sqlalchemy.Column('action', sqlalchemy.Text),
        sqlalchemy.Column('cause', sqlalchemy.String(255)),
        sqlalchemy.Column('owner', sqlalchemy.String(36)),
        sqlalchemy.Column('interval', sqlalchemy.Integer),
        # FIXME: Don't specify fixed precision.
        sqlalchemy.Column('start_time', sqlalchemy.Float(precision='24,8')),
        sqlalchemy.Column('end_time', sqlalchemy.Float(precision='24,8')),
        sqlalchemy.Column('timeout', sqlalchemy.Integer),
        sqlalchemy.Column('control', sqlalchemy.String(255)),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('inputs', types.Dict),
        sqlalchemy.Column('outputs', types.Dict),
        sqlalchemy.Column('depends_on', types.List),
        sqlalchemy.Column('depended_by', types.List),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    dependency = sqlalchemy.Table(
        'dependency', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), nullable=False,
                          primary_key=True),
        sqlalchemy.Column('depended', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('action.id'), nullable=False),
        sqlalchemy.Column('dependent', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('action.id'), nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    event = sqlalchemy.Table(
        'event', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('timestamp', sqlalchemy.DateTime, nullable=False),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('obj_id', sqlalchemy.String(36)),
        sqlalchemy.Column('obj_name', sqlalchemy.String(255)),
        sqlalchemy.Column('obj_type', sqlalchemy.String(36)),
        sqlalchemy.Column('cluster_id', sqlalchemy.String(36)),
        sqlalchemy.Column('level', sqlalchemy.String(63)),
        sqlalchemy.Column('user', sqlalchemy.String(32)),
        sqlalchemy.Column('project', sqlalchemy.String(32)),
        sqlalchemy.Column('action', sqlalchemy.String(36)),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('meta_data', types.Dict),
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
