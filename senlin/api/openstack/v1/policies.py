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
from senlin.common import utils


class PolicyController(wsgi.Controller):
    """WSGI controller for policy resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'policies'

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            consts.POLICY_NAME: 'mixed',
            consts.POLICY_TYPE: 'mixed',
        }
        param_whitelist = {
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if (key not in param_whitelist.keys() and key not in
                    filter_whitelist.keys()):
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)

        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_GLOBAL_PROJECT
        if key in params:
            project_safe = not utils.parse_bool_param(key, params[key])
            del params[key]
            params['project_safe'] = project_safe

        if not filters:
            filters = None

        policies = self.rpc_client.policy_list(req.context, filters=filters,
                                               **params)

        return {'policies': policies}

    @util.policy_enforce
    def create(self, req, body):
        data = body.get('policy', None)
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))
        name = data.get(consts.POLICY_NAME, None)
        if not name:
            raise exc.HTTPBadRequest(_("No policy name specified"))
        spec = data.get(consts.POLICY_SPEC, None)
        if not spec:
            raise exc.HTTPBadRequest(_("No policy spec provided"))

        result = self.rpc_client.policy_create(req.context, name, spec)

        return {'policy': result}

    @util.policy_enforce
    def get(self, req, policy_id):
        policy = self.rpc_client.policy_get(req.context, policy_id)
        return {'policy': policy}

    @util.policy_enforce
    def update(self, req, policy_id, body):
        data = body.get('policy', None)
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))

        spec = data.get(consts.POLICY_SPEC)
        if spec is not None:
            msg = _("Updating the spec of a policy is not supported because "
                    "it may cause state conflicts in engine.")
            raise exc.HTTPBadRequest(msg)

        # Name is the only property that can be updated
        name = data.get(consts.POLICY_NAME, None)
        if not name:
            raise exc.HTTPBadRequest(_("Policy name not specified."))

        policy = self.rpc_client.policy_update(req.context, policy_id, name)

        return {'policy': policy}

    @util.policy_enforce
    def delete(self, req, policy_id):
        self.rpc_client.policy_delete(req.context, policy_id, cast=False)
