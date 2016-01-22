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

from oslo_db.sqlalchemy import models
from oslo_utils import uuidutils
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy import String, Text
from sqlalchemy.ext import declarative
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship

from senlin.db.sqlalchemy import types

BASE = declarative.declarative_base()
UUID4 = uuidutils.generate_uuid


def get_session():
    from senlin.db.sqlalchemy import api as db_api
    return db_api.get_session()


class TimestampMixin(object):
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class SenlinBase(models.ModelBase):
    """Base class for Senlin Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Profile(BASE, TimestampMixin, models.ModelBase):
    """A profile managed by the Senlin engine."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'profile'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    name = Column(String(255))
    type = Column(String(255))
    context = Column(types.Dict)
    spec = Column(types.Dict)
    user = Column(String(32), nullable=False)
    project = Column(String(32), nullable=False)
    domain = Column(String(32))
    permission = Column(String(32))
    meta_data = Column(types.Dict)


class Policy(BASE, TimestampMixin, models.ModelBase):
    """A policy managed by the Senlin engine."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'policy'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    user = Column(String(32), nullable=False)
    project = Column(String(32), nullable=False)
    domain = Column(String(32))
    name = Column(String(255))
    type = Column(String(255))
    cooldown = Column(Integer)
    level = Column(Integer)
    spec = Column(types.Dict)
    data = Column(types.Dict)


class Cluster(BASE, TimestampMixin, models.ModelBase):
    """Represents a cluster created by the Senlin engine."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'cluster'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    name = Column('name', String(255))
    profile_id = Column(String(36), ForeignKey('profile.id'), nullable=False)
    user = Column(String(32), nullable=False)
    project = Column(String(32), nullable=False)
    domain = Column(String(32))
    parent = Column(String(36))

    init_at = Column(DateTime)

    min_size = Column(Integer)
    max_size = Column(Integer)
    desired_capacity = Column(Integer)
    next_index = Column(Integer)
    timeout = Column(Integer)

    status = Column(String(255))
    status_reason = Column(Text)
    meta_data = Column(types.Dict)
    data = Column(types.Dict)


class Node(BASE, TimestampMixin, models.ModelBase):
    """Represents a Node created by the Senlin engine."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'node'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    name = Column(String(255))
    physical_id = Column(String(36))
    cluster_id = Column(String(36))
    profile_id = Column(String(36), ForeignKey('profile.id'))
    user = Column(String(32), nullable=False)
    project = Column(String(32), nullable=False)
    domain = Column(String(32))
    index = Column(Integer)
    role = Column(String(64))

    init_at = Column(DateTime)

    status = Column(String(255))
    status_reason = Column(Text)
    meta_data = Column(types.Dict)
    data = Column(types.Dict)


class ClusterLock(BASE, SenlinBase):
    """Store cluster locks for actions performed by multiple workers.

    Worker threads are able to grab this lock
    """

    __tablename__ = 'cluster_lock'

    cluster_id = Column(String(36), primary_key=True, nullable=False)
    action_ids = Column(types.List)
    semaphore = Column(Integer)


class NodeLock(BASE, SenlinBase):
    """Store node locks for actions performed by multiple workers.

    Worker threads are able to grab this lock
    """

    __tablename__ = 'node_lock'

    node_id = Column(String(36), primary_key=True, nullable=False)
    action_id = Column(String(36))


class ClusterPolicies(BASE, SenlinBase):
    '''Association between clusters and policies.'''

    __tablename__ = 'cluster_policy'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    cluster_id = Column(String(36), ForeignKey('cluster.id'), nullable=False)
    policy_id = Column(String(36), ForeignKey('policy.id'), nullable=False)
    cluster = relationship(Cluster, backref=backref('policies'))
    policy = relationship(Policy, backref=backref('bindings'))
    enabled = Column(Boolean)
    priority = Column(Integer)
    data = Column(types.Dict)
    last_op = Column(DateTime)


class Receiver(BASE, TimestampMixin, models.ModelBase):
    """Represents a receiver associated with a Senlin cluster."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'receiver'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    name = Column('name', String(255))
    type = Column(String(255))
    user = Column(String(32))
    project = Column(String(32))
    domain = Column(String(32))

    cluster_id = Column(String(36), ForeignKey('cluster.id'))
    actor = Column(types.Dict)
    action = Column(Text)
    params = Column(types.Dict)
    channel = Column(types.Dict)


class Credential(BASE, SenlinBase):
    '''A table for storing user credentials.'''

    __tablename__ = 'credential'

    user = Column(String(32), primary_key=True, nullable=False)
    project = Column(String(32), primary_key=True, nullable=False)
    cred = Column(types.Dict, nullable=False)
    data = Column(types.Dict)


class ActionDependency(BASE, SenlinBase):
    """A table for recording action dependencies."""

    __tablename__ = 'dependency'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    depended = Column('depended', String(36), ForeignKey('action.id'),
                      nullable=False)
    dependent = Column('dependent', String(36), ForeignKey('action.id'),
                       nullable=False)


class Action(BASE, TimestampMixin, models.ModelBase):
    """An action persisted in the Senlin database."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'action'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    name = Column(String(63))
    context = Column(types.Dict)
    target = Column(String(36))
    action = Column(Text)
    cause = Column(String(255))
    owner = Column(String(36))
    interval = Column(Integer)
    # FIXME: Don't specify fixed precision.
    start_time = Column(Float(precision='24,8'))
    end_time = Column(Float(precision='24,8'))
    timeout = Column(Integer)
    status = Column(String(255))
    status_reason = Column(Text)
    control = Column(String(255))
    inputs = Column(types.Dict)
    outputs = Column(types.Dict)
    data = Column(types.Dict)


class Event(BASE, SenlinBase):
    """Represents an event generated by the Senin engine."""

    __tablename__ = 'event'

    id = Column('id', String(36), primary_key=True, default=lambda: UUID4())
    timestamp = Column(DateTime)
    obj_id = Column(String(36))
    obj_name = Column(String(255))
    obj_type = Column(String(36))
    cluster_id = Column(String(36), ForeignKey('cluster.id'), nullable=True)
    cluster = relationship(Cluster, backref=backref('events'))
    level = Column(String(64))
    user = Column(String(32))
    project = Column(String(32))
    action = Column(String(36))
    status = Column(String(255))
    status_reason = Column(Text)
    meta_data = Column(types.Dict)


class Service(BASE, TimestampMixin, models.ModelBase):

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __tablename__ = 'service'

    id = Column('id', String(36), primary_key=True, nullable=False)
    host = Column(String(255), nullable=False)
    binary = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False)
    disabled = Column(Boolean, default=False)
    disabled_reason = Column(String(255))
