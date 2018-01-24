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


class OctaviaClient(base.DriverBase):
    '''Fake octavia V2 driver for test.'''

    def __init__(self, ctx):
        self.fake_lb = {
            "loadbalancer": "a36c20d0-18e9-42ce-88fd-82a35977ee8c",
            "vip_address": "192.168.1.100",
            "listener": "35cb8516-1173-4035-8dae-0dae3453f37f",
            "pool": "4c0a0a5f-cf8f-44b7-b912-957daa8ce5e5",
            "healthmonitor": "0a9ac99d-0a09-4b18-8499-a0796850279a"
        }

        self.member_id = "9a7aff27-fd41-4ec1-ba4c-3eb92c629313"

    def loadbalancer_create(self, vip_subnet_id, vip_address=None,
                            admin_state_up=True, name=None, description=None):
        return sdk.FakeResourceObject(self.fake_lb)

    def loadbalancer_delete(self, lb_id, ignore_missing=True):
        return

    def loadbalancer_get(self, name_or_id, ignore_missing=True,
                         show_deleted=False):
        return

    def listener_create(self, loadbalancer_id, protocol, protocol_port,
                        connection_limit=None, admin_state_up=True,
                        name=None, description=None):
        return

    def listener_delete(self, listener_id, ignore_missing=True):
        return

    def pool_create(self, lb_algorithm, listener_id, protocol,
                    admin_state_up=True, name=None, description=None):
        return

    def pool_delete(self, pool_id, ignore_missing=True):
        return

    def pool_member_create(self, pool_id, address, protocol_port, subnet_id,
                           weight=None, admin_state_up=True):
        return

    def pool_member_delete(self, pool_id, member_id, ignore_missing=True):
        return

    def healthmonitor_create(self, hm_type, delay, timeout, max_retries,
                             pool_id, admin_state_up=True, http_method=None,
                             url_path=None, expected_codes=None):
        return

    def healthmonitor_delete(self, hm_id, ignore_missing=True):
        return
