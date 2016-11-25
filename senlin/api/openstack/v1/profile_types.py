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
Profile type endpoint for Senlin v1 ReST API.
"""

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.objects import base as obj_base
from senlin.objects.requests import profile_type as vorp


class ProfileTypeController(wsgi.Controller):
    """WSGI controller for profile types resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profile_types'

    @util.policy_enforce
    def index(self, req):
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileTypeListRequest', {})
            obj = vorp.ProfileTypeListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        types = self.rpc_client.call2(req.context, 'profile_type_list2', obj)
        return {'profile_types': types}

    @util.policy_enforce
    def get(self, req, type_name):
        """Gets the details about a specified profile type."""
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ProfileTypeGetRequest', {'type_name': type_name})
            obj = vorp.ProfileTypeGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        content = self.rpc_client.call2(req.context, 'profile_type_get2', obj)
        return {'profile_type': content}
