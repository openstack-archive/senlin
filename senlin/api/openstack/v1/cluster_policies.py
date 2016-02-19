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

"""
ClusterPolicies endpoint for Senlin v1 ReST API.
"""

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common import utils


class ClusterPolicyController(wsgi.Controller):
    """WSGI controller for Cluster-Policy binding in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'cluster_policies'

    @util.policy_enforce
    def index(self, req, cluster_id):
        filter_whitelist = {
            consts.CP_ENABLED: 'single',
        }
        param_whitelist = {
            consts.PARAM_SORT: 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)
        key = consts.CP_ENABLED
        if key in filters:
            filters[key] = utils.parse_bool_param(key, filters[key])

        if not filters:
            filters = None
        policies = self.rpc_client.cluster_policy_list(req.context,
                                                       cluster_id=cluster_id,
                                                       filters=filters,
                                                       **params)

        return {'cluster_policies': policies}

    @util.policy_enforce
    def get(self, req, cluster_id, policy_id):
        cluster_policy = self.rpc_client.cluster_policy_get(
            req.context, cluster_id=cluster_id, policy_id=policy_id)
        return {'cluster_policy': cluster_policy}
