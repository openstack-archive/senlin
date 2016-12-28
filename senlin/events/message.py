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

from oslo_config import cfg

from senlin.common import utils
from senlin.events import base
from senlin.objects import notification as nobj


class MessageEvent(base.EventBackend):
    """Message driver for event dumping"""

    @classmethod
    def _notify_cluster_action(cls, ctx, level, cluster, action, **kwargs):
        action_name = cls._get_action_name(action)
        priority = utils.level_from_number(level).lower()
        publisher = nobj.NotificationPublisher(
            host=cfg.CONF.host, binary='senlin-engine')
        publisher.obj_set_defaults()
        phase = kwargs.get('phase')
        event_type = nobj.EventType(
            object='cluster', action=action_name, phase=phase)
        payload = nobj.ClusterActionPayload(cluster, action)
        notification = nobj.ClusterActionNotification(
            context=ctx, priority=priority, publisher=publisher,
            event_type=event_type, payload=payload)
        notification.emit(ctx)

    @classmethod
    def _notify_node_action(cls, ctx, level, node, action, **kwargs):
        action_name = cls._get_action_name(action)
        priority = utils.level_from_number(level).lower()
        publisher = nobj.NotificationPublisher(
            host=cfg.CONF.host, binary='senlin-engine')
        publisher.obj_set_defaults()
        phase = kwargs.get('phase')
        event_type = nobj.EventType(
            object='node', action=action_name, phase=phase)
        payload = nobj.NodeActionPayload(node, action)
        notification = nobj.NodeActionNotification(
            context=ctx, priority=priority, publisher=publisher,
            event_type=event_type, payload=payload)
        notification.emit(ctx)

    @classmethod
    def dump(cls, level, action, **kwargs):
        """Dump the provided event into message queue.

        :param level: An integer as defined by python logging module.
        :param action: An action object for the current operation.
        :param dict kwargs: Other keyword arguments for the operation.
        """
        ctx = action.context
        entity = action.entity
        etype = cls._check_entity(entity)
        if etype == 'CLUSTER':
            cls._notify_cluster_action(ctx, level, entity, action, **kwargs)
        else:
            cls._notify_node_action(ctx, level, entity, action, **kwargs)
