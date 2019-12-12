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

REVISION_GROUP = cfg.OptGroup('revision')
REVISION_OPTS = [
    cfg.StrOpt('senlin_api_revision', default='1.0',
               help=_('Senlin API revision.')),
    cfg.StrOpt('senlin_engine_revision', default='1.0',
               help=_('Senlin engine revision.'))
]


def register_opts(conf):
    conf.register_group(REVISION_GROUP)
    conf.register_opts(REVISION_OPTS, group=REVISION_GROUP)


def list_opts():
    return {
        REVISION_GROUP: REVISION_OPTS
    }
