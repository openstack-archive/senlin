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

import datetime

from oslo_log import log as logging

from senlin.common import exception
from senlin.common import i18n
from senlin.db import api as db_api

_LC = i18n._LC
_LE = i18n._LE
_LW = i18n._LW
_LI = i18n._LI
_ = i18n._

LOG = logging.getLogger(__name__)

class_mapping = {
    'senlin.engine.cluster.Cluster': 'CLUSTER',
    'senlin.engine.node.Node': 'NODE',
    'senlin.profiles.profile.Profile': 'PROFILE',
    'senlin.policies.policy.Policy': 'POLICY',
}


class Event(object):
    '''Class capturing a cluster operation or state change.'''

    def __init__(self, context, timestamp, level, **kwargs):
        self.context = context
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.level = level

        self.id = kwargs.get('id', None)
        self.obj_id = kwargs.get('obj_id', None)
        self.obj_type = kwargs.get('obj_type', None)
        self.obj_name = kwargs.get('obj_name', None)
        self.user = kwargs.get('user', None)
        self.action = kwargs.get('action', None)
        self.status = kwargs.get('status', None)
        self.status_reason = kwargs.get('status_reason', None)
        self.deleted_time = kwargs.get('deleted_time', None)

    @classmethod
    def from_db_record(cls, context, record):
        '''Construct an event object from a database record.'''

        kwargs = {
            'id': record.id,
            'obj_id': record.obj_id,
            'obj_type': record.obj_type,
            'obj_name': record.obj_name,
            'user': record.user,
            'action': record.action,
            'status': record.status,
            'status_reason': record.status_reason,
            'deleted_time': record.deleted_time,
        }
        return cls(context, record.timestamp, record.level, **kwargs)

    @classmethod
    def load(cls, context, event_id):
        '''Retrieve an event record from database.'''
        record = db_api.event_get(context, event_id)
        if record is None:
            raise exception.EventNotFound(event=event_id)

        return cls.from_db_record(context, record)

    @classmethod
    def load_all(cls, context, limit=None, sort_keys=None, marker=None,
                 sort_dir=None, filters=None, show_deleted=False):
        '''Retrieve all events from database.'''

        records = db_api.event_get_all(context, limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       show_deleted=show_deleted)

        for record in records:
            yield cls.from_db_record(context, record)

    def store(self, context):
        '''Store the event into database and return its ID.'''
        values = {
            'level': self.level,
            'timestamp': self.timestamp,
            'obj_id': self.obj_id,
            'obj_type': self.obj_type,
            'obj_name': self.obj_name,
            'user': self.user,
            'action': self.action,
            'status': self.status,
            'status_reason': self.status_reason,
            'deleted_time': self.deleted_time,
        }

        event = db_api.event_create(self.context, values)
        self.id = event.id

        return self.id

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(kwargs)

    def to_dict(self):
        evt = {
            'id': self.id,
            'level': self.level,
            'timestamp': self.timestamp,
            'obj_type': self.obj_type,
            'obj_id': self.obj_id,
            'obj_name': self.obj_name,
            'user': self.user,
            'action': self.action,
            'status': self.status,
            'status_reason': self.status_reason,
            'deleted_time': self.deleted_time,
        }
        return evt


def critical(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(logging.CRITICAL, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.critical(_LC(''))


def error(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(logging.ERROR, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.error(_LE(''))


def warning(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(logging.WARNING, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.warning(_LW(''))


def info(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(logging.INFO, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.info(_LI(''))
