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
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

from senlin.common.i18n import _

AUTHENTICATION_GROUP = cfg.OptGroup('authentication')
AUTHENTICATION_OPTS = [
    cfg.StrOpt('auth_url', default='',
               help=_('Complete identity V3 API endpoint.')),
    cfg.StrOpt('service_username', default='senlin',
               help=_('Senlin service user name.')),
    cfg.StrOpt('service_password', default='', secret=True,
               help=_('Password specified for the Senlin service user.')),
    cfg.StrOpt('service_project_name', default='service',
               help=_('Name of the service project.')),
    cfg.StrOpt('service_user_domain', default='Default',
               help=_('Name of the domain for the service user.')),
    cfg.StrOpt('service_project_domain', default='Default',
               help=_('Name of the domain for the service project.')),
    cfg.BoolOpt('verify_ssl', default=True,
                help=_('Verify HTTPS connections.')),
    cfg.StrOpt('interface', default='public',
               help=_('Interface to use for the API endpoints.')),
]


def register_opts(conf):
    conf.register_group(AUTHENTICATION_GROUP)
    conf.register_opts(AUTHENTICATION_OPTS, group=AUTHENTICATION_GROUP)
    ks_loading.register_session_conf_options(cfg.CONF, 'authentication')


def list_opts():
    return {
        AUTHENTICATION_GROUP: AUTHENTICATION_OPTS
    }
