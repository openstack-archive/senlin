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

from senlin.api.common import util
from senlin.api.common import version_request as vr
from senlin.api.common import wsgi


class ProfileTypeController(wsgi.Controller):
    """WSGI controller for profile types resource in Senlin v1 API."""

    # Define request scope
    # (must match what is in policy file and policies in code.)
    REQUEST_SCOPE = 'profile_types'

    @util.policy_enforce
    def index(self, req):

        obj = util.parse_request('ProfileTypeListRequest', req, {})
        types = self.rpc_client.call(req.context, 'profile_type_list', obj)
        result = types
        if req.version_request <= vr.APIVersionRequest("1.4"):
            # We return only profile type name before 1.5
            result = [{'name': '-'.join((t['name'], t['version']))}
                      for t in types]
        return {'profile_types': result}

    @util.policy_enforce
    def get(self, req, type_name):
        """Gets the details about a specified profile type."""

        obj = util.parse_request(
            'ProfileTypeGetRequest', req, {'type_name': type_name})
        content = self.rpc_client.call(req.context, 'profile_type_get', obj)
        key = 'support_status'
        if req.version_request <= vr.APIVersionRequest("1.4"):
            # We return support_status from 1.5
            if key in content:
                content.pop(key)
        return {'profile_type': content}

    @wsgi.Controller.api_version('1.4')
    @util.policy_enforce
    def ops(self, req, type_name):
        """Lists the operations supported by the specified profile type."""

        obj = util.parse_request(
            'ProfileTypeOpListRequest', req, {'type_name': type_name})
        return self.rpc_client.call(req.context, 'profile_type_ops', obj)
