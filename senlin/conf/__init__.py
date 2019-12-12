#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg

from senlin.conf import api
from senlin.conf import authentication
from senlin.conf import base
from senlin.conf import conductor
from senlin.conf import dispatchers
from senlin.conf import engine
from senlin.conf import health_manager
from senlin.conf import notification
from senlin.conf import receiver
from senlin.conf import revision
from senlin.conf import zaqar

CONF = cfg.CONF

api.register_opts(CONF)
authentication.register_opts(CONF)
base.register_opts(CONF)
conductor.register_opts(CONF)
dispatchers.register_opts(CONF)
engine.register_opts(CONF)
health_manager.register_opts(CONF)
notification.register_opts(CONF)
receiver.register_opts(CONF)
revision.register_opts(CONF)
zaqar.register_opts(CONF)
