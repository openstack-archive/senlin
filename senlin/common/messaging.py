# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import eventlet
from oslo_config import cfg
import oslo_messaging as messaging

from senlin.common import context

# An alias for the default serializer
JsonPayloadSerializer = messaging.JsonPayloadSerializer

TRANSPORT = None
NOTIFIER = None


class RequestContextSerializer(messaging.Serializer):
    def __init__(self, base):
        self._base = base

    def serialize_entity(self, ctxt, entity):
        if not self._base:
            return entity
        return self._base.serialize_entity(ctxt, entity)

    def deserialize_entity(self, ctxt, entity):
        if not self._base:
            return entity
        return self._base.deserialize_entity(ctxt, entity)

    @staticmethod
    def serialize_context(ctxt):
        return ctxt.to_dict()

    @staticmethod
    def deserialize_context(ctxt):
        return context.RequestContext.from_dict(ctxt)


def setup(url=None, optional=False):
    """Initialise the oslo_messaging layer."""
    global TRANSPORT, NOTIFIER

    if url and url.startswith("fake://"):
        # NOTE: oslo_messaging fake driver uses time.sleep
        # for task switch, so we need to monkey_patch it
        eventlet.monkey_patch(time=True)

    if not TRANSPORT:
        messaging.set_transport_defaults('senlin')
        exmods = ['senlin.common.exception']
        try:
            TRANSPORT = messaging.get_transport(
                cfg.CONF, url, allowed_remote_exmods=exmods)
        except messaging.InvalidTransportURL as e:
            TRANSPORT = None
            if not optional or e.url:
                # NOTE: oslo_messaging is configured but unloadable
                # so reraise the exception
                raise

    if not NOTIFIER and TRANSPORT:
        serializer = RequestContextSerializer(JsonPayloadSerializer())
        NOTIFIER = messaging.Notifier(TRANSPORT, serializer=serializer,
                                      topics=['versioned_notifications'])


def cleanup():
    """Cleanup the oslo_messaging layer."""
    global TRANSPORT, NOTIFIER
    if TRANSPORT:
        TRANSPORT.cleanup()
        TRANSPORT = None
    NOTIFIER = None


def get_rpc_server(target, endpoint):
    """Return a configured oslo_messaging rpc server."""
    serializer = RequestContextSerializer(JsonPayloadSerializer())
    return messaging.get_rpc_server(TRANSPORT, target, [endpoint],
                                    executor='eventlet',
                                    serializer=serializer)


def get_rpc_client(**kwargs):
    """Return a configured oslo_messaging RPCClient."""
    target = messaging.Target(**kwargs)
    serializer = RequestContextSerializer(JsonPayloadSerializer())
    return messaging.RPCClient(TRANSPORT, target, serializer=serializer)


def get_notifier(publisher_id):
    """Return a configured oslo_messaging notifier."""
    global NOTIFIER
    return NOTIFIER.prepare(publisher_id=publisher_id)
