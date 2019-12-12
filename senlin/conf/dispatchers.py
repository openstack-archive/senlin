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

DISPATCHERS_GROUP = cfg.OptGroup('dispatchers')
DISPATCHERS_OPTS = [
    cfg.StrOpt('priority', default='info',
               choices=("critical", "error", "warning", "info", "debug"),
               help=_("Lowest event priorities to be dispatched.")),
    cfg.BoolOpt("exclude_derived_actions", default=True,
                help=_("Exclude derived actions from events dumping.")),
]


def register_opts(conf):
    conf.register_group(DISPATCHERS_GROUP)
    conf.register_opts(DISPATCHERS_OPTS, group=DISPATCHERS_GROUP)


def list_opts():
    return {
        DISPATCHERS_GROUP: DISPATCHERS_OPTS
    }
