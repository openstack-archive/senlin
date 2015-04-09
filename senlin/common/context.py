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
from oslo_context import context
from oslo_middleware import request_id as oslo_request_id
from oslo_utils import encodeutils
from oslo_utils import importutils

from senlin.common import exception
from senlin.common import policy
from senlin.common import wsgi
from senlin.db import api as db_api

CONF = cfg.CONF


class RequestContext(context.RequestContext):
    '''Stores information about the security context.

    The context encapsulates information related to the user
    accesses the system, as well as additional request information.
    '''

    def __init__(self, auth_token=None, user=None, project=None,
                 domain=None, user_domain=None, project_domain=None,
                 is_admin=None, read_only=False, show_deleted=False,
                 request_id=None, auth_url=None, trusts=None,
                 user_name=None, project_name=None, domain_name=None,
                 user_domain_name=None, project_domain_name=None,
                 auth_token_info=None, region_name=None, roles=None,
                 password=None, **kwargs):
        '''Initializer of request context.'''

        # We still have 'tenant' param because oslo_context still use it.
        super(RequestContext, self).__init__(
            auth_token=auth_token, user=user, tenant=project,
            domain=domain, user_domain=user_domain,
            project_domain=project_domain,
            read_only=read_only, show_deleted=show_deleted,
            request_id=request_id)

        # request_id might be a byte array
        self.request_id = encodeutils.safe_decode(self.request_id)

        # we save an additional 'project' internally for use
        self.project = project

        # Session for DB access
        self._session = None

        self.auth_url = auth_url
        self.trusts = trusts

        self.user_name = user_name
        self.project_name = project_name
        self.domain_name = domain_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name

        self.auth_token_info = auth_token_info
        self.region_name = region_name
        self.roles = roles or []
        self.password = password

        # Check user is admin or not
        if is_admin is None:
            self.is_admin = policy.enforce(self, 'context_is_admin',
                                           target={'project': self.project},
                                           do_raise=False)
        else:
            self.is_admin = is_admin

    @property
    def session(self):
        if self._session is None:
            self._session = db_api.get_session()
        return self._session

    def to_dict(self):
        return {
            'auth_url': self.auth_url,
            'auth_token': self.auth_token,
            'auth_token_info': self.auth_token_info,
            'user': self.user,
            'user_name': self.user_name,
            'user_domain': self.user_domain,
            'user_domain_name': self.user_domain_name,
            'project': self.project,
            'project_name': self.project_name,
            'project_domain': self.project_domain,
            'project_domain_name': self.project_domain_name,
            'domain': self.domain,
            'domain_name': self.domain_name,
            'trusts': self.trusts,
            'region_name': self.region_name,
            'roles': self.roles,
            'show_deleted': self.show_deleted,
            'is_admin': self.is_admin,
            'request_id': self.request_id,
            'password': self.password,
        }

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    @classmethod
    def get_service_context(cls):
        params = {
            'user_name': CONF.keystone_authtoken.admin_user,
            'password': CONF.keystone_authtoken.admin_password,
            'auth_url': CONF.keystone_authtoken.auth_uri,
            'project_name': CONF.keystone_authtoken.admin_tenant_name
        }
        return cls(**params)


class ContextMiddleware(wsgi.Middleware):

    def __init__(self, app, conf, **local_conf):
        # Determine the context class to use
        self.ctxcls = RequestContext
        if 'context_class' in local_conf:
            self.ctxcls = importutils.import_class(local_conf['context_class'])

        super(ContextMiddleware, self).__init__(app)

    def make_context(self, *args, **kwargs):
        '''Create a context with the given arguments.'''

        return self.ctxcls(*args, **kwargs)

    def process_request(self, req):
        '''Build context from authentication info extracted from request.'''

        headers = req.headers
        environ = req.environ
        try:
            auth_url = headers.get('X-Auth-Url')
            if not auth_url:
                # Use auth_url defined in senlin.conf
                importutils.import_module('keystonemiddleware.auth_token')
                auth_url = cfg.CONF.keystone_authtoken.auth_uri

            auth_token = headers.get('X-Auth-Token')
            auth_token_info = environ.get('keystone.token_info')

            project = headers.get('X-Project-Id')
            project_name = headers.get('X-Project-Name')
            project_domain = headers.get('X-Project-Domain-Id')
            project_domain_name = headers.get('X-Project-Domain-Name')

            user = headers.get('X-User-Id')
            user_name = headers.get('X-User-Name')
            user_domain = headers.get('X-User-Domain-Id')
            user_domain_name = headers.get('X-User-Domain-Name')

            domain = headers.get('X-Domain-Id')
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

        req.context = self.make_context(
            auth_token=auth_token,
            user=user,
            project=project,
            domain=domain,
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
            roles=roles)


def ContextMiddleware_filter_factory(global_conf, **local_conf):
    '''Factory method for paste.deploy.'''

    conf = global_conf.copy()
    conf.update(local_conf)

    def filter(app):
        return ContextMiddleware(app, conf)

    return filter
