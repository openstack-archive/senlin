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
Policy endpoint for Senlin v1 ReST API.
"""

from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.objects import base as obj_base


class PolicyController(wsgi.Controller):
    """WSGI controller for policy resource in Senlin v1 API."""

    # Define request scope
    # (must match what is in policy file and policies in code.)
    REQUEST_SCOPE = 'policies'

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.POLICY_NAME: 'mixed',
            consts.POLICY_TYPE: 'mixed',
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if key not in whitelist:
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)

        params = util.get_allowed_params(req.params, whitelist)
        is_global = params.pop(consts.PARAM_GLOBAL_PROJECT, False)

        unsafe = util.parse_bool_param(consts.PARAM_GLOBAL_PROJECT, is_global)
        params['project_safe'] = not unsafe
        obj = util.parse_request('PolicyListRequest', req, params)
        policies = self.rpc_client.call(req.context, 'policy_list', obj)
        return {'policies': policies}

    @util.policy_enforce
    def create(self, req, body):
        obj = util.parse_request('PolicyCreateRequest', req, body, 'policy')
        result = self.rpc_client.call(req.context, 'policy_create',
                                      obj.policy)

        return {'policy': result}

    @util.policy_enforce
    def get(self, req, policy_id):
        """Gets detailed information for a policy"""
        body = {'identity': policy_id}
        obj = util.parse_request('PolicyGetRequest', req, body)
        policy = self.rpc_client.call(req.context, 'policy_get', obj)

        return {'policy': policy}

    @util.policy_enforce
    def update(self, req, policy_id, body):
        data = body.get('policy', None)
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))
        body_req = obj_base.SenlinObject.normalize_req(
            'PolicyUpdateRequestBody', body['policy'])
        obj = util.parse_request('PolicyUpdateRequest', req,
                                 {'identity': policy_id,
                                  'policy': body_req})
        policy = self.rpc_client.call(req.context, 'policy_update', obj)

        return {'policy': policy}

    @util.policy_enforce
    def delete(self, req, policy_id):
        body = {'identity': policy_id}
        obj = util.parse_request('PolicyDeleteRequest', req, body)
        self.rpc_client.call(req.context, 'policy_delete', obj)
        raise exc.HTTPNoContent()

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def validate(self, req, body):
        """Validate the policy spec user specified."""
        obj = util.parse_request('PolicyValidateRequest', req, body,
                                 'policy')
        result = self.rpc_client.call(req.context, 'policy_validate',
                                      obj.policy)

        return {'policy': result}
