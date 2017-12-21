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

from oslo_config import cfg
from oslo_middleware import request_id as oslo_request_id
from oslo_utils import encodeutils

from senlin.api.common import wsgi
from senlin.common import context
from senlin.common import exception


class ContextMiddleware(wsgi.Middleware):

    def process_request(self, req):
        """Build context from authentication info extracted from request."""

        headers = req.headers
        environ = req.environ
        try:
            auth_url = headers.get('X-Auth-Url')
            if not auth_url:
                # Use auth_url defined in senlin.conf
                auth_url = cfg.CONF.authentication.auth_url

            auth_token = headers.get('X-Auth-Token')
            auth_token_info = environ.get('keystone.token_info')

            project_id = headers.get('X-Project-Id')
            project_name = headers.get('X-Project-Name')
            project_domain = headers.get('X-Project-Domain-Id')
            project_domain_name = headers.get('X-Project-Domain-Name')

            user_id = headers.get('X-User-Id')
            user_name = headers.get('X-User-Name')
            user_domain = headers.get('X-User-Domain-Id')
            user_domain_name = headers.get('X-User-Domain-Name')

            domain_id = headers.get('X-Domain-Id')
            domain_name = headers.get('X-Domain-Name')

            region_name = headers.get('X-Region-Name')

            roles = headers.get('X-Roles')
            if roles is not None:
                roles = roles.split(',')

            env_req_id = environ.get(oslo_request_id.ENV_REQUEST_ID)
            if env_req_id is None:
                request_id = None
            else:
                request_id = encodeutils.safe_decode(env_req_id)

        except Exception:
            raise exception.NotAuthenticated()

        api_version = str(req.version_request)
        req.context = context.RequestContext(
            auth_token=auth_token,
            user_id=user_id,
            project_id=project_id,
            domain_id=domain_id,
            user_domain=user_domain,
            project_domain=project_domain,
            request_id=request_id,
            auth_url=auth_url,
            user_name=user_name,
            project_name=project_name,
            domain_name=domain_name,
            user_domain_name=user_domain_name,
            project_domain_name=project_domain_name,
            auth_token_info=auth_token_info,
            region_name=region_name,
            roles=roles,
            api_version=api_version
        )
