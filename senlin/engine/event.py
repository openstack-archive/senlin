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

from oslo_log import log as logging
from oslo_utils import reflection
from oslo_utils import timeutils

from senlin.common.i18n import _, _LC, _LE, _LW, _LI
from senlin.objects import event as eo

LOG = logging.getLogger(__name__)


class Event(object):
    '''Class capturing an interesting happening in Senlin.'''

    def __init__(self, timestamp, level, entity=None, **kwargs):
        self.timestamp = timestamp
        self.level = level

        self.id = kwargs.get('id', None)
        self.user = kwargs.get('user', None)
        self.project = kwargs.get('project', None)

        self.action = kwargs.get('action', None)
        self.status = kwargs.get('status', None)
        self.status_reason = kwargs.get('status_reason', None)

        # we deal with deserialization first
        self.oid = kwargs.get('oid', None)
        self.otype = kwargs.get('otype', None)
        self.oname = kwargs.get('oname', None)
        self.cluster_id = kwargs.get('cluster_id', None)
        self.metadata = kwargs.get('metadata', {})

        # entity not None implies an initial creation of event object,
        # not a deserialization, so we try make an inference here
        if entity is not None:
            self._infer_entity_data(entity)

    def _infer_entity_data(self, entity):
        if self.status is None:
            self.status = entity.status
        if self.status_reason is None:
            self.status_reason = entity.status_reason

        e_type = reflection.get_class_name(entity, fully_qualified=False)
        e_type = e_type.upper()

        if e_type == 'CLUSTER':
            self.oid = entity.id
            self.cluster_id = entity.id
            self.oname = entity.name
            self.otype = 'CLUSTER'
        elif e_type == 'NODE':
            self.oid = entity.id
            self.cluster_id = entity.cluster_id
            self.oname = entity.name
            self.otype = 'NODE'
        elif e_type == 'CLUSTERACTION':
            self.oid = entity.target
            self.cluster_id = entity.target
            self.oname = entity.cluster.name
            self.otype = 'CLUSTER'
        elif e_type == 'NODEACTION':
            self.oid = entity.target
            self.cluster_id = entity.node.cluster_id
            self.oname = entity.node.name
            self.otype = 'NODE'
        else:
            self.oid = entity.target
            self.cluster_id = ''
            self.oname = ''
            self.otype = ''

    def store(self, context):
        '''Store the event into database and return its ID.'''
        values = {
            'level': self.level,
            'timestamp': self.timestamp,
            'oid': self.oid,
            'otype': self.otype,
            'oname': self.oname,
            'cluster_id': self.cluster_id,
            'user': self.user,
            'project': self.project,
            'action': self.action,
            'status': self.status,
            'status_reason': self.status_reason,
            'meta_data': self.metadata,
        }

        event = eo.Event.create(context, values)
        self.id = event.id

        return self.id


def critical(context, entity, action, status=None, status_reason=None,
             timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = Event(timestamp, logging.CRITICAL, entity,
                  action=action, status=status, status_reason=status_reason,
                  user=context.user, project=context.project)
    event.store(context)
    LOG.critical(_LC('%(name)s [%(id)s] - %(status)s: %(reason)s'),
                 {'name': event.oname,
                  'id': event.oid and event.oid[:8],
                  'status': status,
                  'reason': status_reason})


def error(context, entity, action, status=None, status_reason=None,
          timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = Event(timestamp, logging.ERROR, entity,
                  action=action, status=status, status_reason=status_reason,
                  user=context.user, project=context.project)
    event.store(context)
    LOG.error(_LE('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
              {'name': event.oname,
               'id': event.oid and event.oid[:8],
               'action': action,
               'status': status,
               'reason': status_reason})


def warning(context, entity, action, status=None, status_reason=None,
            timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = Event(timestamp, logging.WARNING, entity,
                  action=action, status=status, status_reason=status_reason,
                  user=context.user, project=context.project)
    event.store(context)
    LOG.warning(_LW('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
                {'name': event.oname,
                 'id': event.oid and event.oid[:8],
                 'action': action,
                 'status': status,
                 'reason': status_reason})


def info(context, entity, action, status=None, status_reason=None,
         timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = Event(timestamp, logging.INFO, entity,
                  action=action, status=status, status_reason=status_reason,
                  user=context.user, project=context.project)
    event.store(context)
    LOG.info(_LI('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
             {'name': event.oname,
              'id': event.oid and event.oid[:8],
              'action': action,
              'status': status,
              'reason': status_reason})


def debug(context, entity, action, status=None, status_reason=None,
          timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = Event(timestamp, logging.DEBUG, entity,
                  action=action, status=status, status_reason=status_reason,
                  user=context.user, project=context.project)
    event.store(context)
    LOG.debug(_('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
              {'name': event.oname,
               'id': event.oid and event.oid[:8],
               'action': action,
               'status': status,
               'reason': status_reason})
