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
from senlin.objects import base as obj_base
from senlin.objects.requests import receivers as vorr


class ReceiverController(wsgi.Controller):
    """WSGI controller for receiver resource in Senlin v1 API."""

    REQUEST_SCOPE = 'receivers'

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.RECEIVER_NAME: 'mixed',
            consts.RECEIVER_TYPE: 'mixed',
            consts.RECEIVER_CLUSTER_ID: 'mixed',
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

        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ReceiverListRequest', params)
            obj = vorr.ReceiverListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        receivers = self.rpc_client.call2(req.context, 'receiver_list2', obj)

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
        params = {'identity': receiver_id}
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ReceiverDeleteRequest', params)
            obj = vorr.ReceiverDeleteRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        self.rpc_client.call2(req.context, 'receiver_delete2', obj)
        raise exc.HTTPNoContent()

    @util.policy_enforce
    def notify(self, req, receiver_id, body=None):
        params = {'identity': receiver_id}
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ReceiverNotifyRequest', params)
            obj = vorr.ReceiverNotifyRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        self.rpc_client.call2(req.context, 'receiver_notify2', obj)
        raise exc.HTTPNoContent()
