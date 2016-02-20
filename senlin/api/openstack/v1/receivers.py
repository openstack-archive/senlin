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

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import utils


class ReceiverData(object):
    """The data accompanying a POST request to create a receiver."""

    PARAMS = (consts.RECEIVER_NAME, consts.RECEIVER_TYPE,
              consts.RECEIVER_CLUSTER, consts.RECEIVER_ACTION,
              consts.RECEIVER_ACTOR, consts.RECEIVER_PARAMS)

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.RECEIVER_NAME not in self.data:
            raise exc.HTTPBadRequest(_("Missing 'name' in request."))
        return self.data.get(consts.RECEIVER_NAME, None)

    def cluster_id(self):
        if consts.RECEIVER_CLUSTER_ID not in self.data:
            raise exc.HTTPBadRequest(_("Missing 'cluster_id' in request."))
        return self.data[consts.RECEIVER_CLUSTER_ID]

    def type_name(self):
        if consts.RECEIVER_TYPE not in self.data:
            raise exc.HTTPBadRequest(_("Missing 'type' in request."))
        return self.data[consts.RECEIVER_TYPE]

    def action(self):
        if consts.RECEIVER_ACTION not in self.data:
            raise exc.HTTPBadRequest(_("Missing 'action' in request."))
        return self.data[consts.RECEIVER_ACTION]

    def actor(self):
        return self.data.get(consts.RECEIVER_ACTOR, None)

    def params(self):
        return self.data.get(consts.RECEIVER_PARAMS, None)


class ReceiverController(wsgi.Controller):
    """WSGI controller for receiver resource in Senlin v1 API."""

    REQUEST_SCOPE = 'receivers'

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            consts.RECEIVER_NAME: 'mixed',
            consts.RECEIVER_TYPE: 'mixed',
            consts.RECEIVER_CLUSTER_ID: 'mixed',
            consts.RECEIVER_ACTION: 'mixed',
        }
        param_whitelist = {
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if (key not in param_whitelist.keys() and key not in
                    filter_whitelist.keys()):
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_GLOBAL_PROJECT
        if key in params:
            show_global = utils.parse_bool_param(key, params[key])
            del params[key]
            params['project_safe'] = not show_global

        if not filters:
            filters = None

        receivers = self.rpc_client.receiver_list(req.context, filters=filters,
                                                  **params)

        return {'receivers': receivers}

    @util.policy_enforce
    def create(self, req, body):
        data = body.get('receiver')
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'receiver' key in request body."))

        data = ReceiverData(data)

        result = self.rpc_client.receiver_create(req.context,
                                                 data.name(),
                                                 data.type_name(),
                                                 data.cluster_id(),
                                                 data.action(),
                                                 data.actor(),
                                                 data.params())
        return {'receiver': result}

    @util.policy_enforce
    def get(self, req, receiver_id):
        receiver = self.rpc_client.receiver_get(req.context, receiver_id)
        return {'receiver': receiver}

    @util.policy_enforce
    def delete(self, req, receiver_id):
        self.rpc_client.receiver_delete(req.context, receiver_id, cast=False)
