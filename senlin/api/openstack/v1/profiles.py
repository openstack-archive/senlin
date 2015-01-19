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

from senlin.api.openstack.v1 import util
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import wsgi
from senlin.openstack.common import log as logging
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class ProfileData(object):
    """
    The data accompanying a PUT or POST request to create or update a cluster.
    """

    PARAMS = (NAME, SPEC, TYPE, PERMISSION, TAGS,
    ) = ('name', 'spec', 'type', 'permission', 'tags',
    )

    def __init__(self, data):
        self.data = data

    def name(self):
        if self.NAME not in self.data:
            raise exc.HTTPBadRequest(_("No profile name specified"))
        return self.data[self.NAME]

    def spec(self):
        if self.SPEC not in self.data:
            raise exc.HTTPBadRequest(_("No profile spec provided"))
        return self.data[self.self.SPEC]

    def type(self):
        if self.TYPE not in self.data:
            raise exc.HTTPBadRequest(_("No profile type provided"))
        return self.data[self.self.TYPE]

    def permission(self):
        if self.PERMISSION not in self.data:
            return None
        return self.data[self.PERMISSION]

    def tags(self):
        if self.TAGS not in self.data:
            return None
        return self.data[self.self.TAGS]


class ProfileController(object):
    '''WSGI controller for profiles resource in Senlin v1 API.
    '''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profiles'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    def _index(self, req, tenant_safe=True):
        filter_whitelist = {
            'type': 'mixed',
            'show_deleted': 'mixed',
            'permission': 'mixed',
            'tags': 'mixed',
        }
        whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
        }
        params = util.get_allowed_params(req.params, whitelist)
        filter_params = util.get_allowed_params(req.params, filter_whitelist)

        if not filter_params:
            filter_params = None

        profiles = self.rpc_client.list_profiles(req.context,
                                                 filters=filter_params,
                                                 tenant_safe=tenant_safe,
                                                 **params)

        # TODO: Add profiles_view to handle profile collection?
        return {'profiles': profiles}

    @util.policy_enforce
    def global_index(self, req):
        return self._index(req, tenant_safe=False)

    @util.policy_enforce
    def index(self, req):
        global_tenant = bool(req.params.get('global_tenant', False))
        if global_tenant:
            return self.global_index(req, req.context.tenant_id)

        return self._index(req)

    @util.policy_enforce
    def create(self, req, body):
        data = ProfileData(body)
        result = self.rpc_client.create_profile(req.context,
                                                data.name(),
                                                data.spec(),
                                                data.type(),
                                                data.permission(),
                                                data.tags())

        return {'profile': result}

    @util.policy_enforce
    def get(self, req, profile_id):
        profile = self.rpc_client.show_profile(req.context,
                                               profile_id)

        if not profile:
            raise exc.HTTPInternalServerError()

        return {'profile': profile}

    @util.policy_enforce
    def update(self, req, profile_id, body):
        data = ProfileData(body)
        self.rpc_client.update_profile(req.context,
                                       profile_id,
                                       data.name(),
                                       data.spec(),
                                       data.permission(),
                                       data.tags())

        raise exc.HTTPAccepted()

    @util.policy_enforce
    def delete(self, req, profile_id):
        res = self.rpc_client.delete_profile(req.context,
                                             profile_id,
                                             cast=False)

        if res is not None:
            raise exc.HTTPBadRequest(res['Error'])

        raise exc.HTTPNoContent()


class ProfileSerializer(serializers.JSONResponseSerializer):
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
    serializer = ProfileSerializer()
    return wsgi.Resource(ProfileController(options), deserializer, serializer)
