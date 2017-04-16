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

from senlin.drivers.openstack import ceilometer_v2
from senlin.drivers.openstack import keystone_v3
from senlin.drivers.openstack import zaqar_v2
from senlin.tests.drivers.openstack import heat_v1
from senlin.tests.drivers.openstack import lbaas
from senlin.tests.drivers.openstack import mistral_v2
from senlin.tests.drivers.openstack import neutron_v2
from senlin.tests.drivers.openstack import nova_v2


compute = nova_v2.NovaClient
identity = keystone_v3.KeystoneClient
loadbalancing = lbaas.LoadBalancerDriver
message = zaqar_v2.ZaqarClient
network = neutron_v2.NeutronClient
orchestration = heat_v1.HeatClient
telemetry = ceilometer_v2.CeilometerClient
workflow = mistral_v2.MistralClient
