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
        name="profiles:index",
        check_str=base.UNPROTECTED,
        description="List profiles",
        operations=[
            {
                'path': '/v1/profiles',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profiles:create",
        check_str=base.UNPROTECTED,
        description="Create profile",
        operations=[
            {
                'path': '/v1/profiles',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profiles:get",
        check_str=base.UNPROTECTED,
        description="Show profile details",
        operations=[
            {
                'path': '/v1/profiles/{profile_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profiles:delete",
        check_str=base.UNPROTECTED,
        description="Delete profile",
        operations=[
            {
                'path': '/v1/profiles/{profile_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profiles:update",
        check_str=base.UNPROTECTED,
        description="Update profile",
        operations=[
            {
                'path': '/v1/profiles/{profile_id}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="profiles:validate",
        check_str=base.UNPROTECTED,
        description="Validate profile",
        operations=[
            {
                'path': '/v1/profiles/validate',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules
