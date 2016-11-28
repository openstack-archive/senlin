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


class DBEvent(object):
    """DB driver for event dumping"""

    @staticmethod
    def _check_entity(e):
        e_type = reflection.get_class_name(e, fully_qualified=False)
        e_type = e_type.upper()

        if e_type == 'CLUSTER':
            return (e.id, e.id, e.name, 'CLUSTER')
        elif e_type == 'NODE':
            return (e.id, e.cluster_id, e.name, 'NODE')
        elif e_type == 'CLUSTERACTION':
            return (e.target, e.target, e.entity.name, 'CLUSTER')
        elif e_type == 'NODEACTION':
            return (e.target, e.entity.cluster_id, e.entity.name, 'NODE')
        else:
            return (e.target, '', '', '')

    @classmethod
    def dump(cls, ctx, level, entity, action, **kwargs):
        """Create an event record into database.

        :param ctx: The request context.
        :param level: An integer as defined by python logging module.
        :param entity: A cluster or a node object.
        :param action: The action that triggered this dump.
        :param dict kwargs: Additional parameters such as ``phase``,
                            ``timestamp`` or ``extra``.
        """
        status = kwargs.get('status') or entity.status
        reason = kwargs.get('reason') or entity.status_reason
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
            'user': ctx.user,
            'project': ctx.project,
            'action': action,
            'status': status,
            'status_reason': reason,
            'meta_data': extra,
        }

        eo.Event.create(ctx, values)
