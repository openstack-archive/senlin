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

import mock
from oslo_config import cfg

from senlin.drivers import base as driver_base
from senlin.engine import environment
from senlin.tests.unit.common import base


class TestSenlinDriver(base.SenlinTestCase):

    def test_init_using_default_cloud_backend(self):
        plugin1 = mock.Mock()
        plugin1.compute = 'Compute1'
        plugin1.orchestration = 'Orchestration1'
        env = environment.global_env()
        env.register_driver('cloud_backend_1', plugin1)

        # Using default cloud backend defined in configure file
        cfg.CONF.set_override('cloud_backend', 'cloud_backend_1',
                              enforce_type=True)
        sd = driver_base.SenlinDriver()
        self.assertEqual('Compute1', sd.compute)
        self.assertEqual('Orchestration1', sd.orchestration)

    def test_init_using_specified_cloud_backend(self):
        plugin2 = mock.Mock()
        plugin2.compute = 'Compute2'
        plugin2.orchestration = 'Orchestration2'
        env = environment.global_env()
        env.register_driver('cloud_backend_2', plugin2)

        # Using specified cloud backend
        sd = driver_base.SenlinDriver('cloud_backend_2')
        self.assertEqual('Compute2', sd.compute)
        self.assertEqual('Orchestration2', sd.orchestration)
