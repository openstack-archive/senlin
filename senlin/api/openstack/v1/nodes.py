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
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _


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

        obj = util.parse_request('NodeListRequest', req, params)
        nodes = self.rpc_client.call(req.context, 'node_list', obj)
        return {'nodes': nodes}

    @util.policy_enforce
    def create(self, req, body):
        """Create a new node."""
        obj = util.parse_request('NodeCreateRequest', req, body, 'node')
        node = self.rpc_client.call(req.context, 'node_create',
                                    obj.node)
        action_id = node.pop('action')
        result = {
            'node': node,
            'location': '/actions/%s' % action_id,
        }
        return result

    @wsgi.Controller.api_version('1.7')
    @util.policy_enforce
    def adopt(self, req, body):
        """Adopt a node for management."""
        obj = util.parse_request('NodeAdoptRequest', req, body)
        node = self.rpc_client.call(req.context, 'node_adopt', obj)
        return {'node': node}

    @wsgi.Controller.api_version('1.7')
    @util.policy_enforce
    def adopt_preview(self, req, body):
        """Preview a node adoption."""
        # make sure we will fall into the preview path
        obj = util.parse_request('NodeAdoptPreviewRequest', req, body)
        node = self.rpc_client.call(req.context, 'node_adopt_preview', obj)
        return {'node_profile': node}

    @util.policy_enforce
    def get(self, req, node_id):
        params = {'identity': node_id}
        key = consts.PARAM_SHOW_DETAILS
        if key in req.params:
            params['show_details'] = util.parse_bool_param(
                key, req.params[key])

        obj = util.parse_request('NodeGetRequest', req, params)
        node = self.rpc_client.call(req.context, 'node_get', obj)
        return {'node': node}

    @util.policy_enforce
    def update(self, req, node_id, body):
        data = body.get('node')
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'node' key in request body."))
        params = data
        params['identity'] = node_id

        obj = util.parse_request('NodeUpdateRequest', req, params)
        node = self.rpc_client.call(req.context, 'node_update', obj)

        action_id = node.pop('action')
        result = {
            'node': node,
            'location': '/actions/%s' % action_id,
        }
        return result

    @util.policy_enforce
    def delete(self, req, node_id, body=None):
        if body:
            force = body.get('force')
        else:
            force = False

        if force is not None:
            force = util.parse_bool_param(consts.NODE_DELETE_FORCE, force)

        params = {'identity': node_id, 'force': force}

        obj = util.parse_request('NodeDeleteRequest', req, params)
        res = self.rpc_client.call(req.context, 'node_delete', obj)
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
            msg = _("Unrecognized action '%s' specified") % this_action
            raise exc.HTTPBadRequest(msg)

        params = body.get(this_action)
        if this_action == self.NODE_CHECK:
            res = self._do_check(req, node_id, params)
        else:    # self.NODE_RECOVER
            res = self._do_recover(req, node_id, params)

        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res

    def _do_check(self, req, node_id, params):
        if not isinstance(params, dict):
            msg = _("The params provided is not a map.")
            raise exc.HTTPBadRequest(msg)

        kwargs = {
            'identity': node_id,
            'params': params
        }

        obj = util.parse_request('NodeCheckRequest', req, kwargs)
        res = self.rpc_client.call(req.context, 'node_check', obj)

        return res

    def _do_recover(self, req, node_id, params):
        if not isinstance(params, dict):
            msg = _("The params provided is not a map.")
            raise exc.HTTPBadRequest(msg)

        kwargs = {
            'identity': node_id,
            'params': params
        }

        obj = util.parse_request('NodeRecoverRequest', req, kwargs)
        res = self.rpc_client.call(req.context, 'node_recover', obj)

        return res

    @wsgi.Controller.api_version('1.4')
    @util.policy_enforce
    def operation(self, req, node_id, body=None):
        """Perform the specified operation on the specified node."""

        body = body or {}
        if len(body) == 0:
            raise exc.HTTPBadRequest(_('No operation specified.'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple operations specified.'))

        operation = list(body.keys())[0]
        params = {
            'identity': node_id,
            'operation': operation,
            'params': body.get(operation),
        }

        obj = util.parse_request('NodeOperationRequest', req, params)
        node = self.rpc_client.call(req.context, 'node_op', obj)

        action_id = node.pop('action')
        result = {
            'location': '/actions/%s' % action_id,
        }
        return result
