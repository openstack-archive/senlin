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
from urllib import parse as urlparse
import webob

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.drivers import base as driver_base
from senlin.rpc import client as rpc

LOG = logging.getLogger(__name__)


class WebhookMiddleware(wsgi.Middleware):
    """Middleware for authenticating webhook triggering requests.

    This middleware authenticates the webhook trigger requests and then
    rebuilds the request header so that the request will successfully pass
    the verification of keystone auth_token middleware.
    """
    def process_request(self, req):
        # We only handle POST requests
        if req.method != 'POST':
            return

        # Extract webhook (receiver) ID and params
        results = self._parse_url(req.url)
        if not results:
            return

        (receiver_id, params) = results

        api_version = str(req.version_request)
        ctx = context.RequestContext(is_admin=True, api_version=api_version)
        req.context = ctx

        obj = util.parse_request(
            'ReceiverGetRequest', req, {'identity': receiver_id})
        rpcc = rpc.get_engine_client()
        receiver = rpcc.call(ctx, 'receiver_get', obj)

        svc_ctx = context.get_service_credentials()
        kwargs = {
            'auth_url': svc_ctx['auth_url'],
            'username': svc_ctx['username'],
            'user_domain_name': svc_ctx['user_domain_name'],
            'password': svc_ctx['password'],
            'project_domain_name': svc_ctx['project_domain_name'],
            'verify': svc_ctx['verify'],
            'interface': svc_ctx['interface'],
        }
        kwargs.update(receiver['actor'])

        # Get token and fill it into the request header
        token = self._get_token(**kwargs)
        req.headers['X-Auth-Token'] = token

    def _parse_url(self, url):
        """Extract receiver ID from the request URL.

        Parse a URL of format: http://host:port/v1/webhooks/id/trigger?V=1&k=v
        :param url: The URL from which the request is received.
        """
        parts = urlparse.urlparse(url)
        p = parts.path.split('/')

        try:
            index = p.index('v1')
            p = p[(index + 1):]
        except ValueError:
            pass

        if len(p) != 3 or p[0] != 'webhooks' or p[2] != 'trigger':
            return None

        # at this point it has been determined that the URL is a webhook
        # trigger request
        qs = urlparse.parse_qs(parts.query)
        if 'V' in qs:
            qs.pop('V')
        else:
            raise webob.exc.HTTPBadRequest(
                explanation=_('V query parameter is required in webhook '
                              'trigger URL'))

        params = dict((k, v[0]) for k, v in qs.items())
        return p[1], params

    def _get_token(self, **kwargs):
        """Get a valid token based on the credential provided.

        :param cred: Rebuilt credential dictionary for authentication.
        """
        try:
            token = driver_base.SenlinDriver().identity.get_token(**kwargs)
        except Exception as ex:
            LOG.exception('Webhook failed authentication: %s.', ex)
            raise exc.Forbidden()

        return token
