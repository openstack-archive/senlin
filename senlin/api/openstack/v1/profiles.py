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
from senlin.objects import base as obj_base
from senlin.objects.requests import profiles as vorp


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

        project_safe = not util.parse_bool_param(
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
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileCreateRequest', body, 'profile')
            obj = vorp.ProfileCreateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        result = self.rpc_client.call2(req.context, 'profile_create2', obj)
        return {'profile': result}

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def validate(self, req, body):
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileValidateRequest', body, 'profile')

            obj = vorp.ProfileValidateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        result = self.rpc_client.call2(req.context, 'profile_validate2', obj)
        return {'profile': result}

    @util.policy_enforce
    def get(self, req, profile_id):
        params = {'identity': profile_id}
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileGetRequest', params)
            obj = vorp.ProfileGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        profile = self.rpc_client.call2(req.context, 'profile_get2', obj)
        return {'profile': profile}

    @util.policy_enforce
    def update(self, req, profile_id, body):
        profile_data = body.get('profile', None)
        if profile_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'profile' key in request body."))

        try:
            body_req = obj_base.SenlinObject.normalize_req(
                'ProfileUpdateRequestBody', profile_data)
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileUpdateRequest', {'identity': profile_id,
                                         'profile': body_req})
            obj = vorp.ProfileUpdateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        profile = self.rpc_client.call2(req.context, 'profile_update2', obj)
        return {'profile': profile}

    @util.policy_enforce
    def delete(self, req, profile_id):
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileDeleteRequest', {'identity': profile_id})
            obj = vorp.ProfileDeleteRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        self.rpc_client.call2(req.context, 'profile_delete2', obj)
        raise exc.HTTPNoContent()
