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

from senlin.api.common import wsgi
from senlin.common import context
from senlin.common import exception
from senlin.drivers import base as driver_base
from senlin.rpc import client as rpc


class TrustMiddleware(wsgi.Middleware):
    """Extract trust info from request.

    The extracted information is filled into the request context.
    Senlin engine will use this information for access control.
    """
    def _get_trust(self, ctx):
        """List trusts with current user as the trustor.

        :param ctx: The requesting context.
        :return: ID of the trust or exception of InternalError.
        """
        rpcc = rpc.EngineClient()

        res = rpcc.credential_get(ctx)
        if res:
            trust_id = res.get('trust', None)
            if trust_id:
                return trust_id

        params = {
            'auth_url': ctx.auth_url,
            'token': ctx.auth_token,
            'project_id': ctx.project,
            'user_id': ctx.user,
        }
        kc = driver_base.SenlinDriver().identity(params)
        service_cred = context.get_service_context()
        admin_id = kc.get_user_id(**service_cred)
        try:
            trust = kc.trust_get_by_trustor(ctx.user, admin_id, ctx.project)
        except exception.InternalError as ex:
            if ex.code == 400:
                trust = None
            else:
                raise ex
        if not trust:
            # Create a trust if no existing one found
            trust = kc.trust_create(ctx.user, admin_id, ctx.project, ctx.roles)

        # If credential not exists, create it, otherwise update it.
        rpcc.credential_create(ctx, trust.id)

        return trust.id

    def process_request(self, req):
        trust_id = self._get_trust(req.context)
        req.context.trusts = trust_id
