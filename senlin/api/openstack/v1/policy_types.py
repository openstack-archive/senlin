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

'''
Policy type endpoint for Senlin v1 ReST API.
'''

from webob import exc

from senlin.api.openstack.v1 import util
from senlin.common import serializers
from senlin.common import wsgi
from senlin.openstack.common import log as logging
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class PolicyTypeController(object):
    '''
    WSGI controller for policy types resource in Senlin v1 API
    '''
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'policy_types'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        '''
        Lists all available policy types
        '''
        types = self.rpc_client.list_policy_types(req.context)
        return {'policy_types': types}

    @util.policy_enforce
    def spec(self, req, type_name):
        '''
        Gets the interface schema for a specified policy type.
        '''
        spec = self.rpc_client.policy_type_spec(req.context, type_name)
        if not spec:
            raise exc.HTTPInternalServerError()

        return spec

    @util.policy_enforce
    def template(self, req, type_name):
        '''
        Gets the template representation for a specified policy type.
        '''
        tmpl = self.rpc_client.policy_type_template(req.context, type_name)
        if not tmpl:
            raise exc.HTTPInternalServerError()

        return tmpl


def create_resource(options):
    '''
    Policy type resource factory method.
    '''
    return wsgi.Resource(PolicyTypeController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
