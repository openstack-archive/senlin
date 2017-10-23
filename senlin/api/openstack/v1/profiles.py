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
Profile endpoint for Senlin v1 ReST API.
"""

from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.objects import base as obj_base


class ProfileController(wsgi.Controller):
    """WSGI controller for profiles resource in Senlin v1 API."""

    # Define request scope
    # (must match what is in policy file and policies in code.)
    REQUEST_SCOPE = 'profiles'

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.PROFILE_NAME: 'mixed',
            consts.PROFILE_TYPE: 'mixed',
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if key not in whitelist.keys():
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)

        params = util.get_allowed_params(req.params, whitelist)

        project_safe = not util.parse_bool_param(
            consts.PARAM_GLOBAL_PROJECT,
            params.pop(consts.PARAM_GLOBAL_PROJECT, False))
        params['project_safe'] = project_safe

        obj = util.parse_request('ProfileListRequest', req, params)
        profiles = self.rpc_client.call(req.context, 'profile_list', obj)
        return {'profiles': profiles}

    @util.policy_enforce
    def create(self, req, body):

        obj = util.parse_request('ProfileCreateRequest', req, body, 'profile')
        result = self.rpc_client.call(req.context, 'profile_create', obj)
        return {'profile': result}

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def validate(self, req, body):

        obj = util.parse_request(
            'ProfileValidateRequest', req, body, 'profile')
        result = self.rpc_client.call(req.context, 'profile_validate', obj)
        return {'profile': result}

    @util.policy_enforce
    def get(self, req, profile_id):
        params = {'identity': profile_id}

        obj = util.parse_request('ProfileGetRequest', req, params)
        profile = self.rpc_client.call(req.context, 'profile_get', obj)
        return {'profile': profile}

    @util.policy_enforce
    def update(self, req, profile_id, body):
        profile_data = body.get('profile', None)
        if profile_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'profile' key in request body."))

        body_req = obj_base.SenlinObject.normalize_req(
            'ProfileUpdateRequestBody', profile_data)
        obj = util.parse_request(
            'ProfileUpdateRequest', req, {'identity': profile_id,
                                          'profile': body_req})

        profile = self.rpc_client.call(req.context, 'profile_update', obj)
        return {'profile': profile}

    @util.policy_enforce
    def delete(self, req, profile_id):

        obj = util.parse_request(
            'ProfileDeleteRequest', req, {'identity': profile_id})
        self.rpc_client.call(req.context, 'profile_delete', obj)
        raise exc.HTTPNoContent()
