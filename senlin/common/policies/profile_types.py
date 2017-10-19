# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from oslo_policy import policy

from senlin.common.policies import base

rules = [
    policy.DocumentedRuleDefault(
        name="profile_types:index",
        check_str=base.UNPROTECTED,
        description="List profile types",
        operations=[
            {
                'path': '/v1/profile-types',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profile_types:get",
        check_str=base.UNPROTECTED,
        description="Show profile type details",
        operations=[
            {
                'path': '/v1/profile-types/{profile_type}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profile_types:ops",
        check_str=base.UNPROTECTED,
        description="List profile type operations",
        operations=[
            {
                'path': '/v1/profile-types/{profile_type}/ops',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
