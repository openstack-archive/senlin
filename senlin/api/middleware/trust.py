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
import webob

from oslo_log import log as logging

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import wsgi
from senlin.db import api as db_api
from senlin.drivers.openstack import keystone_v3

LOG = logging.getLogger(__name__)


class TrustMiddleware(wsgi.Middleware):
    '''Extract trust info from request.

    The extracted information is filled into the request context.
    Senlin engine will use this information for access control.
    '''
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

        params = {
            'auth_url': ctx.auth_url,
            'auth_token': ctx.auth_token,
            'project': ctx.project,
            'user': ctx.user,
        }
        kc = keystone_v3.KeystoneClient(params)
        service_cred = keystone_v3.get_service_credentials()

        try:
            admin_id = kc.get_user_id(**service_cred)
        except Exception as ex:
            LOG.exception(six.text_type(ex))
            msg = _('Failed in getting service user ID.')
            raise webob.exc.HTTPInternalServerError(explanation=msg)

        trust = kc.trust_get_by_trustor(ctx.user, admin_id, ctx.project)
        if not trust:
            # Create a trust if no existing one found
            try:
                trust = kc.trust_create(ctx.user, admin_id, ctx.project,
                                        ctx.roles)
            except exception.ResourceCreationFailure as ex:
                raise webob.exc.HTTPInternalServerError(six.text_type(ex))

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
