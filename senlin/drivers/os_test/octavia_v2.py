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

FAKE_LB_ID = "607226db-27ef-4d41-ae89-f2a800e9c2db"
FAKE_LISTENER_ID = "023f2e34-7806-443b-bfae-16c324569a3d"
FAKE_HM_ID = "8ed3c5ac-6efa-420c-bedb-99ba14e58db5"
FAKE_MEMBER_ID = "957a1ace-1bd2-449b-8455-820b6e4b63f3"
FAKE_POOL_ID = "4029d267-3983-4224-a3d0-afb3fe16a2cd"
FAKE_PROJECT_ID = "e3cd678b11784734bc366148aa37580e"
FAKE_SUBNET_ID = "bbb35f84-35cc-4b2f-84c2-a6a29bba68aa"


class OctaviaClient(base.DriverBase):
    '''Fake octavia V2 driver for test.'''

    def __init__(self, ctx):
        self.fake_lb = {
            "admin_state_up": True,
            "description": "Best App load balancer 1",
            "id": FAKE_LB_ID,
            "listeners": [{"id": FAKE_LISTENER_ID}],
            "name": "bestapplb1",
            "operating_status": "ONLINE",
            "pools": [],
            "project_id": FAKE_PROJECT_ID,
            "provider": "octavia",
            "provisioning_status": "ACTIVE",
            "vip_address": "203.0.113.10",
            "vip_port_id": "1e20d91d-8df9-4c15-9778-28bc89226c19",
            "vip_subnet_id": "08dce793-daef-411d-a896-d389cd45b1ea"
        }

        self.fake_listener = {
            "admin_state_up": True,
            "connection_limit": 200,
            "created_at": "2017-02-28T00:42:44",
            "description": "A great TLS listener",
            "default_pool_id": FAKE_POOL_ID,
            "default_tls_container_ref": "http://fake_url",
            "description": "A great TLS listener",
            "id": FAKE_LISTENER_ID,
            "insert_headers": {
                "X-Forwarded-For": "true",
                "X-Forwarded-Port": "true"
            },
            "l7policies": [{"id": "5e618272-339d-4a80-8d14-dbc093091bb1"}],
            "loadbalancers": [{"id": FAKE_LB_ID}],
            "name": "great_tls_listener",
            "operating_status": "ONLINE",
            "project_id": FAKE_PROJECT_ID,
            "protocol": "TERMINATED_HTTPS",
            "protocol_port": 443,
            "provisioning_status": "ACTIVE",
            "sni_container_refs": [
                "http://loc1", "http://loca2"
            ],
            "updated_at": "2017-02-28T00:44:30"
        }

        self.fake_pool = {
            "admin_state_up": True,
            "created_at": "2017-05-10T18:14:44",
            "description": "Super Round Robin Pool",
            "healthmonitor_id": FAKE_HM_ID,
            "id": FAKE_POOL_ID,
            "lb_algorithm": "ROUND_ROBIN",
            "listeners": [{"id": FAKE_LISTENER_ID}],
            "loadbalancers": [{"id": FAKE_LB_ID}],
            "members": [],
            "name": "super-pool",
            "operating_status": "ONLINE",
            "project_id": FAKE_PROJECT_ID,
            "protocol": "HTTP",
            "provisioning_status": "ACTIVE",
            "session_persistence": {
                "cookie_name": "ChocolateChip",
                "type": "APP_COOKIE"
            },
            "updated_at": "2017-05-10T23:08:12"
        }

        self.fake_member = {
            "address": "192.0.2.16",
            "admin_state_up": True,
            "created_at": "2017-05-11T17:21:34",
            "id": FAKE_MEMBER_ID,
            "monitor_address": None,
            "monitor_port": 8080,
            "name": "web-server-1",
            "operating_status": "NO_MONITOR",
            "project_id": FAKE_PROJECT_ID,
            "protocol_port": 80,
            "provisioning_status": "ACTIVE",
            "subnet_id": FAKE_SUBNET_ID,
            "updated_at": "2017-05-11T17:21:37",
            "weight": 20,
        }

        self.fake_hm = {
            "admin_state_up": True,
            "created_at": "2017-05-11T23:53:47",
            "delay": 10,
            "expected_codes": 200,
            "http_method": "GET",
            "id": FAKE_HM_ID,
            "max_retries": 1,
            "max_retries_down": 3,
            "name": "super-pool-health-monitor",
            "operating_status": "ONLINE",
            "pools": [{"id": FAKE_POOL_ID}],
            "project_id": FAKE_PROJECT_ID,
            "provisioning_status": "ACTIVE",
            "timeout": 5,
            "type": "HTTP",
            "updated_at": "2017-05-11T23:53:47",
            "url_path": "/"
        }

    def loadbalancer_create(self, vip_subnet_id, vip_address=None,
                            admin_state_up=True, name=None, description=None):
        self.fake_lb["vip_subnet_id"] = vip_subnet_id
        self.fake_lb["admin_state_up"] = admin_state_up
        if vip_address:
            self.fake_lb["vip_address"] = vip_address
        if name:
            self.fake_lb["name"] = name
        if description:
            self.fake_lb["description"] = description
        return sdk.FakeResourceObject(self.fake_lb)

    def loadbalancer_delete(self, lb_id, ignore_missing=True):
        return

    def loadbalancer_get(self, name_or_id, ignore_missing=True,
                         show_deleted=False):
        if name_or_id in (self.fake_lb["id"], self.fake_lb["name"]):
            return sdk.FakeResourceObject(self.fake_lb)
        return None

    def listener_create(self, loadbalancer_id, protocol, protocol_port,
                        connection_limit=None, admin_state_up=True,
                        name=None, description=None):
        self.fake_listener["loadbalancers"] = [{"id": loadbalancer_id}]
        self.fake_listener["protocol"] = protocol
        self.fake_listener["protocol_port"] = protocol_port
        self.fake_listener["admin_state_up"] = admin_state_up
        if connection_limit:
            self.fake_listener["connection_limit"] = connection_limit
        if name:
            self.fake_listener["name"] = name
        if description:
            self.fake_listener["description"] = description

        return sdk.FakeResourceObject(self.fake_listener)

    def listener_delete(self, listener_id, ignore_missing=True):
        return

    def pool_create(self, lb_algorithm, listener_id, protocol,
                    admin_state_up=True, name=None, description=None):
        self.fake_pool["lb_algorithm"] = lb_algorithm
        self.fake_pool["listeners"] = [{"id": listener_id}]
        self.fake_pool["protocol"] = protocol
        self.fake_pool["admin_state_up"] = admin_state_up
        if name:
            self.fake_pool["name"] = name
        if description:
            self.fake_pool["description"] = description
        return sdk.FakeResourceObject(self.fake_pool)

    def pool_delete(self, pool_id, ignore_missing=True):
        return

    def pool_member_create(self, pool_id, address, protocol_port, subnet_id,
                           weight=None, admin_state_up=True):
        # pool_id is ignored
        self.fake_member["address"] = address
        self.fake_member["protocol_port"] = protocol_port
        self.fake_member["subnet_id"] = subnet_id
        self.fake_member["admin_state_up"] = admin_state_up
        if weight:
            self.fake_member["weight"] = weight
        return sdk.FakeResourceObject(self.fake_member)

    def pool_member_delete(self, pool_id, member_id, ignore_missing=True):
        return

    def healthmonitor_create(self, hm_type, delay, timeout, max_retries,
                             pool_id, admin_state_up=True, http_method=None,
                             url_path=None, expected_codes=None):
        self.fake_hm["type"] = hm_type
        self.fake_hm["delay"] = delay
        self.fake_hm["timeout"] = timeout
        self.fake_hm["max_retries"] = max_retries
        self.fake_hm["pools"] = [{"id": pool_id}]
        self.fake_hm["admin_state_up"] = admin_state_up
        if http_method:
            self.fake_hm["http_method"] = http_method
        if url_path:
            self.fake_hm["url_path"] = url_path
        if expected_codes:
            self.fake_hm["expected_codes"] = expected_codes

        return sdk.FakeResourceObject(self.fake_hm)

    def healthmonitor_delete(self, hm_id, ignore_missing=True):
        return
