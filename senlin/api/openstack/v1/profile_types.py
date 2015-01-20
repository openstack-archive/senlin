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

'''
Profile type endpoint for Senlin v1 ReST API.
'''

from webob import exc

from senlin.api.openstack.v1 import util
from senlin.common import serializers
from senlin.common import wsgi
from senlin.openstack.common import log as logging
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class ProfileTypeController(object):
    '''
    WSGI controller for profile types resource in Senlin v1 API
    '''
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'profile_types'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        types = self.rpc_client.profile_type_list(req.context)
        return {'profile_types': types}

    @util.policy_enforce
    def spec(self, req, type_name):
        '''
        Gets the interface schema for a specified profile type.
        '''
        spec = self.rpc_client.profile_type_spec(req.context, type_name)
        if not spec:
            raise exc.HTTPInternalServerError()

        return spec

    @util.policy_enforce
    def template(self, req, type_name):
        '''
        Gets the template representation for a specified profile type.
        '''
        tmpl = self.rpc_client.profile_type_template(req.context, type_name)
        if not tmpl:
            raise exc.HTTPInternalServerError()

        return tmpl


def create_resource(options):
    '''
    Profiles resource factory method.
    '''
    return wsgi.Resource(ProfileTypeController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
