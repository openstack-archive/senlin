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

from oslo_log import log as logging

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import utils
from senlin.common import wsgi
from senlin.drivers.openstack import sdk
from senlin.webhooks import webhooks

LOG = logging.getLogger(__name__)


class WebhookMiddleware(wsgi.Middleware):
    '''Middleware to do authentication for webhook triggering

    This middleware gets authentication for request to a webhook
    based on information embedded inside url and then rebuild the
    request header.
    '''
    def process_request(self, req):
        self._authenticate(req)

    def _authenticate(self, req):
        LOG.debug("Checking credentials of webhook request")
        credential = self._get_credential(req)
        if not credential:
            return

        # Get a valid token based on credential
        # and fill into the request header
        token_id = self._get_token(credential)
        req.headers['X-Auth-Token'] = token_id

    def _get_credential(self, req):
        try:
            url_bottom = req.url.rsplit('webhooks')[1]
            webhook_id = url_bottom.rsplit('/')[1]
            trigger = url_bottom.rsplit('/')[2].startswith('trigger')
            if trigger is not True or 'key' not in req.params:
                raise Exception()
        except Exception:
            LOG.debug(_("%(url)s is not a webhook trigger url,"
                        " pass."), {'url': req.url})
            return

        if req.method != 'POST':
            LOG.debug(_("Not a post request to webhook trigger url"
                        " %(url)s, pass."), {'url': req.url})
            return

        # This is a webhook triggering, we need to fill in valid
        # credential info into the http headers to ensure this
        # request can pass keystone auth_token validation.
        #
        # Get the credential stored in DB based on webhook ID.
        # TODO(Anyone): Use Barbican to store these credential.
        LOG.debug(_("Get credential of webhook %(id)s"), webhook_id)
        senlin_context = context.RequestContext.get_service_context()
        webhook_obj = webhooks.Webhook.load(senlin_context, webhook_id)
        credential = webhook_obj.credential
        credential['webhook_id'] = webhook_id
        if 'auth_url' not in credential:
            # If no auth_url is provided in credential, use
            # auth_url of senlin service context
            credential['auth_url'] = senlin_context.auth_url

        # Decrypt the credential password with key embedded in req params
        try:
            password = utils.decrypt(credential['password'],
                                     req.params['key'])
            credential['password'] = password
        except Exception:
            msg = 'Invalid key for webhook(%s) credential decryption' % \
                webhook_id
            LOG.error(msg)
            raise exception.SenlinBadRequest(msg=msg)

        return credential

    def _get_token(self, credential):
        '''Get a valid token based on credential'''

        try:
            access_info = sdk.authenticate(**credential)
            token_id = access_info.auth_token
        except Exception as ex:
            msg = 'Webhook get token failed: %s' % ex.message
            LOG.error(msg)
            raise exception.WebhookCredentialInvalid(
                webhook=credential['webhook_id'])

        # Get token successfully!
        return token_id
