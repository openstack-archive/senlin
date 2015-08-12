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

from oslo_log import log as logging

from senlin.api.openstack.v1 import util
from senlin.common import serializers
from senlin.common import wsgi
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class PolicyTypeController(object):
    '''WSGI controller for policy types resource in Senlin v1 API.'''
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'policy_types'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        types = self.rpc_client.policy_type_list(req.context)
        return {'policy_types': types}

    @util.policy_enforce
    def schema(self, req, type_name):
        return self.rpc_client.policy_type_schema(req.context, type_name)


def create_resource(options):
    '''Policy type resource factory method.'''

    return wsgi.Resource(PolicyTypeController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
