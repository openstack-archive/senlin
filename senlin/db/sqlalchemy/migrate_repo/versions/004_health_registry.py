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

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, MetaData, String, Table
from senlin.db.sqlalchemy import types


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    cluster = Table('cluster', meta, autoload=True)

    health_registry = Table(
        'health_registry', meta,
        Column('id', String(36), primary_key=True, nullable=False),
        Column('cluster_id', String(36), ForeignKey(cluster.c.id),
               nullable=False),
        Column('check_type', String(255)),
        Column('interval', Integer),
        Column('params', types.Dict),
        Column('engine_id', String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    health_registry.create()


def downgrade(migrate_engine):
    raise NotImplementedError('Database downgrade not supported - '
                              'would drop all tables')
