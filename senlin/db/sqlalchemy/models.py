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

from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
import six
import sqlalchemy
from sqlalchemy.ext import declarative
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
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
    user = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    domain = sqlalchemy.Column(sqlalchemy.String(32))
    parent = sqlalchemy.Column(sqlalchemy.String(36))

    init_time = sqlalchemy.Column(sqlalchemy.DateTime)
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)

    min_size = sqlalchemy.Column(sqlalchemy.Integer)
    max_size = sqlalchemy.Column(sqlalchemy.Integer)
    desired_capacity = sqlalchemy.Column(sqlalchemy.Integer)
    next_index = sqlalchemy.Column(sqlalchemy.Integer)
    timeout = sqlalchemy.Column(sqlalchemy.Integer)

    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.Text)
    meta_data = sqlalchemy.Column(types.Dict)
    data = sqlalchemy.Column(types.Dict)


class Node(BASE, SenlinBase, SoftDelete):
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
    user = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    domain = sqlalchemy.Column(sqlalchemy.String(32))
    index = sqlalchemy.Column(sqlalchemy.Integer)
    role = sqlalchemy.Column(sqlalchemy.String(64))

    init_time = sqlalchemy.Column(sqlalchemy.DateTime)
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)

    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.Text)
    meta_data = sqlalchemy.Column(types.Dict)
    data = sqlalchemy.Column(types.Dict)


class ClusterLock(BASE, SenlinBase):
    """Store cluster locks for actions performed by multiple workers.

    Worker threads are able to grab this lock
    """

    __tablename__ = 'cluster_lock'

    cluster_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('cluster.id'),
                                   primary_key=True, nullable=False)
    action_ids = sqlalchemy.Column(types.List)
    semaphore = sqlalchemy.Column(sqlalchemy.Integer)


class NodeLock(BASE, SenlinBase):
    """Store node locks for actions performed by multiple workers.

    Worker threads are able to grab this lock
    """

    __tablename__ = 'node_lock'

    node_id = sqlalchemy.Column(sqlalchemy.String(36),
                                sqlalchemy.ForeignKey('node.id'),
                                primary_key=True, nullable=False)
    action_id = sqlalchemy.Column(sqlalchemy.String(36))


class Policy(BASE, SenlinBase, SoftDelete):
    '''A policy managed by the Senlin engine.'''

    __tablename__ = 'policy'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    user = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    domain = sqlalchemy.Column(sqlalchemy.String(32))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    type = sqlalchemy.Column(sqlalchemy.String(255))
    cooldown = sqlalchemy.Column(sqlalchemy.Integer)
    level = sqlalchemy.Column(sqlalchemy.Integer)
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)
    spec = sqlalchemy.Column(types.Dict)
    data = sqlalchemy.Column(types.Dict)


class ClusterPolicies(BASE, SenlinBase):
    '''Association between clusters and policies.'''

    __tablename__ = 'cluster_policy'

    id = sqlalchemy.Column('id', sqlalchemy.String(36),
                           primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    cluster_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('cluster.id'),
                                   nullable=False)
    policy_id = sqlalchemy.Column(sqlalchemy.String(36),
                                  sqlalchemy.ForeignKey('policy.id'),
                                  nullable=False)
    cluster = relationship(Cluster, backref=backref('policies'))
    policy = relationship(Policy, backref=backref('bindings'))
    cooldown = sqlalchemy.Column(sqlalchemy.Integer)
    priority = sqlalchemy.Column(sqlalchemy.Integer)
    level = sqlalchemy.Column(sqlalchemy.Integer)
    enabled = sqlalchemy.Column(sqlalchemy.Boolean)
    data = sqlalchemy.Column(types.Dict)
    last_op = sqlalchemy.Column(sqlalchemy.DateTime)


class Profile(BASE, SenlinBase, SoftDelete):
    '''A profile managed by the Senlin engine.'''

    __tablename__ = 'profile'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    type = sqlalchemy.Column(sqlalchemy.String(255))
    context = sqlalchemy.Column(types.Dict)
    spec = sqlalchemy.Column(types.Dict)
    user = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    domain = sqlalchemy.Column(sqlalchemy.String(32))
    permission = sqlalchemy.Column(sqlalchemy.String(32))
    meta_data = sqlalchemy.Column(types.Dict)
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)


