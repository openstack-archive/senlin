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
from senlin.rpc import client as rpc_client


class ProfileData(object):
    '''The data accompanying a POST/PUT request to create/update a profile.'''

    PARAMS = (
        NAME, SPEC, TYPE, PERMISSION, TAGS,
    ) = (
        'name', 'spec', 'type', 'permission', 'tags',
    )

    def __init__(self, data):
        self.data = data['profile']

    def name(self):
        if self.NAME not in self.data:
            raise exc.HTTPBadRequest(_("No profile name specified"))
        return self.data[self.NAME]

    def spec(self):
        if self.SPEC not in self.data:
            raise exc.HTTPBadRequest(_("No profile spec provided"))
        return self.data[self.SPEC]

    def type(self):
        if self.TYPE not in self.data:
            raise exc.HTTPBadRequest(_("No profile type provided"))
        return self.data[self.TYPE]

    def permission(self):
        return self.data.get(self.PERMISSION)

    def tags(self):
        return self.data.get(self.TAGS)


class ProfileController(object):
    '''WSGI controller for profiles resource in Senlin v1 API.'''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profiles'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'name': 'mixed',
            'type': 'mixed',
            'created_time': 'single',
            'updated_time': 'single',
            'deleted_time': 'single',
            'permission': 'mixed',
            'tags': 'mixed',
        }
        param_whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
            'show_deleted': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        if not filters:
            filters = None

        profiles = self.rpc_client.profile_list(req.context,
                                                filters=filters,
                                                **params)

        # TODO(Qiming): Add profiles_view to handle profile collection?
        return {'profiles': profiles}

    @util.policy_enforce
    def create(self, req, body):
        data = ProfileData(body)
        result = self.rpc_client.profile_create(req.context,
                                                data.name(),
                                                data.type(),
                                                data.spec(),
                                                data.permission(),
                                                data.tags())

        return {'profile': result}

    @util.policy_enforce
    def get(self, req, profile_id):
        profile = self.rpc_client.profile_get(req.context,
                                              profile_id)

        return {'profile': profile}

    @util.policy_enforce
    def update(self, req, profile_id, body):
        data = ProfileData(body)
        self.rpc_client.profile_update(req.context,
                                       profile_id,
                                       data.name(),
                                       data.spec(),
                                       data.permission(),
                                       data.tags())

        raise exc.HTTPAccepted()

    @util.policy_enforce
    def delete(self, req, profile_id):
        res = self.rpc_client.profile_delete(req.context,
                                             profile_id,
                                             cast=False)

        if res is not None:
            raise exc.HTTPBadRequest(res['Error'])

        raise exc.HTTPNoContent()


def create_resource(options):
    '''Profiles resource factory method.'''

    return wsgi.Resource(ProfileController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
