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

from oslo_config import cfg

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.rpc import client as rpc_client


class BuildInfoController(wsgi.Controller):
    """WSGI controller for BuildInfo in Senlin v1 API."""

    # Define request scope
    # (must match what is in policy file and policies in code.)
    REQUEST_SCOPE = 'build_info'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def build_info(self, req):
        obj = util.parse_request('GetRevisionRequest', req, {})
        engine_revision = self.rpc_client.call(req.context, 'get_revision',
                                               obj)
        build_info = {
            'api': {'revision': cfg.CONF.revision['senlin_api_revision']},
            'engine': {'revision': engine_revision}
        }

        return {'build_info': build_info}
