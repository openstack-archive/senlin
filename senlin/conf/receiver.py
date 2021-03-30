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

from oslo_config import cfg

from senlin.common.i18n import _

RECEIVER_GROUP = cfg.OptGroup(
    name='receiver',
)

RECEIVER_OPTS = [
    cfg.StrOpt('host', deprecated_group='webhook',
               help=_('The address for notifying and triggering receivers. '
                      'It is useful for case Senlin API service is running '
                      'behind a proxy.')),
    cfg.PortOpt('port', default=8777, deprecated_group='webhook',
                help=_('The port for notifying and triggering receivers. '
                       'It is useful for case Senlin API service is running '
                       'behind a proxy.')),
    cfg.IntOpt('max_message_size', default=65535,
               help=_('The max size(bytes) of message can be posted to '
                      'receiver queue.')),
]


def register_opts(conf):
    conf.register_group(RECEIVER_GROUP)
    conf.register_opts(RECEIVER_OPTS, group=RECEIVER_GROUP)


def list_opts():
    return {
        RECEIVER_GROUP: RECEIVER_OPTS,
    }
