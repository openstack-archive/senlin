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
        name="policies:index",
        check_str=base.UNPROTECTED,
        description="List policies",
        operations=[
            {
                'path': '/v1/policies',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="policies:create",
        check_str=base.UNPROTECTED,
        description="Create policy",
        operations=[
            {
                'path': '/v1/policies',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="policies:get",
        check_str=base.UNPROTECTED,
        description="Show policy details",
        operations=[
            {
                'path': '/v1/policies/{policy_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="policies:update",
        check_str=base.UNPROTECTED,
        description="Update policy",
        operations=[
            {
                'path': '/v1/policies/{policy_id}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="policies:delete",
        check_str=base.UNPROTECTED,
        description="Delete policy",
        operations=[
            {
                'path': '/v1/policies/{policy_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="policies:validate",
        check_str=base.UNPROTECTED,
        description="Validate policy.",
        operations=[
            {
                'path': '/v1/policies/validate',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules
