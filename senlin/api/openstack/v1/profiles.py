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

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import utils
from senlin.objects import base as obj_base
from senlin.objects.requests import profiles as vorp


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

        project_safe = not utils.parse_bool_param(
            consts.PARAM_GLOBAL_PROJECT,
            params.pop(consts.PARAM_GLOBAL_PROJECT, False))
        params['project_safe'] = project_safe

        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileListRequest', params)
            obj = vorp.ProfileListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        profiles = self.rpc_client.call2(req.context, 'profile_list2', obj)
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

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def validate(self, req, body):
        profile_data = body.get('profile')
        if profile_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'profile' key in request body."))
        if consts.PROFILE_SPEC not in profile_data:
            raise exc.HTTPBadRequest(_("No profile spec provided"))

        result = self.rpc_client.profile_validate(
            req.context, profile_data[consts.PROFILE_SPEC])

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

        # Spec is not allowed to be updated
        spec = profile_data.get(consts.PROFILE_SPEC)
        if spec is not None:
            msg = _("Updating the spec of a profile is not supported because "
                    "it may cause state conflicts in engine.")
            raise exc.HTTPBadRequest(msg)

        # Handle updatable properties including name and metadata
        name = profile_data.get(consts.PROFILE_NAME, None)
        metadata = profile_data.get(consts.PROFILE_METADATA, None)
        # We don't check if type is specified or not
        profile = self.rpc_client.profile_update(req.context, profile_id,
                                                 name, metadata)

        return {'profile': profile}

    @util.policy_enforce
    def delete(self, req, profile_id):
        self.rpc_client.profile_delete(req.context, profile_id, cast=False)
        raise exc.HTTPNoContent()
