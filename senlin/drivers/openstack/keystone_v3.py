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

from oslo_config import cfg

from senlin.common import exception
from senlin.common.i18n import _
from senlin.drivers import base
from senlin.drivers.openstack import sdk

CONF = cfg.CONF


class KeystoneClient(base.DriverBase):
    '''Keystone V3 driver.'''

    def __init__(self, context):
        self.conn = sdk.create_connection(context)
        self.session = self.conn.session

    def trust_list(self, **query):
        try:
            trusts = [t for t in self.conn.identity.trusts(**query)]
        except sdk.exc.HttpException as ex:
            raise ex

        return trusts

    def trust_delete(self, trust_id):
        try:
            self.conn.identity.delete_trust(trust_id, ignore_missing=True)
        except sdk.exc.HttpException as ex:
            raise ex

        return

    def user_get_by_name(self, user_name):
        try:
            user = self.conn.identity.find_user(user_name)
        except sdk.exc.HttpException:
            raise exception.UserNotFound(user=user_name)

        return user.id

    def endpoint_get(self, service_id, region=None, interface=None):
        '''Utility function to get endpoints of a service.'''
        filters = {
            'service_id': service_id,
        }
        if region:
            filters['region'] = region
        if interface:
            filters['interface'] = interface

        endpoints = [e for e in self.conn.identity.endpoints(**filters)]
        if len(endpoints) == 0:
            resource = _('endpoint: service=%(service)s,region='
                         '%(region)s,visibility=%(interface)s.'
                         ) % {'service': service_id,
                              'region': region,
                              'interface': interface}
            raise exception.ResourceNotFound(resource=resource)

        return endpoints[0]

    def service_get(self, service_type, name=None):
        '''Utility function to get service detail based on name and type.'''
        filters = {
            'type': service_type,
        }
        if name:
            filters['name'] = name

        services = [s for s in self.conn.identity.services(**filters)]
        if len(services) == 0:
            resource = _('service:type=%(type)s%(name)s'
                         ) % {'type': service_type,
                              'name': ',name=%s' % name if name else ''}
            raise exception.ResourceNotFound(resource=resource)

        return services[0]

    def trust_get_by_trustor(self, trustor, trustee=None, project=None):
        '''Get trust by trustor.

        :param trustor: ID of the user who is the trustor, not None;
        :param trustee: ID of the user who is the trustee;
        :param project: ID of the project to which the trust is scoped.
        '''
        filters = {
            'trustor_user_id': trustor
        }
        if trustee:
            filters['trustee_user_id'] = trustee
        if project:
            filters['project'] = project

        try:
            trusts = [t for t in self.conn.identity.trusts(**filters)]
        except sdk.exc.HttpException:
            raise exception.TrustNotFound(trustor=trustor)

        return trusts

    def trust_create(self, trustor, trustee, project, roles=None,
                     impersonation=True):
        '''Create trust between two users.

        :param trustor: ID of the user who is the trustor.
        :param trustee: ID of the user who is the trustee.
        :param project: Scope of of the trust which is a project ID.
        :param roles: List of roles the trustee will inherit from the trustor.
        :param impersonation: Whether the trustee is allowed to impersonate
                              the trustor.
        '''

        if roles:
            role_list = [{'name': role} for role in roles]
        else:
            role_list = []
        params = {
            'trustor_user_id': trustor,
            'trustee_user_id': trustee,
            'project': project,
            'impersonation': impersonation,
            'allow_redelegation': True,
            'roles': role_list
        }

        try:
            result = self.conn.identity.create_trust(**params)
        except sdk.exc.HttpException as ex:
            raise exception.TrustCreationFailure(reason=six.text_type(ex))

        return result


def get_service_credentials(**kwargs):
    '''Senlin service credential to use with Keystone.

    :param kwargs: An additional keyword argument list that can be used
                   for customizing the default settings.
    '''

    creds = {
        'user_name': CONF.authentication.service_username,
        'password': CONF.authentication.service_password,
        'auth_url': CONF.authentication.auth_url,
        'project_name': CONF.authentication.service_project_name,
        'user_domain_name': 'Default',
        'project_domain_name': 'Default',
    }
    creds.update(**kwargs)
    return creds
