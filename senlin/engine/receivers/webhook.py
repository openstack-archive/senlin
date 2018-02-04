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

import socket

from oslo_config import cfg
from oslo_log import log as logging
from six.moves.urllib import parse

from senlin.common.i18n import _
from senlin.engine.receivers import base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Webhook(base.Receiver):
    """Webhook flavor of receivers."""

    def initialize_channel(self, context):
        host = CONF.receiver.host
        port = CONF.receiver.port
        base = None

        if not host:
            # Try to get base url by querying senlin endpoint if host
            # is not provided in configuration file
            base = self._get_base_url()
            if not base:
                host = socket.gethostname()
                msg = _('Webhook host is not specified in configuration '
                        'file and Senlin service endpoint can not be found,'
                        'using local hostname (%(host)s) for webhook url.'
                        ) % {'host': host}
                LOG.warning(msg)
            elif base.rfind("v1") == -1:
                base = "%s/v1" % base

        if not base:
            base = "http://%(h)s:%(p)s/v1" % {'h': host, 'p': port}
        webhook = "/webhooks/%(id)s/trigger" % {'id': self.id}

        if self.params:
            normalized = sorted(self.params.items(), key=lambda d: d[0])
            qstr = parse.urlencode(normalized)
            url = "".join([base, webhook, '?V=1&', qstr])
        else:
            url = "".join([base, webhook, '?V=1'])

        self.channel = {
            'alarm_url': url
        }
        return self.channel
