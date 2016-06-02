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

"""Senlin RPC Notifier."""

import oslo_messaging as messaging
from oslo_serialization import jsonutils

from senlin.common import context as senlin_context
from senlin.common import exception as senlin_exc

TRANSPORT = None
NOTIFIER = None


class JsonPayloadSerializer(messaging.NoOpSerializer):

    @staticmethod
    def serialize_entity(context, entity):
        return jsonutils.to_primitive(entity, convert_instances=True)


class RequestContextSerializer(messaging.Serializer):

    def __init__(self, base):
        self._base = base

    def serialize_entity(self, context, entity):
        if not self._base:
            return entity
        return self._base.serialize_entity(context, entity)

    def deserialize_entity(self, context, entity):
        if not self._base:
            return entity
        return self._base.deserialize_entity(context, entity)

    def serialize_context(self, context):
        return context.to_dict()

    def deserialize_context(self, context):
        return senlin_context.RequestContext.from_dict(context)


def init(conf):
    global TRANSPORT, NOTIFIER

    exmods = [senlin_exc.__name__]
    TRANSPORT = messaging.get_notification_transport(
        conf, allowed_remote_exmods=exmods)
    serializer = RequestContextSerializer(JsonPayloadSerializer())
    NOTIFIER = messaging.Notifier(TRANSPORT, serializer=serializer,
                                  topics=['versioned_notifications'])


def cleanup():
    global TRANSPORT, NOTIFIER
    assert TRANSPORT is not None
    assert NOTIFIER is not None

    TRANSPORT.cleanup()
    TRANSPORT = None
    NOTIFIER = None


def get_notifier(publisher_id):
    assert NOTIFIER is not None

    return NOTIFIER.prepare(publisher_id=publisher_id)
