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

HEALTH_MANAGER_GROUP = cfg.OptGroup('health_manager')
HEALTH_MANAGER_OPTS = [
    cfg.StrOpt('nova_control_exchange', default='nova',
               help=_("Exchange name for nova notifications.")),
    cfg.StrOpt('nova_notification_topic', default='versioned_notifications',
               help=_("Topic name for nova notifications.")),
    cfg.StrOpt('heat_control_exchange', default='heat',
               help=_("Exchange name for heat notifications.")),
    cfg.StrOpt('heat_notification_topic', default='notifications',
               help=_("Topic name for heat notifications.")),
    cfg.MultiStrOpt("enabled_endpoints", default=['nova', 'heat'],
                    help=_("Notification endpoints to enable.")),
    cfg.IntOpt('workers',
               default=1,
               help=_('Number of senlin-health-manager processes.')),
    cfg.IntOpt('threads',
               default=1000,
               deprecated_name='health_manager_thread_pool_size',
               deprecated_group="DEFAULT",
               help=_('Number of senlin-health-manager threads.')),
]


def register_opts(conf):
    conf.register_group(HEALTH_MANAGER_GROUP)
    conf.register_opts(HEALTH_MANAGER_OPTS, group=HEALTH_MANAGER_GROUP)


def list_opts():
    return {
        HEALTH_MANAGER_GROUP: HEALTH_MANAGER_OPTS
    }
