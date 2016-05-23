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

"""
Routines for configuring Senlin
"""
import socket

from oslo_config import cfg

from senlin.common.i18n import _


# DEFAULT, service
service_opts = [
    cfg.StrOpt('default_region_name',
               help=_('Default region name used to get services endpoints.')),
    cfg.IntOpt('max_response_size',
               default=524288,
               help=_('Maximum raw byte size of data from web response.'))
]

cfg.CONF.register_opts(service_opts)

# DEFAULT, engine
engine_opts = [
    cfg.IntOpt('periodic_interval',
               default=60,
               help=_('Seconds between running periodic tasks.')),
    cfg.IntOpt('periodic_interval_max',
               default=120,
               help='Seconds between periodic tasks to be called'),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=10,
               help='Range of seconds to randomly delay when starting the'
                    ' periodic task scheduler to reduce stampeding.'
                    ' (Disable by setting to 0)'),
    cfg.IntOpt('num_engine_workers',
               default=1,
               help=_('Number of senlin-engine processes to fork and run.')),
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
    cfg.IntOpt('max_events_per_cluster',
               default=3000,
               help=_('Maximum events per cluster. Older events will be '
                      'deleted when this is reached.  Set to 0 for unlimited '
                      'events per cluster.')),
    cfg.IntOpt('default_action_timeout',
               default=3600,
               help=_('Timeout in seconds for actions.')),
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
    cfg.IntOpt('engine_life_check_timeout',
               default=2,
               help=_('RPC timeout for the engine liveness check that is used'
                      ' for cluster locking.')),
    cfg.BoolOpt('name_unique',
                default=False,
                help=_('Flag to indicate whether to enforce unique names for '
                       'Senlin objects belonging to the same project.'))
]
cfg.CONF.register_opts(engine_opts)

# DEFAULT, cloud_backend
rpc_opts = [
    cfg.StrOpt('host',
               default=socket.gethostname(),
               help=_('Name of the engine node. This can be an opaque '
                      'identifier. It is not necessarily a hostname, FQDN, '
                      'or IP address.'))
]
cfg.CONF.register_opts(rpc_opts)

# DEFAULT, cloud_backend
cloud_backend_opts = [
    cfg.StrOpt('cloud_backend',
               default='openstack',
               help=_('Default cloud backend to use.'))]
cfg.CONF.register_opts(cloud_backend_opts)

authentication_group = cfg.OptGroup('authentication')
authentication_opts = [
    cfg.StrOpt('auth_url', default='',
               help=_('Complete public identity V3 API endpoint.')),
    cfg.StrOpt('service_username', default='senlin',
               help=_('Senlin service user name')),
    cfg.StrOpt('service_password', default='',
               help=_('Password specified for the Senlin service user.')),
    cfg.StrOpt('service_project_name', default='service',
               help=_('Name of the service project.')),
    cfg.StrOpt('service_user_domain', default='Default',
               help=_('Name of the domain for the service user.')),
    cfg.StrOpt('service_project_domain', default='Default',
               help=_('Name of the domain for the service project.')),
]
cfg.CONF.register_group(authentication_group)
cfg.CONF.register_opts(authentication_opts, group=authentication_group)

# Health Manager Group
healthmgr_group = cfg.OptGroup('health_manager')
healthmgr_opts = [
    cfg.StrOpt('nova_control_exchange',
               default='nova',
               help="Exchange name for nova notifications"),
]
cfg.CONF.register_group(healthmgr_group)
cfg.CONF.register_opts(healthmgr_opts, group=healthmgr_group)

# Revision group
revision_group = cfg.OptGroup('revision')
revision_opts = [
    cfg.StrOpt('senlin_api_revision', default='1.0',
               help=_('Senlin API revision.')),
    cfg.StrOpt('senlin_engine_revision', default='1.0',
               help=_('Senlin engine revision.'))
]
cfg.CONF.register_group(revision_group)
cfg.CONF.register_opts(revision_opts, group=revision_group)

# Webhook group
webhook_group = cfg.OptGroup('webhook')
webhook_opts = [
    cfg.StrOpt('host',
               default=socket.gethostname(),
               help=_('Address for invoking webhooks. It is useful for cases '
                      'where proxies are used for triggering webhooks. '
                      'Default to the hostname of the API node.')),
    cfg.PortOpt('port', default=8778,
                help=_('The port on which a webhook will be invoked. Useful '
                       'when service is running behind a proxy.'))
]
cfg.CONF.register_group(webhook_group)
cfg.CONF.register_opts(webhook_opts, group=webhook_group)


def list_opts():
    yield None, cloud_backend_opts
    yield None, rpc_opts
    yield None, engine_opts
    yield None, service_opts
    yield authentication_group.name, authentication_opts
    yield revision_group.name, revision_opts
    yield webhook_group.name, webhook_opts
