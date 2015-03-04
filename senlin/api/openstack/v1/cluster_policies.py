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

from webob import exc

from senlin.api.openstack.v1 import util
from senlin.common import serializers
from senlin.common import wsgi
from senlin.rpc import client as rpc_client


class ClusterPolicyController(object):
    '''WSGI controller for Cluster-Policy binding resource in Senlin v1 API.'''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'cluster_policies'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req, cluster_id):
        filter_whitelist = {
            'priority': 'single',
            'level': 'single',
            'cooldown': 'single',
            'enabled': 'single',
        }
        param_whitelist = {
            'sort_dir': 'single',
            'sort_keys': 'multi',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

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


def create_resource(options):
    '''ClusterPolicies resource factory method.'''

    return wsgi.Resource(ClusterPolicyController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
