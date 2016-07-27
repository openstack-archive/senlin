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


spec_heat_stack = {
    "type": "os.heat.stack",
    "version": "1.0",
    "properties": {
        "template": {
            "heat_template_version": "2014-10-16",
            "parameters": {
                "str_length": {
                    "type": "number",
                    "default": 64
                }
            },
            "resources": {
                "random": {
                    "type": "OS::Heat::RandomString",
                    "properties": {
                        "length": {"get_param": "str_length"}
                    }
                }
            },
            "outputs": {
                "result": {
                    "value": {"get_attr": ["random", "value"]}
                }
            }
        }
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
        },
        "health_monitor": {
            "type": "HTTP",
            "delay": "1",
            "timeout": 1,
            "max_retries": 5,
            "admin_state_up": True,
            "http_method": "GET",
            "url_path": "/index.html",
            "expected_codes": "200,201,202"
        },
        "lb_status_timeout": 300
    }
}
