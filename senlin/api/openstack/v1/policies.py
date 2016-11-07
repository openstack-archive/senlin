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

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import utils
from senlin.objects import base as obj_base
from senlin.objects.requests import policies as vorp


class PolicyController(wsgi.Controller):
    """WSGI controller for policy resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
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

        unsafe = utils.parse_bool_param(consts.PARAM_GLOBAL_PROJECT,
                                        is_global)
        params['project_safe'] = not unsafe
        norm_req = obj_base.SenlinObject.normalize_req(
            'PolicyListRequest', params, None)
        obj = None
        try:
            obj = vorp.PolicyListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        policies = self.rpc_client.call2(req.context, 'policy_list2', obj)
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
        """Gets detailed information for a policy"""
        norm_req = obj_base.SenlinObject.normalize_req(
            'PolicyGetRequest', {'identity': policy_id})
        obj = None
        try:
            obj = vorp.PolicyGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        policy = self.rpc_client.call2(req.context, 'policy_get2', obj)

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
        raise exc.HTTPNoContent()

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def validate(self, req, body):
        data = body.get('policy', None)
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))
        spec = data.get(consts.POLICY_SPEC, None)
        if not spec:
            raise exc.HTTPBadRequest(_("No policy spec provided"))

        result = self.rpc_client.policy_validate(req.context, spec)

        return {'policy': result}