class Trigger(BASE, SenlinBase, SoftDelete):
    '''A profile managed by the Senlin engine.'''

    # The table cannot be named as 'trigger' because 'trigger' may be
    # a reserved word in mysql

    __tablename__ = 'triggers'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    physical_id = sqlalchemy.Column(sqlalchemy.String(36))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    type = sqlalchemy.Column(sqlalchemy.String(255))
    desc = sqlalchemy.Column(sqlalchemy.String(255))
    state = sqlalchemy.Column(sqlalchemy.String(32))
    enabled = sqlalchemy.Column(sqlalchemy.Boolean)
    severity = sqlalchemy.Column(sqlalchemy.String(32))
    links = sqlalchemy.Column(types.Dict)
    spec = sqlalchemy.Column(types.Dict)
    user = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String(32), nullable=False)
    domain = sqlalchemy.Column(sqlalchemy.String(32))
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)


class Webhook(BASE, SenlinBase, SoftDelete):
    """Represents a webhook bonded with Senlin resource entity."""

    __tablename__ = 'webhook'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column('name', sqlalchemy.String(255))
    user = sqlalchemy.Column(sqlalchemy.String(32))
    domain = sqlalchemy.Column(sqlalchemy.String(32))
    project = sqlalchemy.Column(sqlalchemy.String(32))

    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)

    obj_id = sqlalchemy.Column(sqlalchemy.String(36))
    obj_type = sqlalchemy.Column(sqlalchemy.String(36))
    action = sqlalchemy.Column(sqlalchemy.String(36))
    credential = sqlalchemy.Column(sqlalchemy.Text)
    params = sqlalchemy.Column(types.Dict)


class Credential(BASE, SenlinBase):
    '''A table for storing user credentials.'''

    __tablename__ = 'credential'

    user = sqlalchemy.Column(sqlalchemy.String(32), primary_key=True,
                             nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String(32), primary_key=True,
                                nullable=False)
    cred = sqlalchemy.Column(types.Dict, nullable=False)
    data = sqlalchemy.Column(types.Dict)


class Action(BASE, SenlinBase, SoftDelete):
    '''An action persisted in the Senlin database.'''

    __tablename__ = 'action'

    id = sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column(sqlalchemy.String(63))
    context = sqlalchemy.Column(types.Dict)
    target = sqlalchemy.Column(sqlalchemy.String(36))
    action = sqlalchemy.Column(sqlalchemy.Text)
    cause = sqlalchemy.Column(sqlalchemy.String(255))
    owner = sqlalchemy.Column(sqlalchemy.String(36))
    interval = sqlalchemy.Column(sqlalchemy.Integer)
    start_time = sqlalchemy.Column(sqlalchemy.Float)
    end_time = sqlalchemy.Column(sqlalchemy.Float)
    timeout = sqlalchemy.Column(sqlalchemy.Integer)
    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.Text)
    control = sqlalchemy.Column(sqlalchemy.String(255))
    inputs = sqlalchemy.Column(types.Dict)
    outputs = sqlalchemy.Column(types.Dict)
    depends_on = sqlalchemy.Column(types.List)
    depended_by = sqlalchemy.Column(types.List)
    created_time = sqlalchemy.Column(sqlalchemy.DateTime)
    updated_time = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)
    data = sqlalchemy.Column(types.Dict)


class Event(BASE, SenlinBase, SoftDelete):
    """Represents an event generated by the Senin engine."""

    __tablename__ = 'event'

    id = sqlalchemy.Column('id', sqlalchemy.String(36),
                           primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted_time = sqlalchemy.Column(sqlalchemy.DateTime)
    obj_id = sqlalchemy.Column(sqlalchemy.String(36))
    obj_name = sqlalchemy.Column(sqlalchemy.String(255))
    obj_type = sqlalchemy.Column(sqlalchemy.String(36))
    cluster_id = sqlalchemy.Column(sqlalchemy.String(36),
                                   sqlalchemy.ForeignKey('cluster.id'),
                                   nullable=True)
    cluster = relationship(Cluster, backref=backref('events'))
    level = sqlalchemy.Column(sqlalchemy.String(64))
    user = sqlalchemy.Column(sqlalchemy.String(32))
    project = sqlalchemy.Column(sqlalchemy.String(32))
    action = sqlalchemy.Column(sqlalchemy.String(36))
    status = sqlalchemy.Column(sqlalchemy.String(255))
    status_reason = sqlalchemy.Column(sqlalchemy.Text)
    meta_data = sqlalchemy.Column(types.Dict)
