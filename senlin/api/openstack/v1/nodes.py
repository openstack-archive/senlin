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
Node endpoint for Senlin v1 ReST API.
"""
import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.objects import base as obj_base
from senlin.objects.requests import nodes as vorn


class NodeController(wsgi.Controller):
    """WSGI controller for nodes resource in Senlin v1 API."""

    REQUEST_SCOPE = 'nodes'

    SUPPORTED_ACTIONS = (
        NODE_CHECK, NODE_RECOVER
    ) = (
        'check', 'recover'
    )

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.NODE_CLUSTER_ID: 'single',
            consts.NODE_NAME: 'mixed',
            consts.NODE_STATUS: 'mixed',
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single'
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
                'NodeListRequest', params)
            obj = vorn.NodeListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        nodes = self.rpc_client.call2(req.context, 'node_list2', obj)
        return {'nodes': nodes}

    @util.policy_enforce
    def create(self, req, body):
        """Create a new node."""
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'NodeCreateRequest', body, 'node')
            obj = vorn.NodeCreateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        node = self.rpc_client.call2(req.context, 'node_create2',
                                     obj.node)
        action_id = node.pop('action')
        result = {
            'node': node,
            'location': '/actions/%s' % action_id,
        }
        return result

    @util.policy_enforce
    def get(self, req, node_id):
        params = {'identity': node_id}
        key = consts.PARAM_SHOW_DETAILS
        if key in req.params:
            params['show_details'] = util.parse_bool_param(
                key, req.params[key])
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'NodeGetRequest', params, None)
            obj = vorn.NodeGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        node = self.rpc_client.call2(req.context, 'node_get2', obj)
        return {'node': node}

    @util.policy_enforce
    def update(self, req, node_id, body):
        data = body.get('node')
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'node' key in request body."))
        params = data
        params['identity'] = node_id
        try:
            norm_req = obj_base.SenlinObject.normalize_req('NodeUpdateRequest',
                                                           params, None)
            obj = vorn.NodeUpdateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        node = self.rpc_client.call2(req.context, 'node_update2', obj)

        action_id = node.pop('action')
        result = {
            'node': node,
            'location': '/actions/%s' % action_id,
        }
        return result

    @util.policy_enforce
    def delete(self, req, node_id):
        params = {'identity': node_id}
        try:
            norm_req = obj_base.SenlinObject.normalize_req('NodeDeleteRequest',
                                                           params)
            obj = vorn.NodeDeleteRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        res = self.rpc_client.call2(req.context, 'node_delete2', obj)
        action_id = res.pop('action')
        result = {'location': '/actions/%s' % action_id}
        return result

    @util.policy_enforce
    def action(self, req, node_id, body=None):
        """Perform specified action on a node."""

        body = body or {}
        if len(body) == 0:
            raise exc.HTTPBadRequest(_('No action specified.'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple actions specified.'))

        this_action = list(body.keys())[0]
        if this_action not in self.SUPPORTED_ACTIONS:
            msg = _('Unrecognized action "%s" specified') % this_action
            raise exc.HTTPBadRequest(msg)

        params = body.get(this_action)
        if this_action == self.NODE_CHECK:
            res = self._do_check(req.context, node_id, params)
        else:    # self.NODE_RECOVER
            res = self._do_recover(req.context, node_id, params)

        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res

    def _do_check(self, context, node_id, params):
        if not isinstance(params, dict):
            msg = _("The params provided is not a map.")
            raise exc.HTTPBadRequest(msg)

        kwargs = {
            'identity': node_id,
            'params': params
        }
        norm_req = obj_base.SenlinObject.normalize_req(
            'NodeCheckRequest', kwargs)

        try:
            obj = vorn.NodeCheckRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        res = self.rpc_client.call2(context, 'node_check2', obj)

        return res

    def _do_recover(self, context, node_id, params):
        if not isinstance(params, dict):
            msg = _("The params provided is not a map.")
            raise exc.HTTPBadRequest(msg)

        kwargs = {
            'identity': node_id,
            'params': params
        }
        norm_req = obj_base.SenlinObject.normalize_req(
            'NodeRecoverRequest', kwargs)

        try:
            obj = vorn.NodeRecoverRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        res = self.rpc_client.call2(context, 'node_recover2', obj)

        return res
