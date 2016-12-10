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

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.objects import base as obj_base
from senlin.objects.requests import cluster_policies as vocp


class ClusterPolicyController(wsgi.Controller):
    """WSGI controller for Cluster-Policy binding in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'cluster_policies'

    @util.policy_enforce
    def index(self, req, cluster_id):
        param_whitelist = {
            consts.CP_ENABLED: 'single',
            consts.CP_POLICY_NAME: 'single',
            consts.CP_POLICY_TYPE: 'single',
            consts.PARAM_SORT: 'single',
        }
        for key in req.params.keys():
            if (key not in param_whitelist.keys()):
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)

        params = util.get_allowed_params(req.params, param_whitelist)
        key = consts.CP_ENABLED
        if key in params:
            params[key] = util.parse_bool_param(key, params[key])
        params['identity'] = cluster_id
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ClusterPolicyListRequest', params, None)
            obj = vocp.ClusterPolicyListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        policies = self.rpc_client.call2(req.context, 'cluster_policy_list2',
                                         obj)

        return {'cluster_policies': policies}

    @util.policy_enforce
    def get(self, req, cluster_id, policy_id):

        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ClusterPolicyGetRequest', {'identity': cluster_id,
                                            'policy_id': policy_id})
            obj = vocp.ClusterPolicyGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        cluster_policy = self.rpc_client.call2(req.context,
                                               'cluster_policy_get2', obj)
        return {'cluster_policy': cluster_policy}
