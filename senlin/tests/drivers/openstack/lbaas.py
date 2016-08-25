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


class LoadBalancerDriver(base.DriverBase):
    def __init__(self, params):
        self.lb_result = {
            "loadbalancer": "a36c20d0-18e9-42ce-88fd-82a35977ee8c",
            "vip_address": "192.168.1.100",
            "listener": "35cb8516-1173-4035-8dae-0dae3453f37f",
            "pool": "4c0a0a5f-cf8f-44b7-b912-957daa8ce5e5",
            "healthmonitor": "0a9ac99d-0a09-4b18-8499-a0796850279a"
        }

        self.member_id = "9a7aff27-fd41-4ec1-ba4c-3eb92c629313"

    def lb_create(self, vip, pool, hm=None):
        return True, self.lb_result

    def lb_delete(self, **kwargs):
        return True, 'LB deletion succeeded'

    def member_add(self, node, lb_id, pool_id, port, subneat):
        return self.member_id

    def member_remove(self, lb_id, pool_id, member_id):
        return True
