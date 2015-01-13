#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Profile endpoint for Senlin v1 ReST API.
"""

from webob import exc

from senlin.api.openstack.v1 import util
from senlin.common import serializers
from senlin.common import wsgi
from senlin.openstack.common import log as logging
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class ProfileTypeController(object):
    """
    WSGI controller for profiles resource in Senlin v1 API
    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profiles'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        """
        Lists all available profile_types
        """
        profile_types = self.rpc_client.list_profile_types(req.context)

        return {'profile_types': profile_types}

    @util.policy_enforce
    def spec(self, req, type_name):
        """
        Gets the interface schema for a specified profile type.
        """

        profile_type_spec = self.rpc_client.profile_type_spec(req.context,
                                                              type_name)

        if not profile_type_spec:
            raise exc.HTTPInternalServerError()

        return profile_type_spec

    @util.policy_enforce
    def template(self, req, type_name):
        """
        Gets the template representation for a specified profile type.
        """

        profile_type_template = self.rpc_client.profile_type_template(
            req.context,
            type_name)

        if not profile_type_template:
            raise exc.HTTPInternalServerError()

        return profile_type_template


class ProfileTypeSerializer(serializers.JSONResponseSerializer):
    """Handles serialization of specific controller method responses."""

    def _populate_response_header(self, response, location, status):
        response.status = status
        response.headers['Location'] = location.encode('utf-8')
        response.headers['Content-Type'] = 'application/json'
        return response

    def create(self, response, result):
        self._populate_response_header(response,
                                       result['profile']['links'][0]['href'],
                                       201)
        response.body = self.to_json(result)
        return response


def create_resource(options):
    """
    Profiles resource factory method.
    """
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = ProfileTypeSerializer()
    return wsgi.Resource(ProfileTypeController(options),
                         deserializer,
                         serializer)
