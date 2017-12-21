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

from oslo_utils import timeutils

from senlin.common import consts
from senlin.events import base
from senlin.objects import event as eo


class DBEvent(base.EventBackend):
    """DB driver for event dumping"""

    @classmethod
    def dump(cls, level, action, **kwargs):
        """Create an event record into database.

        :param level: An integer as defined by python logging module.
        :param action: The action that triggered this dump.
        :param dict kwargs: Additional parameters such as ``phase``,
                            ``timestamp`` or ``extra``.
        """
        ctx = action.context
        entity = action.entity
        status = kwargs.get('phase') or entity.status
        reason = kwargs.get('reason') or entity.status_reason
        otype = cls._check_entity(entity)
        cluster_id = entity.id if otype == 'CLUSTER' else entity.cluster_id
        # use provided timestamp if any
        timestamp = kwargs.get('timestamp') or timeutils.utcnow(True)
        # use provided extra data if any
        extra = kwargs.get("extra") or {}

        # Make a guess over the action name
        action_name = action.action
        if action_name in (consts.NODE_OPERATION, consts.CLUSTER_OPERATION):
            action_name = action.inputs.get('operation', action_name)

        values = {
            'level': level,
            'timestamp': timestamp,
            'oid': entity.id,
            'otype': otype,
            'oname': entity.name,
            'cluster_id': cluster_id,
            'user': ctx.user_id,
            'project': ctx.project_id,
            'action': action_name,
            'status': status,
            'status_reason': reason,
            'meta_data': extra,
        }

        eo.Event.create(ctx, values)
