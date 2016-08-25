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
from six.moves.urllib import parse

from senlin.engine.receivers import base

CONF = cfg.CONF


class Webhook(base.Receiver):
    """Webhook flavor of receivers."""

    def initialize_channel(self):
        host = CONF.webhook.host
        port = CONF.webhook.port
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
