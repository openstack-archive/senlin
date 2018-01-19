#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Cluster endpoint for Senlin v1 ReST API.
"""

from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _


class ClusterController(wsgi.Controller):
    """WSGI controller for clusters resource in Senlin v1 API."""

    # Define request scope
    # (must match what is in policy file and policies in code.)
    REQUEST_SCOPE = 'clusters'

    SUPPORTED_ACTIONS = (
        ADD_NODES, DEL_NODES, SCALE_OUT, SCALE_IN, RESIZE,
        POLICY_ATTACH, POLICY_DETACH, POLICY_UPDATE,
        CHECK, RECOVER, REPLACE_NODES, COMPLETE_LIFECYCLE
    ) = (
        'add_nodes', 'del_nodes', 'scale_out', 'scale_in', 'resize',
        'policy_attach', 'policy_detach', 'policy_update',
        'check', 'recover', 'replace_nodes', 'complete_lifecycle'
    )

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.CLUSTER_NAME: 'mixed',
            consts.CLUSTER_STATUS: 'mixed',
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if key not in whitelist:
                raise exc.HTTPBadRequest(_("Invalid parameter '%s'") % key)

        params = util.get_allowed_params(req.params, whitelist)
        # Note: We have to do a boolean parsing here because 1) there is
        # a renaming, 2) the boolean is usually presented as a string.
        is_global = params.pop(consts.PARAM_GLOBAL_PROJECT, False)
        unsafe = util.parse_bool_param(consts.PARAM_GLOBAL_PROJECT, is_global)
        params['project_safe'] = not unsafe
        req_obj = util.parse_request('ClusterListRequest', req, params)
        clusters = self.rpc_client.call(req.context, 'cluster_list', req_obj)
        return {'clusters': clusters}

    @util.policy_enforce
    def create(self, req, body):
        """Create a new cluster."""
        obj = util.parse_request('ClusterCreateRequest', req, body, 'cluster')
        cluster = self.rpc_client.call(req.context, 'cluster_create',
                                       obj.cluster)
        action_id = cluster.pop('action')
        result = {
            'cluster': cluster,
            'location': '/actions/%s' % action_id,
        }
        return result

    @util.policy_enforce
    def get(self, req, cluster_id):
        """Gets detailed information for a cluster."""
        body = {'identity': cluster_id}
        obj = util.parse_request('ClusterGetRequest', req, body)
        cluster = self.rpc_client.call(req.context, 'cluster_get', obj)

        return {'cluster': cluster}

    @util.policy_enforce
    def update(self, req, cluster_id, body):
        """Update an existing cluster with new parameters."""
        data = body.get('cluster')
        if data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'cluster' key in request body."))
        params = body['cluster']
        params['identity'] = cluster_id

        obj = util.parse_request('ClusterUpdateRequest', req, params)
        cluster = self.rpc_client.call(req.context, 'cluster_update', obj)

        action_id = cluster.pop('action')
        result = {
            'cluster': cluster,
            'location': '/actions/%s' % action_id,
        }
        return result

    def _do_add_nodes(self, req, cid, data):
        nodes = data.get('nodes', [])
        params = {'identity': cid, 'nodes': nodes}
        obj = util.parse_request('ClusterAddNodesRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_add_nodes', obj)

    def _do_del_nodes(self, req, cid, data):
        nodes = data.get('nodes', [])
        destroy = data.get('destroy_after_deletion', False)
        params = {'identity': cid, 'nodes': nodes,
                  'destroy_after_deletion': destroy}
        obj = util.parse_request('ClusterDelNodesRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_del_nodes', obj)

    @wsgi.Controller.api_version('1.3')
    def _do_replace_nodes(self, req, cluster_id, data):
        nodes = data.get('nodes', {})
        if not nodes or not isinstance(nodes, dict):
            msg = _("The data provided is not a map")
            raise exc.HTTPBadRequest(msg)

        params = {'identity': cluster_id, 'nodes': nodes}
        obj = util.parse_request('ClusterReplaceNodesRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_replace_nodes',
                                    obj)

    def _do_resize(self, req, cluster_id, data):
        params = {}

        for key in [consts.ADJUSTMENT_TYPE, consts.ADJUSTMENT_NUMBER,
                    consts.ADJUSTMENT_MIN_SIZE, consts.ADJUSTMENT_MAX_SIZE]:
            if data.get(key, None) is not None:
                params[key] = data.get(key)

        adj_type = data.get(consts.ADJUSTMENT_TYPE, None)
        min_step = data.get(consts.ADJUSTMENT_MIN_STEP, None)
        if ((adj_type == consts.CHANGE_IN_PERCENTAGE) and
                min_step is not None):
            params[consts.ADJUSTMENT_MIN_STEP] = min_step

        if not params:
            msg = _("Not enough parameters to do resize action.")
            raise exc.HTTPBadRequest(msg)

        strict = data.get(consts.ADJUSTMENT_STRICT, None)
        if strict is not None:
            params[consts.ADJUSTMENT_STRICT] = strict

        params['identity'] = cluster_id
        obj = util.parse_request('ClusterResizeRequest', req, params)

        if (obj.obj_attr_is_set('adjustment_type') and
                not obj.obj_attr_is_set('number')):
            msg = _("Missing number value for size adjustment.")
            raise exc.HTTPBadRequest(msg)

        if (obj.obj_attr_is_set('number') and
                not obj.obj_attr_is_set('adjustment_type')):
            msg = _("Missing adjustment_type value for size adjustment.")
            raise exc.HTTPBadRequest(msg)

        if (obj.obj_attr_is_set('min_size') and
                obj.obj_attr_is_set('max_size')):
            if obj.max_size > 0 and obj.min_size > obj.max_size:
                msg = _("The specified min_size (%(n)s) is greater than the "
                        "specified max_size (%(m)s)."
                        ) % {'m': obj.max_size, 'n': obj.min_size}
                raise exc.HTTPBadRequest(msg)

        return self.rpc_client.call(req.context, 'cluster_resize', obj)

    def _do_scale_out(self, req, cid, data):
        count = data.get('count', None)
        params = {'identity': cid}
        if count is not None:
            params['count'] = count
        obj = util.parse_request('ClusterScaleOutRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_scale_out', obj)

    def _do_scale_in(self, req, cid, data):
        count = data.get('count', None)
        params = {'identity': cid}

        if count is not None:
            params['count'] = count

        obj = util.parse_request('ClusterScaleInRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_scale_in', obj)

    def _do_policy_attach(self, req, cid, data):
        params = {'identity': cid}
        params.update(data)
        obj = util.parse_request('ClusterAttachPolicyRequest', req, params)
        return self.rpc_client.call(req.context,
                                    'cluster_policy_attach', obj)

    def _do_policy_detach(self, req, cid, data):
        params = {'identity': cid}
        params.update(data)

        obj = util.parse_request('ClusterDetachPolicyRequest', req, params)
        return self.rpc_client.call(req.context,
                                    'cluster_policy_detach', obj)

    def _do_policy_update(self, req, cid, data):
        params = {'identity': cid}
        params.update(data)

        obj = util.parse_request('ClusterUpdatePolicyRequest', req, params)
        return self.rpc_client.call(req.context,
                                    'cluster_policy_update', obj)

    def _do_check(self, req, cid, data):
        params = {'identity': cid, 'params': data}
        obj = util.parse_request('ClusterCheckRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_check', obj)

    def _do_recover(self, req, cid, data):
        params = {'identity': cid, 'params': data}
        obj = util.parse_request('ClusterRecoverRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_recover', obj)

    @wsgi.Controller.api_version('1.9')
    def _do_complete_lifecycle(self, req, cid, data):
        lifecycle_action_token = data.get('lifecycle_action_token', None)

        params = {'identity': cid,
                  'lifecycle_action_token': lifecycle_action_token}
        obj = util.parse_request('ClusterCompleteLifecycleRequest', req,
                                 params)
        return self.rpc_client.call(req.context, 'cluster_complete_lifecycle',
                                    obj)

    @util.policy_enforce
    def action(self, req, cluster_id, body=None):
        """Perform specified action on a cluster."""
        body = body or {}
        if len(body) < 1:
            raise exc.HTTPBadRequest(_('No action specified'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple actions specified'))

        this_action = list(body.keys())[0]
        if this_action not in self.SUPPORTED_ACTIONS:
            msg = _("Unrecognized action '%s' specified") % this_action
            raise exc.HTTPBadRequest(msg)

        do_func_name = "_do_" + this_action
        if not hasattr(self, do_func_name):
            raise exc.HTTPBadRequest(_('Unsupported action'))

        do_func = getattr(self, do_func_name)
        data = body.get(this_action, {})
        if not isinstance(data, dict):
            msg = _("The data provided is not a map")
            raise exc.HTTPBadRequest(msg)

        res = do_func(req, cluster_id, data)

        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def collect(self, req, cluster_id, path):
        """Aggregate attribute values across a cluster."""
        stripped_path = path.strip()
        if (stripped_path == '') or (stripped_path == 'None'):
            raise exc.HTTPBadRequest(_("Required path attribute is missing."))

        params = {
            'identity': cluster_id,
            'path': stripped_path,
        }
        obj = util.parse_request('ClusterCollectRequest', req, params)
        return self.rpc_client.call(req.context, 'cluster_collect', obj)

    @wsgi.Controller.api_version('1.4')
    @util.policy_enforce
    def operation(self, req, cluster_id, body=None):
        """Perform specified operation on the specified cluster."""
        body = body or {}
        if len(body) < 1:
            raise exc.HTTPBadRequest(_('No operation specified'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple operations specified'))

        operation = list(body.keys())[0]
        params = {
            'identity': cluster_id,
            'operation': operation,
            'params': body[operation].get('params', {}),
            'filters': body[operation].get('filters', {}),
        }
        obj = util.parse_request('ClusterOperationRequest', req, params)

        res = self.rpc_client.call(req.context, 'cluster_op', obj)

        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res

    @util.policy_enforce
    def delete(self, req, cluster_id, body=None):
        if req.params.get('force') is not None:
            force = util.parse_bool_param(consts.CLUSTER_DELETE_FORCE,
                                          req.params.get('force'))
        elif body:
            force = body.get('force')
            if force is None:
                force = False
        else:
            force = False

        params = {'identity': cluster_id, 'force': force}
        obj = util.parse_request('ClusterDeleteRequest', req, params)
        res = self.rpc_client.call(req.context, 'cluster_delete', obj)

        action_id = res.pop('action')
        result = {'location': '/actions/%s' % action_id}
        return result
