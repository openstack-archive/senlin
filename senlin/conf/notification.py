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

NOTIFICATION_GROUP = cfg.OptGroup(
    name='notification',
)

NOTIFICATION_OPTS = [
    cfg.IntOpt('max_message_size', default=65535,
               help=_('The max size(bytes) of message can be posted to '
                      'notification queue.')),
    cfg.IntOpt('ttl', default=300,
               help=_('The ttl in seconds of a message posted to '
                      'notification queue.')),
]


def register_opts(conf):
    conf.register_group(NOTIFICATION_GROUP)
    conf.register_opts(NOTIFICATION_OPTS, group=NOTIFICATION_GROUP)


def list_opts():
    return {
        NOTIFICATION_GROUP: NOTIFICATION_OPTS,
    }
