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
from oslo_utils import timeutils

from senlin.common.i18n import _LC, _LE, _LW, _LI
from senlin.events import database as DB

LOG = logging.getLogger(__name__)


def critical(context, entity, action, status=None, status_reason=None,
             timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = DB.Event(timestamp, logging.CRITICAL, entity,
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
    event = DB.Event(timestamp, logging.ERROR, entity,
                     action=action, status=status, status_reason=status_reason,
                     user=context.user, project=context.project)
    event.store(context)
    msg = _LE('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s')
    LOG.error(msg,
              {'name': event.oname,
               'id': event.oid and event.oid[:8],
               'action': action,
               'status': status,
               'reason': status_reason})


def warning(context, entity, action, status=None, status_reason=None,
            timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = DB.Event(timestamp, logging.WARNING, entity,
                     action=action, status=status, status_reason=status_reason,
                     user=context.user, project=context.project)
    event.store(context)
    msg = _LW('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s')
    LOG.warning(msg,
                {'name': event.oname,
                 'id': event.oid and event.oid[:8],
                 'action': action,
                 'status': status,
                 'reason': status_reason})


def info(context, entity, action, status=None, status_reason=None,
         timestamp=None):
    timestamp = timestamp or timeutils.utcnow(True)
    event = DB.Event(timestamp, logging.INFO, entity,
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
    event = DB.Event(timestamp, logging.DEBUG, entity,
                     action=action, status=status, status_reason=status_reason,
                     user=context.user, project=context.project)
    event.store(context)
    LOG.debug('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s',
              {'name': event.oname,
               'id': event.oid and event.oid[:8],
               'action': action,
               'status': status,
               'reason': status_reason})
