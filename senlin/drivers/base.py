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

import copy

from oslo_config import cfg

from senlin.engine import environment

CONF = cfg.CONF


class DriverBase(object):
    '''Base class for all drivers.'''

    def __init__(self, params):
        self.conn_params = copy.deepcopy(params)


class SenlinDriver(object):
    '''Generic driver class'''

    def __init__(self, backend_name=None):

        if backend_name is None:
            backend_name = cfg.CONF.cloud_backend

        backend = environment.global_env().get_driver(backend_name)

        self.compute = backend.compute
        self.loadbalancing = backend.loadbalancing
        self.network = backend.network
        self.octavia = backend.octavia
        self.orchestration = backend.orchestration
        self.identity = backend.identity
        self.message = backend.message
        self.workflow = backend.workflow
        self.block_storage = backend.block_storage
