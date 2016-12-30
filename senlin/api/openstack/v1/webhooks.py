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

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.objects import base as obj_base


class WebhookController(wsgi.Controller):
    """WSGI controller for webhooks resource in Senlin v1 API."""

    REQUEST_SCOPE = 'webhooks'

    @util.policy_enforce
    def trigger(self, req, webhook_id, body=None):
        if body is None:
            body = {'params': None}

        body = obj_base.SenlinObject.normalize_req(
            'WebhookTriggerRequestBody', body)
        obj = util.parse_request(
            'WebhookTriggerRequest', req, {'identity': webhook_id,
                                           'body': body})

        res = self.rpc_client.call(req.context, 'webhook_trigger', obj)
        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res
