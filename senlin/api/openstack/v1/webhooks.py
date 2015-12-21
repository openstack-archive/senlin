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

"""
Webhook endpoint for Senlin v1 ReST API.
"""

from webob import exc

from oslo_log import log as logging

from senlin.api.openstack.v1 import util
from senlin.common import serializers
from senlin.common import wsgi
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class WebhookController(object):
    """WSGI controller for webhooks resource in Senlin v1 API."""

    REQUEST_SCOPE = 'webhooks'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def trigger(self, req, webhook_id, body=None):
        params = None
        if body is None:
            body = {}
        if body and 'params' in body:
            params = body.get('params')

        res = self.rpc_client.webhook_trigger(req.context, webhook_id, params)
        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res


def create_resource(options):
    """Webhooks resource factory method."""

    return wsgi.Resource(WebhookController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
