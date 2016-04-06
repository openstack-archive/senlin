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

from oslo_context import context as base_context
from oslo_utils import encodeutils

from senlin.common import policy
from senlin.db import api as db_api
from senlin.drivers import base as driver_base


class RequestContext(base_context.RequestContext):
    '''Stores information about the security context.

    The context encapsulates information related to the user accessing the
    the system, as well as additional request information.
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
            request_id=request_id,
            roles=roles)

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
        d = super(RequestContext, self).to_dict()
        d.update({
            'auth_url': self.auth_url,
            'auth_token_info': self.auth_token_info,
            'user_name': self.user_name,
            'user_domain_name': self.user_domain_name,
            'project': self.project,
            'project_name': self.project_name,
            'project_domain_name': self.project_domain_name,
            'domain_name': self.domain_name,
            'trusts': self.trusts,
            'region_name': self.region_name,
            'password': self.password})
        return d

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def get_service_context(**kwargs):
    '''An abstraction layer for getting service credential.

    There could be multiple cloud backends for senlin to use. This
    abstraction layer provides an indirection for senlin to get the
    credentials of 'senlin' user on the specific cloud. By default,
    this credential refers to the credentials built for keystone middleware
    in an OpenStack cloud.
    '''
    identity_service = driver_base.SenlinDriver().identity
    return identity_service.get_service_credentials(**kwargs)


def get_admin_context():
    """Create an administrator context."""
    return RequestContext(is_admin=True)
