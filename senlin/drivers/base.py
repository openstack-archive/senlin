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

from oslo_config import cfg
from oslo_log import log as logging

from senlin.engine import environment

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class DriverBase(object):
    '''Base class for all drivers.'''

    def __init__(self, context):
        self.context = context


class SenlinDriver(object):
    '''Generic driver class'''

    def __init__(self, cloud_backend=None):
        if cloud_backend:
            plugin_name = cloud_backend
        else:
            plugin_name = cfg.CONF.cloud_backend

        cloud_backend_plugin = environment.global_env().get_driver(plugin_name)

        # TODO(Yanyan Hu): Use openstack compute driver(nova_v2)
        # as the start point of using senlin generic driver.
        self.compute = cloud_backend_plugin.ComputeClient
        self.network = cloud_backend_plugin.NetworkClient
        self.loadbalancing = cloud_backend_plugin.LoadBalancingClient
        self.orchestration = cloud_backend_plugin.OrchestrationClient
        self.telemetry = cloud_backend_plugin.TelemetryClient
