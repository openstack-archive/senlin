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
from oslo_context import context as oslo_context
from oslo_log import log as logging
import oslo_messaging

from senlin.common import consts
from senlin.common import messaging

LOG = logging.getLogger(__name__)

OPERATIONS = (
    START_ACTION, CANCEL_ACTION, STOP
) = (
    'start_action', 'cancel_action', 'stop'
)


def notify(method, engine_id=None, **kwargs):
    """Send notification to dispatcher.

    Note that dispatcher is an engine internal communication. We are not using
    versioned object serialization at this level.

    :param method: remote method to call
    :param engine_id: dispatcher to notify; None implies broadcast
    """
    client = messaging.get_rpc_client(consts.ENGINE_TOPIC, cfg.CONF.host)

    if engine_id:
        # Notify specific dispatcher identified by engine_id
        call_context = client.prepare(server=engine_id)
    else:
        # Broadcast to all disptachers
        call_context = client.prepare(fanout=True)

    try:
        # We don't use ctext parameter in action progress
        # actually. But since RPCClient.call needs this param,
        # we use oslo current context here.
        call_context.cast(oslo_context.get_current(), method, **kwargs)
        return True
    except oslo_messaging.MessagingTimeout:
        return False


def start_action(engine_id=None, **kwargs):
    return notify(START_ACTION, engine_id, **kwargs)
