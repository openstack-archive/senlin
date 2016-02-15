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
from senlin.api.common import wsgi


class ProfileTypeController(wsgi.Controller):
    """WSGI controller for profile types resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profile_types'

    @util.policy_enforce
    def index(self, req):
        types = self.rpc_client.profile_type_list(req.context)
        return {'profile_types': types}

    @util.policy_enforce
    def get(self, req, type_name):
        """Gets the details about a specified profile type."""
        content = self.rpc_client.profile_type_get(req.context, type_name)
        return {'profile_type': content}
