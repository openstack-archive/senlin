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
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client


class ProfileData(object):
    '''The data accompanying a POST/PUT request to create/update a profile.'''

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

    def permission(self):
        return self.data.get(consts.PROFILE_PERMISSION, None)

    def metadata(self):
        return self.data.get(consts.PROFILE_METADATA, None)

    def context(self):
        return self.data.get(consts.PROFILE_CONTEXT, None)


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
            'metadata': 'mixed',
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

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        if not filters:
            filters = None

        profiles = self.rpc_client.profile_list(req.context,
                                                filters=filters,
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
                                                data.permission(),
                                                data.metadata())

        return {'profile': result}

    @util.policy_enforce
    def get(self, req, profile_id):
        profile = self.rpc_client.profile_get(req.context,
                                              profile_id)

        return {'profile': profile}

    @util.policy_enforce
    def update(self, req, profile_id, body):
        '''The update operation actually creates a new profile.'''
        profile_data = body.get('profile', None)
        if profile_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'profile' key in request body."))
        # spec can be empty in an update request
        name = profile_data.get(consts.PROFILE_NAME, None)
        spec = profile_data.get(consts.PROFILE_SPEC, None)
        permission = profile_data.get(consts.PROFILE_PERMISSION, None)
        metadata = profile_data.get(consts.PROFILE_METADATA, None)
        # We don't check if type is specified or not
        profile = self.rpc_client.profile_update(req.context, profile_id,
                                                 name, spec, permission,
                                                 metadata)

        return {'profile': profile}

    @util.policy_enforce
    def delete(self, req, profile_id):
        self.rpc_client.profile_delete(req.context, profile_id, cast=False)

        raise exc.HTTPNoContent()


def create_resource(options):
    '''Profiles resource factory method.'''

    return wsgi.Resource(ProfileController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
