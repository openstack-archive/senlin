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
Policy type endpoint for Senlin v1 ReST API.
"""

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.objects import base as obj_base
from senlin.objects.requests import policy_type as orpt


class PolicyTypeController(wsgi.Controller):
    """WSGI controller for policy types resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'policy_types'

    @util.policy_enforce
    def index(self, req):
        """Gets the supported policy types"""
        norm_req = obj_base.SenlinObject.normalize_req(
            'PolicyTypeListRequest', {})
        obj = None
        try:
            obj = orpt.PolicyTypeListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        types = self.rpc_client.call2(req.context, 'policy_type_list2', obj)
        return {'policy_types': types}

    @util.policy_enforce
    def get(self, req, type_name):
        """Gets detailed information for a policy-type"""
        norm_req = obj_base.SenlinObject.normalize_req(
            'PolicyTypeGetRequest', {'type_name': type_name})
        obj = None
        try:
            obj = orpt.PolicyTypeGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        content = self.rpc_client.call2(req.context, 'policy_type_get2', obj)
        return {'policy_type': content}
