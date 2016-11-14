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

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import utils
from senlin.objects import base as obj_base
from senlin.objects.requests import receivers as vorr


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
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ReceiverCreateRequest', body, 'receiver')
            obj = vorr.ReceiverCreateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        result = self.rpc_client.call2(req.context, 'receiver_create2',
                                       obj.receiver)

        return {'receiver': result}

    @util.policy_enforce
    def get(self, req, receiver_id):
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ReceiverGetRequest', {'identity': receiver_id})
            obj = vorr.ReceiverGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        receiver = self.rpc_client.call2(req.context, 'receiver_get2', obj)
        return {'receiver': receiver}

    @util.policy_enforce
    def delete(self, req, receiver_id):
        self.rpc_client.receiver_delete(req.context, receiver_id, cast=False)
        raise exc.HTTPNoContent()

    @util.policy_enforce
    def notify(self, req, receiver_id, body=None):
        self.rpc_client.receiver_notify(req.context, receiver_id, body)
        raise exc.HTTPNoContent()
