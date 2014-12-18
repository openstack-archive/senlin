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
        sqlalchemy.Column('spec', types.Json),
        sqlalchemy.Column('permission', sqlalchemy.String(32)),
        sqlalchemy.Column('tags', types.Json),
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
        sqlalchemy.Column('user', sqlalchemy.String(36)),
        sqlalchemy.Column('project', sqlalchemy.String(36)),
        sqlalchemy.Column('domain', sqlalchemy.String(36)),
        sqlalchemy.Column('parent', sqlalchemy.String(36)),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('next_index', sqlalchemy.Integer),
        sqlalchemy.Column('timeout', sqlalchemy.Integer),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.String(255)),
        sqlalchemy.Column('tags', types.Json),
        sqlalchemy.Column('data', types.Json),
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
        sqlalchemy.Column('index', sqlalchemy.Integer),
        sqlalchemy.Column('role', sqlalchemy.String(64)),
        sqlalchemy.Column('created_time', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_time', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_time', sqlalchemy.DateTime),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.String(255)),
        sqlalchemy.Column('tags', types.Json),
        sqlalchemy.Column('data', types.Json),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    cluster_lock = sqlalchemy.Table(
        'cluster_lock', meta,
        sqlalchemy.Column('cluster_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('cluster.id'),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('worker_id', sqlalchemy.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    node_lock = sqlalchemy.Table(
        'node_lock', meta,
        sqlalchemy.Column('node_id', sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('node.id'),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('worker_id', sqlalchemy.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    policy = sqlalchemy.Table(
        'policy', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('type', sqlalchemy.String(255)),
        sqlalchemy.Column('coolcown', sqlalchemy.Integer),
        sqlalchemy.Column('level', sqlalchemy.Integer),
        sqlalchemy.Column('spec', types.Json),
        sqlalchemy.Column('data', types.Json),
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
        sqlalchemy.Column('coolcown', sqlalchemy.Integer),
        sqlalchemy.Column('level', sqlalchemy.Integer),
        sqlalchemy.Column('enabled', sqlalchemy.Boolean),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    action = sqlalchemy.Table(
        'action', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(63)),
        sqlalchemy.Column('context', types.Json),
        sqlalchemy.Column('target', sqlalchemy.String(36)),
        sqlalchemy.Column('action', types.LongText),
        sqlalchemy.Column('cause', sqlalchemy.String(255)),
        sqlalchemy.Column('owner', sqlalchemy.String(36)),
        sqlalchemy.Column('interval', sqlalchemy.Integer),
        sqlalchemy.Column('start_time', sqlalchemy.String(255)),
        sqlalchemy.Column('end_time', sqlalchemy.String(255)),
        sqlalchemy.Column('timeout', sqlalchemy.Integer),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.String(255)),
        sqlalchemy.Column('inputs', types.Json),
        sqlalchemy.Column('outputs', types.Json),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    event = sqlalchemy.Table(
        'event', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('timestamp', sqlalchemy.DateTime, nullable=False),
        sqlalchemy.Column('obj_id', sqlalchemy.String(36)),
        sqlalchemy.Column('obj_name', sqlalchemy.String(255)),
        sqlalchemy.Column('obj_type', sqlalchemy.String(36)),
        sqlalchemy.Column('user', sqlalchemy.String(36)),
        sqlalchemy.Column('action', sqlalchemy.String(36)),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.String(255)),
        sqlalchemy.Column('tags', types.Json),
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
        action,
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
