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

"""
SQLAlchemy models for Senlin data.
"""

import uuid

from oslo.db.sqlalchemy import models
from oslo.utils import timeutils
import six
import sqlalchemy
from sqlalchemy.ext import declarative
from sqlalchemy.orm import session as orm_session

from senlin.db.sqlalchemy import types

BASE = declarative.declarative_base()


def get_session():
    from senlin.db.sqlalchemy import api as db_api
    return db_api.get_session()


class SenlinBase(models.ModelBase):
    """Base class for Senlin Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def expire(self, session=None, attrs=None):
        if not session:
            session = orm_session.Session.object_session(self)
            if not session:
                session = get_session()
        session.expire(self, attrs)

    def refresh(self, session=None, attrs=None):
        """Refresh this object."""
        if not session:
            session = orm_session.Session.object_session(self)
            if not session:
                session = get_session()
        session.refresh(self, attrs)

    def delete(self, session=None):
        """Delete this object."""
        if not session:
            session = orm_session.Session.object_session(self)
            if not session:
                session = get_session()
        session.begin()
        session.delete(self)
        session.commit()

    def update_and_save(self, values, session=None):
        if not session:
            session = orm_session.Session.object_session(self)
            if not session:
                session = get_session()
        session.begin()
        for k, v in six.iteritems(values):
            setattr(self, k, v)
        session.commit()


class SoftDelete(object):
    def soft_delete(self, session=None):
        # Mark an object as deleted
        self.update_and_save({'deleted_time': timeutils.utcnow()},
                             session=session)


class Cluster(BASE, SenlinBase, SoftDelete):
    """Represents a cluster created by the Senlin engine."""

    __tablename__ = 'cluster'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column('name', sqlalchemy.String(255))
    profile_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('profile.id'),
                                   nullable=False)
    user = sqlalchemy.Column(sqlalchemy.String(36))
    project = sqlalchemy.Column(sqlalchemy.String(36))
    domain = sqlalchemy.Column(sqlalchemy.String(36))
    parent = sqlalchemy.Column(sqlalchemy.String(36))
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)
    next_index = sqlalchemy.Column(sqlalchemy.Integer)
    timeout = sqlalchemy.Column(sqlalchemy.Integer)
    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.String(255))
    tags = sqlalchemy.Column(types.Json)
    data = sqlalchemy.Column(types.Json)


class Node(BASE, SenlinBase):
    """Represents a Node created by the Senlin engine."""

    __tablename__ = 'node'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    physical_id = sqlalchemy.Column(sqlalchemy.String(36))
    cluster_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('cluster.id'))
    profile_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('profile.id'))
    index = sqlalchemy.Column(sqlalchemy.Integer)
    role = sqlalchemy.Column(sqlalchemy.String(64))

    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)

    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.String(255))
    tags = sqlalchemy.Column(types.Json)
    data = sqlalchemy.Column(types.Json)


class ClusterLock(BASE, SenlinBase):
    """
    Store cluster locks for actions performed by multiple workers.

    Worker threads are able to grab this lock
    """

    __tablename__ = 'cluster_lock'

    cluster_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('cluster.id'),
                                   primary_key=True, nullable=False)
    worker_id = sqlalchemy.Column(sqlalchemy.String(36))


class NodeLock(BASE, SenlinBase):
    """
    Store node locks for actions performed by multiple workers.

    Worker threads are able to grab this lock
    """

    __tablename__ = 'node_lock'

    node_id = sqlalchemy.Column(sqlalchemy.String(36),
                                sqlalchemy.ForeignKey('node.id'),
                                primary_key=True, nullable=False)
    engine_id = sqlalchemy.Column(sqlalchemy.String(36))


class Policy(BASE, SenlinBase):
    '''A policy managed by the Senlin engine.'''

    __tablename__ = 'policy'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    type = sqlalchemy.Column(sqlalchemy.String(255))
    cooldown = sqlalchemy.Column(sqlalchemy.Integer)
    level = sqlalchemy.Column(sqlalchemy.Integer)
    spec = sqlalchemy.Column(types.Json)
    data = sqlalchemy.Column(types.Json)


class ClusterPolicies(BASE, SenlinBase):
    '''Association betwen clusters and policies.'''

    __tablename__ = 'cluster_policy'

    id = sqlalchemy.Column('uuid', sqlalchemy.String(36),
                           primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    cluster_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('cluster.id'),
                                   nullable=False)
    policy_id = sqlalchemy.Column(sqlalchemy.String(36),
                                  sqlalchemy.ForeignKey('policy.id'),
                                  nullable=False)
    cooldown = sqlalchemy.Column(sqlalchemy.Integer)
    level = sqlalchemy.Column(sqlalchemy.Integer)
    enabled = sqlalchemy.Column(sqlalchemy.Boolean)


class Profile(BASE, SenlinBase):
    '''A profile managed by the Senlin engine.'''

    __tablename__ = 'profile'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    type = sqlalchemy.Column(sqlalchemy.String(255))
    spec = sqlalchemy.Column(types.Json)
    permission = sqlalchemy.Column(sqlalchemy.String(32))
    tags = sqlalchemy.Column(types.Json)


class Event(BASE, SenlinBase):
    """Represents an event generated by the Senin engine."""

    __tablename__ = 'event'

    id = sqlalchemy.Column('uuid', sqlalchemy.String(36),
                           primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime)
    obj_id = sqlalchemy.Column(sqlalchemy.String(36))
    obj_name = sqlalchemy.Column(sqlalchemy.String(255))
    obj_type = sqlalchemy.Column(sqlalchemy.String(36))
    user = sqlalchemy.Column(sqlalchemy.String(36))
    action = sqlalchemy.Column(sqlalchemy.String(36))
    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.String(255))
