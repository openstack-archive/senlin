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

from oslo_context import context
from oslo_log import log as logging
from oslo_middleware import request_id as oslo_request_id
from oslo_utils import importutils

from senlin.common import exception
from senlin.common import policy
from senlin.common import wsgi
from senlin.db import api as db_api

LOG = logging.getLogger(__name__)


class RequestContext(context.RequestContext):
    '''Stores information about the security context.

    The context encapsulates information related to the user
    accesses the system, as well as additional request information.
    '''

    def __init__(self, auth_token=None, auth_token_info=None,
                 username=None, user_id=None, password=None,
                 trusts=None, is_admin=None,
                 tenant=None, tenant_id=None, auth_url=None,
                 domain_id=None, project_id=None, project_domain_id=None,
                 user_domain_id=None,
                 region_name=None, roles=None,
                 read_only=False, show_deleted=False,
                 request_id=None, **kwargs):
        '''Initializer of request context.

         :param kwargs: Extra arguments that might be present, but we ignore
            because they possibly came in from older rpc messages.
        '''
        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=username,
                                             tenant=tenant,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id)
        # Session for DB access
        self._session = None

        self.auth_url = auth_url
        self.auth_token_info = auth_token_info

        self.user_id = user_id
        self.username = username
        self.password = password
        self.trusts = trusts

        # To be deprecated
        self.tenant_id = tenant_id

        self.domain_id = domain_id
        self.project_id = project_id
        self.project_domain_id = project_domain_id
        self.user_domain_id = user_domain_id

        self.region_name = region_name

        self.roles = roles or []

        # Check user is admin or not
        self.policy = policy.Enforcer()
        if is_admin is None:
            self.is_admin = self.policy.check_is_admin(self)
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
            'username': self.username,
            'user_id': self.user_id,
            'password': self.password,
            'trusts': self.trusts,
            'tenant': self.tenant,
            'tenant_id': self.tenant_id,
            'domain_id': self.domain_id,
            'project_id': self.project_id,
            'project_domain_id': self.project_domain_id,
            'user_domain_id': self.user_domain_id,
            'region_name': self.region_name,
            'roles': self.roles,
            'show_deleted': self.show_deleted,
            'is_admin': self.is_admin,
            'request_id': self.request_id
        }

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def get_admin_context(show_deleted=False):
    return RequestContext(is_admin=True, show_deleted=show_deleted)


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
            auth_token = headers.get('X-Auth-Token')
            auth_token_info = environ.get('keystone.token_info')

            tenant_id = headers.get('X-Tenant-Id')
            tenant_name = headers.get('X-Tenant-Name')

            domain_id = headers.get('X-Domain-Id')
            project_id = headers.get('X-Project-Id')
            project_domain_id = headers.get('X-Project-Domain-Id')

            user_id = headers.get('X-User-Id')
            username = headers.get('X-User-Name')
            password = None

            user_domain_id = headers.get('X-User-Domain-Id')

            if headers.get('X-Auth-User') is not None:
                username = headers.get('X-Auth-User')
                password = headers.get('X-Auth-Key')

            region_name = headers.get('X-Region-Name')
            roles = headers.get('X-Roles')
            if roles is not None:
                roles = roles.split(',')
            request_id = environ.get(oslo_request_id.ENV_REQUEST_ID)

        except Exception:
            raise exception.NotAuthenticated()

        req.context = self.make_context(
            auth_token=auth_token, auth_token_info=auth_token_info,
            username=username, user_id=user_id, password=password,
            tenant=tenant_name, tenant_id=tenant_id,
            auth_url=auth_url, domain_id=domain_id,
            project_id=project_id, project_domain_id=project_domain_id,
            user_domain_id=user_domain_id,
            region_name=region_name, roles=roles,
            request_id=request_id)


def ContextMiddleware_filter_factory(global_conf, **local_conf):
    '''Factory method for paste.deploy.'''

    conf = global_conf.copy()
    conf.update(local_conf)

    def filter(app):
        return ContextMiddleware(app, conf)

    return filter
