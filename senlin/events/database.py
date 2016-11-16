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

from oslo_utils import reflection
from oslo_utils import timeutils

from senlin.objects import event as eo


class Event(object):
    """Class encapsulating an interesting happening in Senlin."""

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
        """Store the event into database and return its ID."""
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

    @staticmethod
    def _check_entity(e):
        e_type = reflection.get_class_name(e, fully_qualified=False)
        e_type = e_type.upper()

        if e_type == 'CLUSTER':
            return (e.id, e.id, e.name, 'CLUSTER')
        elif e_type == 'NODE':
            return (e.id, e.cluster_id, e.name, 'NODE')
        elif e_type == 'CLUSTERACTION':
            return (e.target, e.target, e.cluster.name, 'CLUSTER')
        elif e_type == 'NODEACTION':
            return (e.target, e.node.cluster_id, e.node.name, 'NODE')
        else:
            return (e.target, '', '', '')

    @classmethod
    def dump(cls, context, level, entity, action, status=None, reason=None,
             **kwargs):
        """Create an event record into database.

        :param context: The request context.
        :param level: The log level which is an integer as defined in logging.
        :param entity: The object in question.
        :param action: The action that triggered this dump.
        :param status: The status of the action or the object.
        :param reason: The reason that led the object into its current status.
        :param kwargs: Additional parameters such as ``timestamp`` or
                       ``extra``.
        """
        status = status or entity.status
        reason = reason or entity.status_reason
        oid, cluster_id, oname, otype = cls._check_entity(entity)

        # use provided timestamp if any
        timestamp = kwargs.get('timestamp') or timeutils.utcnow(True)
        # use provided extra data if any
        extra = kwargs.get("extra") or {}

        values = {
            'level': level,
            'timestamp': timestamp,
            'oid': oid,
            'otype': otype,
            'oname': oname,
            'cluster_id': cluster_id,
            'user': context.user,
            'project': context.project,
            'action': action,
            'status': status,
            'status_reason': reason,
            'meta_data': extra,
        }

        eo.Event.create(context, values)
