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
from oslo_log import log

from senlin.common.i18n import _LW
from senlin.drivers import base
from senlin.drivers.openstack import sdk

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class KeystoneClient(base.DriverBase):
    '''Keystone V3 driver.'''

    def __init__(self, params):
        super(KeystoneClient, self).__init__(params)
        self.conn = sdk.create_connection(params)
        self.session = self.conn.session

    @sdk.translate_exception
    def trust_list(self, **query):
        trusts = [t for t in self.conn.identity.trusts(**query)]
        return trusts

    @sdk.translate_exception
    def trust_delete(self, trust_id):
        self.conn.identity.delete_trust(trust_id, ignore_missing=True)
        return

    @sdk.translate_exception
    def user_get(self, name_or_id, ignore_missing=False):
        # Note: Since default keystone policy will block non-admin user to
        # get/list user(s), this function may not be workable. Please use
        # get_user_id method to get the ID of user if needed.
        user = self.conn.identity.find_user(
            name_or_id, ignore_missing=ignore_missing)
        return user

    @sdk.translate_exception
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
        return endpoints[0] if endpoints else None

    @sdk.translate_exception
    def service_get(self, service_type):
        """Utility function to get service detail based on type.

        :param service_type: A string specifying the service type for
            retrieval.
        :return: An openstack.identity.v3.Service object.
        """
        return self.conn.identity.services(type=service_type)

    @sdk.translate_exception
    def trust_get_by_trustor(self, trustor, trustee=None, project=None):
        '''Get trust by trustor.

        Note we cannot provide two or more filters to keystone due to
        constraints in keystone implementation. We do additional filtering
        after the results are returned.

        :param trustor: ID of the trustor;
        :param trustee: ID of the trustee;
        :param project: ID of the project to which the trust is scoped.
        :returns: The trust object or None if no matching trust is found.
        '''
        filters = {'trustor_user_id': trustor}

        trusts = [t for t in self.conn.identity.trusts(**filters)]

        for trust in trusts:
            if (trustee and trust.trustee_user_id != trustee):
                continue

            if (project and trust.project_id != project):
                continue

            return trust

        return None

    @sdk.translate_exception
    def trust_create(self, trustor, trustee, project, roles=None,
                     impersonation=True):
        '''Create trust between two users.

        :param trustor: ID of the user who is the trustor.
        :param trustee: ID of the user who is the trustee.
        :param project: Scope of the trust which is a project ID.
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
            'project_id': project,
            'impersonation': impersonation,
            'allow_redelegation': True,
            'roles': role_list
        }

        result = self.conn.identity.create_trust(**params)

        return result

    @sdk.translate_exception
    def region_list(self, **queries):
        return self.conn.identity.regions(**queries)

    @classmethod
    @sdk.translate_exception
    def get_token(cls, **creds):
        '''Get token using given credential'''

        access_info = sdk.authenticate(**creds)
        return access_info['token']

    @classmethod
    @sdk.translate_exception
    def get_user_id(cls, **creds):
        '''Get ID of the user with given credential'''

        access_info = sdk.authenticate(**creds)
        return access_info['user_id']

    @classmethod
    def get_service_credentials(cls, **kwargs):
        '''Senlin service credential to use with Keystone.

        :param kwargs: An additional keyword argument list that can be used
                       for customizing the default settings.
        '''

        creds = {
            'auth_url': CONF.authentication.auth_url,
            'username': CONF.authentication.service_username,
            'password': CONF.authentication.service_password,
            'project_name': CONF.authentication.service_project_name,
            'user_domain_name': cfg.CONF.authentication.service_user_domain,
            'project_domain_name':
                cfg.CONF.authentication.service_project_domain,
        }
        creds.update(**kwargs)
        return creds

    def validate_regions(self, regions):
        """Check whether the given regions are valid.

        :param regions: A list of regions for validation.
        :returns: A list of regions that are found available on keystone.
        """
        known = [r['id'] for r in self.region_list()]

        validated = []
        for r in regions:
            if r in known:
                validated.append(r)
            else:
                LOG.warning(_LW('Region %s is not found.'), r)

        return validated
