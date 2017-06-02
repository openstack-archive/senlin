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


class ReceiverController(wsgi.Controller):
    """WSGI controller for receiver resource in Senlin v1 API."""

    REQUEST_SCOPE = 'receivers'

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.RECEIVER_NAME: 'mixed',
            consts.RECEIVER_TYPE: 'mixed',
            consts.RECEIVER_CLUSTER_ID: 'mixed',
            consts.RECEIVER_USER_ID: 'mixed',
            consts.RECEIVER_ACTION: 'mixed',
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if key not in whitelist.keys():
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)

        params = util.get_allowed_params(req.params, whitelist)

        project_safe = not util.parse_bool_param(
            consts.PARAM_GLOBAL_PROJECT,
            params.pop(consts.PARAM_GLOBAL_PROJECT, False))
        params['project_safe'] = project_safe

        obj = util.parse_request('ReceiverListRequest', req, params)
        receivers = self.rpc_client.call(req.context, 'receiver_list', obj)

        return {'receivers': receivers}

    @util.policy_enforce
    def create(self, req, body):

        obj = util.parse_request(
            'ReceiverCreateRequest', req, body, 'receiver')
        result = self.rpc_client.call(req.context, 'receiver_create',
                                      obj.receiver)

        return {'receiver': result}

    @util.policy_enforce
    def get(self, req, receiver_id):
        obj = util.parse_request(
            'ReceiverGetRequest', req, {'identity': receiver_id})
        receiver = self.rpc_client.call(req.context, 'receiver_get', obj)
        return {'receiver': receiver}

    @util.policy_enforce
    def update(self, req, receiver_id, body):
        receiver_data = body.get('receiver', None)
        if receiver_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'receiver' key in request body."))

        kwargs = receiver_data
        kwargs['identity'] = receiver_id
        obj = util.parse_request('ReceiverUpdateRequest', req,
                                 kwargs)
        receiver = self.rpc_client.call(req.context, 'receiver_update', obj)

        return {'receiver': receiver}

    @util.policy_enforce
    def delete(self, req, receiver_id):

        obj = util.parse_request(
            'ReceiverDeleteRequest', req, {'identity': receiver_id})
        self.rpc_client.call(req.context, 'receiver_delete', obj)
        raise exc.HTTPNoContent()

    @util.policy_enforce
    def notify(self, req, receiver_id, body=None):

        obj = util.parse_request(
            'ReceiverNotifyRequest', req, {'identity': receiver_id})
        self.rpc_client.call(req.context, 'receiver_notify', obj)
        raise exc.HTTPNoContent()
