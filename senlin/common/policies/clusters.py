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
        name="clusters:index",
        check_str=base.UNPROTECTED,
        description="List clusters",
        operations=[
            {
                'path': '/v1/clusters',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:create",
        check_str=base.UNPROTECTED,
        description="Create cluster",
        operations=[
            {
                'path': '/v1/clusters',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:delete",
        check_str=base.UNPROTECTED,
        description="Delete cluster",
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:get",
        check_str=base.UNPROTECTED,
        description="Show cluster details",
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:action",
        check_str=base.UNPROTECTED,
        description="Perform specified action on a cluster.",
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/actions',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:update",
        check_str=base.UNPROTECTED,
        description="Update cluster",
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:collect",
        check_str=base.UNPROTECTED,
        description="Collect Attributes Across a Cluster",
        operations=[
            {
                'path': 'v1/clusters/{cluster_id}/attrs/{path}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name="clusters:operation",
        check_str=base.UNPROTECTED,
        description="Perform an Operation on a Cluster",
        operations=[
            {
                'path': '/v1/clusters/{cluster_id}/ops',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules
