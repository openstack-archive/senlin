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

'''
Webhook endpoint for Senlin v1 ReST API.
'''

from webob import exc

from oslo_log import log as logging

from senlin.api.openstack.v1 import util
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class WebhookData(object):
    '''The data accompanying a POST request to create a webhook.'''

    PARAMS = (consts.WEBHOOK_NAME, consts.WEBHOOK_OBJ_ID,
              consts.WEBHOOK_OBJ_TYPE, consts.WEBHOOK_ACTION,
              consts.WEBHOOK_CREDENTIAL, consts.WEBHOOK_PARAMS)

    def __init__(self, data):
        self.data = data

    def name(self):
        # We allow to create a webhook without giving its name
        return self.data.get(consts.WEBHOOK_NAME, None)

    def obj_id(self):
        if consts.WEBHOOK_OBJ_ID not in self.data:
            raise exc.HTTPBadRequest(_("No obj_id provided."))
        return self.data[consts.WEBHOOK_OBJ_ID]

    def obj_type(self):
        if consts.WEBHOOK_OBJ_TYPE not in self.data:
            raise exc.HTTPBadRequest(_("No obj_type provided."))
        return self.data[consts.WEBHOOK_OBJ_TYPE]

    def action(self):
        if consts.WEBHOOK_ACTION not in self.data:
            raise exc.HTTPBadRequest(_("No action provided."))
        return self.data[consts.WEBHOOK_ACTION]

    def credential(self):
        if consts.WEBHOOK_CREDENTIAL not in self.data:
            raise exc.HTTPBadRequest(_("No credential provided."))
        return self.data[consts.WEBHOOK_CREDENTIAL]

    def params(self):
        return self.data.get(consts.WEBHOOK_PARAMS, None)


class WebhookController(object):
    '''WSGI controller for webhooks resource in Senlin v1 API.'''

    REQUEST_SCOPE = 'webhooks'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'name': 'mixed',
            'user': 'mixed',
            'obj_id': 'mixed',
            'obj_type': 'mixed',
            'action': 'mixed',
        }
        param_whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_keys': 'multi',
            'sort_dir': 'single',
            'show_deleted': 'single',
            'global_project': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_GLOBAL_PROJECT
        if key in params:
            project_safe = not utils.parse_bool_param(key, params[key])
            del params[key]
            params['project_safe'] = project_safe

        if not filters:
            filters = None

        webhooks = self.rpc_client.webhook_list(req.context, filters=filters,
                                                **params)

        return {'webhooks': webhooks}

    @util.policy_enforce
    def create(self, req, body):
        webhook_data = body.get('webhook')
        if webhook_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'webhook' key in request body."))

        data = WebhookData(webhook_data)

        result = self.rpc_client.webhook_create(req.context,
                                                data.name(),
                                                data.obj_id(),
                                                data.obj_type(),
                                                data.action(),
                                                data.credential(),
                                                data.params())
        return {'webhook': result}

    @util.policy_enforce
    def get(self, req, webhook_id):
        wh = self.rpc_client.webhook_get(req.context, webhook_id)
        return {'webhook': wh}

    @util.policy_enforce
    def trigger(self, req, webhook_id, body=None):
        params = None
        if body is not None and 'params' in body:
            params = body.get('params')

        return self.rpc_client.webhook_trigger(req.context, webhook_id, params)

    @util.policy_enforce
    def delete(self, req, webhook_id):
        self.rpc_client.webhook_delete(req.context, webhook_id, cast=False)

        raise exc.HTTPNoContent()


def create_resource(options):
    '''Webhooks resource factory method.'''

    return wsgi.Resource(WebhookController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
