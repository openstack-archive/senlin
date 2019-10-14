# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from keystoneauth1 import loading as ksa_loading
from oslo_config import cfg

from senlin.common.i18n import _

ZAQAR_GROUP = cfg.OptGroup(
    name='zaqar',
    title=_('Configuration options for zaqar trustee.')
)


def register_opts(conf):
    conf.register_group(ZAQAR_GROUP)
    ksa_loading.register_session_conf_options(conf, ZAQAR_GROUP)
    ksa_loading.register_auth_conf_options(conf, ZAQAR_GROUP)


def list_opts():
    return {
        ZAQAR_GROUP: (ksa_loading.get_auth_common_conf_options() +
                      ksa_loading.get_auth_plugin_conf_options('password'))
    }
