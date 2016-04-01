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
from senlin.common import utils


class ProfileData(object):
    """The data accompanying a POST/PUT request to create/update a profile."""

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.PROFILE_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No profile name specified"))
        return self.data[consts.PROFILE_NAME]

    def spec(self):
        if consts.PROFILE_SPEC not in self.data:
            raise exc.HTTPBadRequest(_("No profile spec provided"))
        return self.data[consts.PROFILE_SPEC]

    def metadata(self):
        return self.data.get(consts.PROFILE_METADATA, None)


class ProfileController(wsgi.Controller):
    """WSGI controller for profiles resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profiles'

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            consts.PROFILE_NAME: 'mixed',
            consts.PROFILE_TYPE: 'mixed',
            consts.PROFILE_METADATA: 'mixed',
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

        profiles = self.rpc_client.profile_list(req.context, filters=filters,
                                                **params)

        return {'profiles': profiles}

    @util.policy_enforce
    def create(self, req, body):
        profile_data = body.get('profile')
        if profile_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'profile' key in request body."))

        data = ProfileData(profile_data)
        result = self.rpc_client.profile_create(req.context,
                                                data.name(),
                                                data.spec(),
                                                data.metadata())

        return {'profile': result}

    @util.policy_enforce
    def get(self, req, profile_id):
        profile = self.rpc_client.profile_get(req.context,
                                              profile_id)

        return {'profile': profile}

    @util.policy_enforce
    def update(self, req, profile_id, body):

        profile_data = body.get('profile', None)
        if profile_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'profile' key in request body."))
        # We ignore the 'spec' property even if it is specified.
        name = profile_data.get(consts.PROFILE_NAME, None)
        metadata = profile_data.get(consts.PROFILE_METADATA, None)
        # We don't check if type is specified or not
        profile = self.rpc_client.profile_update(req.context, profile_id,
                                                 name, metadata)

        return {'profile': profile}

    @util.policy_enforce
    def delete(self, req, profile_id):
        self.rpc_client.profile_delete(req.context, profile_id, cast=False)
