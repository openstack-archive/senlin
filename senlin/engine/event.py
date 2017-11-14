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
from oslo_log import log as logging
from oslo_utils import timeutils
import six
from stevedore import named

from senlin.common import consts

LOG = logging.getLogger(__name__)
FMT = '%(name)s[%(obj_id)s] %(action)s[%(id)s] %(phase)s: %(reason)s'
dispatchers = None


def load_dispatcher():
    """Load dispatchers."""
    global dispatchers

    LOG.debug("Loading dispatchers")
    dispatchers = named.NamedExtensionManager(
        namespace="senlin.dispatchers",
        names=cfg.CONF.event_dispatchers,
        invoke_on_load=True,
        propagate_map_exceptions=True)
    if not list(dispatchers):
        LOG.warning("No dispatchers configured for 'senlin.dispatchers'")
    else:
        LOG.info("Loaded dispatchers: %s", dispatchers.names())


def _event_data(action, phase=None, reason=None):
    action_name = action.action
    if action_name in [consts.NODE_OPERATION, consts.CLUSTER_OPERATION]:
        action_name = action.inputs.get('operation', action_name)
    return dict(name=action.entity.name,
                obj_id=action.entity.id[:8],
                action=action_name,
                id=action.id[:8],
                phase=phase,
                reason=reason)


def _dump(level, action, phase, reason, timestamp):
    global dispatchers

    if timestamp is None:
        timestamp = timeutils.utcnow(True)

    # We check the logging level threshold only when debug is False
    if cfg.CONF.debug is False:
        watermark = cfg.CONF.dispatchers.priority.upper()
        bound = consts.EVENT_LEVELS.get(watermark, logging.INFO)
        if level < bound:
            return

    if cfg.CONF.dispatchers.exclude_derived_actions:
        if action.cause == consts.CAUSE_DERIVED:
            return

    try:
        dispatchers.map_method("dump", level, action,
                               phase=phase, reason=reason, timestamp=timestamp)
    except Exception as ex:
        LOG.exception("Dispatcher failed to handle the event: %s",
                      six.text_type(ex))


def critical(action, phase=None, reason=None, timestamp=None):
    _dump(logging.CRITICAL, action, phase, reason, timestamp)
    LOG.critical(FMT, _event_data(action, phase, reason))


def error(action, phase=None, reason=None, timestamp=None):
    _dump(logging.ERROR, action, phase, reason, timestamp)
    LOG.error(FMT, _event_data(action, phase, reason))


def warning(action, phase=None, reason=None, timestamp=None):
    _dump(logging.WARNING, action, phase, reason, timestamp)
    LOG.warning(FMT, _event_data(action, phase, reason))


def info(action, phase=None, reason=None, timestamp=None):
    _dump(logging.INFO, action, phase, reason, timestamp)
    LOG.info(FMT, _event_data(action, phase, reason))


def debug(action, phase=None, reason=None, timestamp=None):
    _dump(logging.DEBUG, action, phase, reason, timestamp)
    LOG.debug(FMT, _event_data(action, phase, reason))
