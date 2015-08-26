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
from oslo_serialization import jsonutils
import six
from six.moves.urllib import parse as urlparse

from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import utils
from senlin.common import wsgi
from senlin.drivers import base as driver_base
from senlin.engine import webhook as webhook_mod

LOG = logging.getLogger(__name__)


class WebhookMiddleware(wsgi.Middleware):
    """Middleware for authenticating webhook triggering requests.

    This middleware authenticates the webhook trigger requests and then
    rebuild the request header so that the request will successfully pass
    the verification of keystone auth_token middleware.
    """
    def process_request(self, req):
        # We only handle POST requests
        if req.method != 'POST':
            return

        # Extract project, webhook ID and key
        results = self._parse_url(req.url)
        if not results:
            return

        (project, webhook_id, key) = results

        credential = self._get_credential(project, webhook_id, key)
        if not credential:
            return

        svc_ctx = context.get_service_context()
        kwargs = {
            'auth_url': svc_ctx['auth_url'],
            'username': svc_ctx['username'],
            'user_domain_name': svc_ctx['user_domain_name'],
            'password': svc_ctx['password']
        }
        kwargs.update(credential)

        # Get token and fill it into the request header
        token = self._get_token(**kwargs)
        req.headers['X-Auth-Token'] = token

    def _parse_url(self, url):
        """Extract webhook ID from the request URL.

        :param url: The URL from which the request is received.
        """
        parts = urlparse.urlparse(url)
        components = parts.path.split('/')
        if len(components) < 6:
            return None

        if any((components[0] != '', components[3] != 'webhooks',
                components[5] != 'trigger')):
            return None

        qs = urlparse.parse_qs(parts.query)
        if 'key' not in qs:
            return None

        return components[2], components[4], qs['key'][0]

    def _get_credential(self, project, webhook_id, key):
        """Get credential for the given webhook using the provided key.

        :param webhook_id: ID of the webhook.
        :param key: The key string to be used for decryption.
        """
        # Build a dummy RequestContext for DB APIs
        dbctx = context.RequestContext(is_admin=True, project=project)
        webhook = webhook_mod.Webhook.load(dbctx, webhook_id)
        credential = webhook.credential
        # Decrypt the credential using provided key
        try:
            cdata = utils.decrypt(webhook.credential, key)
            credential = jsonutils.loads(cdata)
        except Exception as ex:
            LOG.exception(six.text_type(ex))
            raise exc.Forbidden()

        return credential

    def _get_token(self, **kwargs):
        """Get a valid token based on the credential provided.

        :param cred: Rebuilt credential dictionary for authentication.
        """
        try:
            token = driver_base.SenlinDriver().identity.get_token(**kwargs)
        except Exception as ex:
            LOG.exception(_('Webhook failed authentication: %s.'),
                          six.text_type(ex))
            raise exc.Forbidden()

        return token
