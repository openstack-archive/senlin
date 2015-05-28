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
from oslo_utils import importutils
import six
import webob

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import wsgi
from senlin.db import api as db_api
from senlin.drivers.openstack import keystone_v3


class TrustMiddleware(wsgi.Middleware):
    '''Extract trust info from request.

    The extracted information is filled into the request context.
    Senlin engine will use this information for access control.
    '''
    def _get_service_user_id(self, ctx):
        # Convert user name to user ID first
        importutils.import_module('keystonemiddleware.auth_token')
        admin_user = cfg.CONF.keystone_authtoken.admin_user
        admin_passwd = cfg.CONF.keystone_authtoken.admin_password
        project_name = cfg.CONF.keystone_authtoken.admin_tenant_name

        params = {
            'auth_url': ctx.auth_url,
            'user_name': admin_user,
            'password': admin_passwd,
            'project_name': project_name,
            # This is a hack, we need to know the domain name somehow
            'user_domain_name': 'Default',
            'project_domain_name': 'Default',
        }

        kc = keystone_v3.KeystoneClient(params)
        try:
            admin_id = kc.user_get_by_name(admin_user)
        except exception.UserNotFound:
            # This is unacceptable, treat it as a server error
            msg = _("Failed Senlin user checking.")
            raise webob.exc.HTTPInternalServerError(msg)

        return admin_id

    def _get_trust(self, ctx):
        '''List trusts with current user as the trustor.'''

        # DB table is used as a cache for the trusts.
        cred_exists = False
        res = db_api.cred_get(ctx, ctx.user, ctx.project)
        if res is not None:
            try:
                trust_id = res.cred['openstack']['trust']
                return trust_id
            except KeyError:
                # Garbage in the store, ignore it
                cred_exists = True
                pass

        admin_id = self._get_service_user_id(ctx)

        params = {
            'auth_url': ctx.auth_url,
            'auth_token': ctx.auth_token,
            'project': ctx.project,
            'user': ctx.user,
        }
        kc = keystone_v3.KeystoneClient(params)

        try:
            trusts = kc.trust_get_by_trustor(ctx.user, admin_id, ctx.project)
        except exception.TrustNotFound:
            # No trust found is okay
            pass

        if len(trusts) > 0:
            trust = trusts[0]
        else:
            # Create a trust if no existing one found
            try:
                trust = kc.trust_create(ctx.user, admin_id, ctx.project,
                                        ctx.roles)
            except exception.Error as ex:
                msg = _("Failed building trust from user: "
                        "%s.") % six.text_type(ex)
                raise webob.exc.HTTPInternalServerError(msg)

        # update cache
        if cred_exists:
            db_api.cred_update(ctx.user, ctx.project,
                               {'cred': {'openstack': {'trust': trust.id}}})
        else:
            values = {
                'user': ctx.user,
                'project': ctx.project,
                'cred': {'openstack': {'trust': trust.id}}
            }
            db_api.cred_create(ctx, values)

        return trust.id

    def process_request(self, req):
        trust_id = self._get_trust(req.context)
        req.context.trusts = trust_id
