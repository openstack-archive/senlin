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
from senlin.drivers import sdk


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
        self.fake_port = {
            "ip_address": "10.0.1.10",
            "fixed_ips": [
                "172.17.1.129"
            ],
            "network_id": "d32019d3-bc6e-4319-9c1d-6722fc136a22",
            "status": "ACTIVE",
            "subnet_id": "54d6f61d-db07-451c-9ab3-b9609b6b6f0b",
            "id": "60f65938-3ebb-451d-a3a3-a0918d345469",
            "security_group_ids": [
                "45aa2abc-47f0-4008-8d67-606b41cabb7a"
            ]
        }
        self.fake_subnet = {
            "network_id": "d32019d3-bc6e-4319-9c1d-6722fc136a22",
            "subnet_pool_id": "54d6f61d-db07-451c-9ab3-b9609b6b6f0b",
            "id": "60f65938-3ebb-451d-a3a3-a0918d345469"
        }

    def network_get(self, value, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_network)

    def port_create(self, **attr):
        return sdk.FakeResourceObject(self.fake_port)

    def port_delete(self, port, ignore_missing=True):
        return None

    def subnet_get(self, name_or_id, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_subnet)
