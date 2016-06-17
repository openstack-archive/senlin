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

from senlin.drivers import base
from senlin.tests.drivers.openstack import sdk


class NeutronClient(base.DriverBase):
    '''Fake Neutron V2 driver for test.'''

    def __init__(self, ctx):
        self.fake_network = {
            "status": "ACTIVE",
            "subnets": [
                "54d6f61d-db07-451c-9ab3-b9609b6b6f0b"
            ],
            "name": "private-network",
            "router:external": False,
            "admin_state_up": True,
            "tenant_id": "4fd44f30292945e481c7b8a0c8908869",
            "mtu": 0,
            "shared": True,
            "port_security_enabled": True,
            "id": "d32019d3-bc6e-4319-9c1d-6722fc136a22"
        }

    def network_get(self, value, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_network)
