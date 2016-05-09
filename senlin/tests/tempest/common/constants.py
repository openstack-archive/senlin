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


spec_nova_server = {
    "type": "os.nova.server",
    "version": "1.0",
    "properties": {
        "flavor": 1,
        "name": "new-server-test",
        "image": "cirros-0.3.4-x86_64-uec",
        "networks": [
            {"network": "private-net"}
        ]
    }
}

spec_scaling_policy = {
    "type": "senlin.policy.scaling",
    "version": "1.0",
    "properties": {
        "event": "CLUSTER_SCALE_IN",
        "adjustment": {
            "type": "CHANGE_IN_CAPACITY",
            "number": 1,
            "min_step": 1,
            "best_effort": True
        }
    }
}
