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

import six

from openstack.identity.v3 import user
from oslo_config import cfg
from oslo_utils import importutils

from senlin.common import exception
from senlin.drivers import base
from senlin.drivers.openstack import sdk
from senlin.openstack.identity.v3 import trust

CONF = cfg.CONF

# Ensure keystonemiddleware options are imported
importutils.import_module('keystonemiddleware.auth_token')


class KeystoneClient(base.DriverBase):
    '''Keystone V3 driver.'''

    def __init__(self, context):
        conn = sdk.create_connection(context)
        self.session = conn.session
        self.auth = self.session.authenticator

    def user_get(self, **params):
        obj = user.User.new(**params)
        try:
            return obj.get(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def user_list(self, **params):
        try:
            return user.User.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def trust_list(self, **params):
        try:
            return trust.Trust.list(self.session, **params)
        except sdk.exc.HttpException as ex:
            raise ex

    def trust_delete(self, **params):
        obj = trust.Trust.new(**params)
        try:
            return obj.delete(self.session)
        except sdk.exc.HttpException as ex:
            raise ex

    def user_get_by_name(self, user_name):
        '''Utility function to convert user name to ID.'''
        params = {'name': user_name}
        users = [u for u in self.user_list(**params)]
        if len(users) == 0:
            raise exception.UserNotFound(user=user_name)

        return users[0].id

    def trust_get_by_trustor(self, trustor, trustee=None, project=None):
        '''Get trust by trustor.

        :param trustor: ID of the user who is the trustor, not None;
        :param trustee: ID of the user who is the trustee;
        :param project: ID of the project to which the trust is scoped.
        '''
        try:
            trusts = trust.Trust.list(self.session, trustor_user_id=trustor)
        except sdk.exc.HttpException:
            raise exception.TrustNotFound(trustor=trustor)

        results = []
        for t in trusts:
            if trustee is not None and trustee == t.trustee_user_id:
                if project is not None and project == t.project_id:
                    results.append(t)

        return results

    def trust_create(self, trustor, trustee, project, roles,
                     impersonation=True):
        '''Create trust between two users.

        :param trustor: ID of the user who is the trustor.
        :param trustee: ID of the user who is the trustee.
        :param project: Scope of of the trust which is a project ID.
        :param roles: List of roles the trustee will inherit from the trustor.
        :param impersonation: Whether the trustee is allowed to impersonate
                              the trustor.
        '''

        params = {
            'trustor_user_id': trustor,
            'trustee_user_id': trustee,
            'project_id': project,
            'impersonation': impersonation,
            'allow_redelegation': True,
            'roles': [{'name': role} for role in roles]
        }

        obj = trust.Trust.new(**params)
        try:
            result = obj.create(self.session)
        except sdk.exc.HttpException as ex:
            raise exception.Error(message=six.text_type(ex))

        return result


def get_service_credentials(**kwargs):
    '''Senlin service credential to use with Keystone.

    :param args: An additional keyword argument list that can be used
                 for customizing the default settings.
    '''

    creds = {
        'user_name': CONF.keystone_authtoken.admin_user,
        'password': CONF.keystone_authtoken.admin_password,
        'auth_url': CONF.keystone_authtoken.auth_uri,
        'project_name': CONF.keystone_authtoken.admin_tenant_name,
        'user_domain_name': 'Default',
        'project_domain_name': 'Default',
    }
    creds.update(**kwargs)
    return creds
