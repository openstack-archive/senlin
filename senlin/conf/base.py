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
import socket

from oslo_config import cfg

from senlin.common.i18n import _

SENLIN_OPTS = [
    cfg.HostAddressOpt('host',
                       default=socket.gethostname(),
                       help=_('Name of the engine node. This can be an opaque '
                              'identifier. It is not necessarily a hostname, '
                              'FQDN or IP address.')),
    cfg.StrOpt('default_region_name',
               help=_('Default region name used to get services endpoints.')),
    cfg.IntOpt('max_response_size',
               default=524288,
               help=_('Maximum raw byte size of data from web response.')),
    cfg.ListOpt('notification_topics',
                default=['versioned_notifications'],
                help=_('Default notification topic.')),
]

ENGINE_OPTS = [
    cfg.IntOpt('periodic_interval',
               default=60,
               help=_('Seconds between running periodic tasks.')),
    cfg.IntOpt('periodic_interval_max',
               default=120,
               help=_('Maximum seconds between periodic tasks to be called.')),
    cfg.IntOpt('check_interval_max',
               default=3600,
               help=_('Maximum seconds between cluster check to be called.')),
    cfg.IntOpt('health_check_interval_min',
               default=60,
               help=_('Minimum seconds between health check to be called.')),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=10,
               help=_('Range of seconds to randomly delay when starting the '
                      'periodic task scheduler to reduce stampeding. '
                      '(Disable by setting to 0)')),
    cfg.StrOpt('environment_dir',
               default='/etc/senlin/environments',
               help=_('The directory to search for environment files.')),
    cfg.IntOpt('max_nodes_per_cluster',
               default=1000,
               help=_('Maximum nodes allowed per top-level cluster.')),
    cfg.IntOpt('max_clusters_per_project',
               default=100,
               help=_('Maximum number of clusters any one project may have'
                      ' active at one time.')),
    cfg.IntOpt('default_action_timeout',
               default=3600,
               help=_('Timeout in seconds for actions.')),
    cfg.IntOpt('default_nova_timeout',
               default=600,
               help=_('Timeout in seconds for nova API calls.')),
    cfg.IntOpt('max_actions_per_batch',
               default=0,
               help=_('Maximum number of node actions that each engine worker '
                      'can schedule consecutively per batch. 0 means no '
                      'limit.')),
    cfg.IntOpt('batch_interval',
               default=3,
               help=_('Seconds to pause between scheduling two consecutive '
                      'batches of node actions.')),
    cfg.IntOpt('lock_retry_times',
               default=3,
               help=_('Number of times trying to grab a lock.')),
    cfg.IntOpt('lock_retry_interval',
               default=10,
               help=_('Number of seconds between lock retries.')),
    cfg.IntOpt('database_retry_limit',
               default=10,
               help=_('Number of times retrying a failed operation on the '
                      'database.')),
    cfg.IntOpt('database_retry_interval',
               default=0.3,
               help=_('Initial number of seconds between database retries.')),
    cfg.IntOpt('database_max_retry_interval',
               default=2,
               help=_('Maximum number of seconds between database retries.')),
    cfg.IntOpt('engine_life_check_timeout',
               default=2,
               help=_('RPC timeout for the engine liveness check that is used'
                      ' for cluster locking.')),
    cfg.BoolOpt('name_unique',
                default=False,
                help=_('Flag to indicate whether to enforce unique names for '
                       'Senlin objects belonging to the same project.')),
    cfg.IntOpt('service_down_time',
               default=60,
               help=_('Maximum time since last check-in for a service to be '
                      'considered up.')),
    cfg.ListOpt('trust_roles',
                default=[],
                help=_('The roles which are delegated to the trustee by the '
                       'trustor when a cluster is created.')),
]

CLOUD_BACKEND_OPTS = [
    cfg.StrOpt('cloud_backend', default='openstack',
               choices=("openstack", "openstack_test"),
               help=_('Default cloud backend to use.')),
]

EVENT_OPTS = [
    cfg.MultiStrOpt("event_dispatchers", default=['database'],
                    help=_("Event dispatchers to enable.")),
]


def register_opts(conf):
    conf.register_opts(SENLIN_OPTS)
    conf.register_opts(ENGINE_OPTS)
    conf.register_opts(CLOUD_BACKEND_OPTS)
    conf.register_opts(EVENT_OPTS)


def list_opts():
    return {
        'DEFAULT': SENLIN_OPTS + ENGINE_OPTS + CLOUD_BACKEND_OPTS + EVENT_OPTS
    }
