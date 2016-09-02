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

from sqlalchemy import Column, MetaData, Table

from senlin.db.sqlalchemy import types


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    node = Table('node', meta, autoload=True)
    node_dependents = Column('dependents', types.Dict())
    node_dependents.create(node)

    cluster = Table('cluster', meta, autoload=True)
    cluster_dependents = Column('dependents', types.Dict())
    cluster_dependents.create(cluster)
