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

from senlin.common import i18n
from senlin.db import api as db_api
from senlin.openstack.common import log

_LC = i18n._LC
_LE = i18n._LE
_LW = i18n._LW
_LI = i18n._LI
_ = i18n._

LOG = log.getLogger(__name__)

class_mapping = {
    'senlin.engine.cluster.Cluster': 'CLUSTER',
    'senlin.engine.node.Node': 'NODE',
    'senlin.profiles.profile.Profile': 'PROFILE',
    'senlin.policies.policy.Policy': 'POLICY',
}


class Event(object):
    '''
    Class capturing a cluster operation or state change.
    '''
    def __init__(self, level, context, entity, action, status,
                 timestamp=None, reason='', entity_type='CLUSTER'):
        self.level = level
        self.context = context
        self.entity = entity.uuid
        self.action = action
        self.status = status
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.reason = reason
        self.entity_type = entity_type


def critical(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(log.CRITICAL, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.critical(_LC(''))


def error(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(log.ERROR, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.error(_LE(''))


def warning(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(log.WARNING, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.warning(_LW(''))


def info(context, entity, action, status, timestamp=None, reason=''):
    entity_type = class_mapping[entity.__class__]
    event = Event(log.INFO, context, entity, action, status,
                  entity_type=entity_type)
    db_api.add_event(event)
    LOG.info(_LI(''))
