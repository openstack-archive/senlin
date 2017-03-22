#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
import osprofiler.profiler
import osprofiler.web

from senlin.common import context
from senlin.common import messaging

cfg.CONF.import_opt('enabled', 'senlin.common.config', group='profiler')

LOG = logging.getLogger(__name__)


def setup(binary, host):
    if cfg.CONF.profiler.enabled:
        _notifier = osprofiler.notifier.create(
            "Messaging", oslo_messaging, context.get_admin_context().to_dict(),
            messaging.TRANSPORT, "senlin", binary, host)
        osprofiler.notifier.set(_notifier)
        osprofiler.web.enable(cfg.CONF.profiler.hmac_keys)
        LOG.warning("OSProfiler is enabled.\nIt means that any person who "
                    "knows any of hmac_keys that are specified in "
                    "/etc/senlin/senlin.conf can trace his requests. \n"
                    "In real life only an operator can read this file so "
                    "there is no security issue. Note that even if any "
                    "person can trigger the profiler, only an admin user "
                    "can retrieve trace.\n"
                    "To disable OSProfiler set in senlin.conf:\n"
                    "[profiler]\nenabled=false")
    else:
        osprofiler.web.disable()
