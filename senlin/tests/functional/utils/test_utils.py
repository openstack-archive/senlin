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

import time


spec_nova_server = {
    "type": "os.nova.server",
    "version": "1.0",
    "properties": {
        # TODO(Yanyan Hu): Use flavor name rather than ID in
        # nova server spec file after sdk support is done.
        "flavor": 1,
        "name": "new-server-test",
        "image": "cirros-0.3.2-x86_64-uec",
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

spec_lb_policy = {
    "type": "senlin.policy.loadbalance",
    "version": "1.0",
    "properties": {
        "pool": {
            "protocol": "HTTP",
            "protocol_port": 80,
            "subnet": "private-subnet",
            "lb_method": "ROUND_ROBIN",
            "session_persistence": {
                "type": "SOURCE_IP",
                "cookie_name": "test-cookie"
            }
        },
        "vip": {
            "subnet": "private-subnet",
            "connection_limit": 100,
            "protocol": "HTTP",
            "protocol_port": 80
        }
    }
}


def wait_for_status(func, client, obj_id, expected_status, timeout=60,
                    ignore_missing=False):
    # TODO(Yanyan Hu): Put timeout option into test configure file
    while timeout > 0:
        res = func(client, obj_id, ignore_missing)
        if not ignore_missing:
            if res['status'] == expected_status:
                return res
        else:
            if res.status == 404:
                return res
        time.sleep(5)
        timeout -= 5

    raise Exception('Waiting for status timeout.')
