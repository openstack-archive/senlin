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

import jsonschema
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import utils
from senlin.objects import base as obj_base
from senlin.objects.requests import clusters as vorc


class ClusterController(wsgi.Controller):
    """WSGI controller for clusters resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'clusters'

    SUPPORTED_ACTIONS = (
        ADD_NODES, DEL_NODES, SCALE_OUT, SCALE_IN, RESIZE,
        POLICY_ATTACH, POLICY_DETACH, POLICY_UPDATE,
        CHECK, RECOVER, REPLACE_NODES
    ) = (
        'add_nodes', 'del_nodes', 'scale_out', 'scale_in', 'resize',
        'policy_attach', 'policy_detach', 'policy_update',
        'check', 'recover', 'replace_nodes'
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
        unsafe = utils.parse_bool_param(consts.PARAM_GLOBAL_PROJECT,
                                        is_global)
        params['project_safe'] = not unsafe
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterListRequest', params, None)
        obj = None
        try:
            obj = vorc.ClusterListRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        clusters = self.rpc_client.call2(req.context, 'cluster_list2', obj)
        return {'clusters': clusters}

    @util.policy_enforce
    def create(self, req, body):
        """Create a new cluster."""
        try:
            norm_req = obj_base.SenlinObject.normalize_req(
                'ClusterCreateRequest', body, 'cluster')
            obj = vorc.ClusterCreateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except (ValueError) as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))

        cluster = self.rpc_client.call2(req.context, 'cluster_create2',
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
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterGetRequest', {'identity': cluster_id})
        obj = None
        try:
            obj = vorc.ClusterGetRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        cluster = self.rpc_client.call2(req.context, 'cluster_get2', obj)

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
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterUpdateRequest', params)
        try:
            obj = vorc.ClusterUpdateRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        cluster = self.rpc_client.call2(req.context, 'cluster_update2', obj)

        action_id = cluster.pop('action')
        result = {
            'cluster': cluster,
            'location': '/actions/%s' % action_id,
        }
        return result

    def _add_nodes(self, ctx, cid, nodes):
        params = {'identity': cid, 'nodes': nodes}
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterAddNodesRequest', params)
        obj = None
        try:
            obj = vorc.ClusterAddNodesRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(ctx, 'cluster_add_nodes2', obj)

    def _del_nodes(self, ctx, cid, nodes):
        params = {'identity': cid, 'nodes': nodes}
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterDelNodesRequest', params)
        obj = None
        try:
            obj = vorc.ClusterDelNodesRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(ctx, 'cluster_del_nodes2', obj)

    @wsgi.Controller.api_version('1.3')
    def _replace_nodes(self, req, cluster_id, data):
        nodes = data.get('nodes')
        if not nodes or not isinstance(nodes, dict):
            msg = _("The data provided is not a map.")
            raise exc.HTTPBadRequest(msg)

        params = {
            'identity': cluster_id,
            'nodes': nodes
        }
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterReplaceNodesRequest', params)
        obj = None
        try:
            obj = vorc.ClusterReplaceNodesRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(req.context, 'cluster_replace_nodes2',
                                     obj)

    def _do_resize(self, context, cluster_id, data):
        params = {'identity': cluster_id}
        if consts.ADJUSTMENT_TYPE in data:
            params['adjustment_type'] = data.get(consts.ADJUSTMENT_TYPE)
        if consts.ADJUSTMENT_NUMBER in data:
            params['number'] = data.get(consts.ADJUSTMENT_NUMBER)
        if consts.ADJUSTMENT_MIN_SIZE in data:
            params['min_size'] = data.get(consts.ADJUSTMENT_MIN_SIZE)
        if consts.ADJUSTMENT_MAX_SIZE in data:
            params['max_size'] = data.get(consts.ADJUSTMENT_MAX_SIZE)
        if consts.ADJUSTMENT_MIN_STEP in data:
            params['min_step'] = data.get(consts.ADJUSTMENT_MIN_STEP)
        if consts.ADJUSTMENT_STRICT in data:
            params['strict'] = data.get(consts.ADJUSTMENT_STRICT)

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterResizeRequest', params)

        obj = None
        try:
            obj = vorc.ClusterResizeRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

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

        return self.rpc_client.call2(context, 'cluster_resize2', obj)

    def _do_scale_out(self, context, cid, count):
        params = {'identity': cid}
        if count is not None:
            params['count'] = count

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterScaleOutRequest', params, None)
        obj = None
        try:
            obj = vorc.ClusterScaleOutRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_scale_out2', obj)

    def _do_scale_in(self, context, cid, count):
        params = {'identity': cid}
        if count is not None:
            params['count'] = count

        norm_req = obj_base.SenlinObject.normalize_req('ClusterScaleInRequest',
                                                       params, None)
        obj = None
        try:
            obj = vorc.ClusterScaleInRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_scale_in2', obj)

    def _do_policy_attach(self, context, cid, data):
        params = {'identity': cid}
        if not isinstance(data, dict):
            msg = _("The data provided is not a map.")
            raise exc.HTTPBadRequest(msg)
        params.update(data)

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterAttachPolicyRequest', params, None)

        obj = None
        try:
            obj = vorc.ClusterAttachPolicyRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_policy_attach2', obj)

    def _do_policy_detach(self, context, cid, data):
        params = {'identity': cid}
        if not isinstance(data, dict):
            msg = _("The data provided is not a map.")
            raise exc.HTTPBadRequest(msg)
        params.update(data)

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterDetachPolicyRequest', params, None)

        obj = None
        try:
            obj = vorc.ClusterDetachPolicyRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_policy_detach2', obj)

    def _do_policy_update(self, context, cid, data):
        params = {'identity': cid}
        if not isinstance(data, dict):
            msg = _("The data provided is not a map.")
            raise exc.HTTPBadRequest(msg)
        params.update(data)

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterUpdatePolicyRequest', params, None)

        obj = None
        try:
            obj = vorc.ClusterUpdatePolicyRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_policy_update2', obj)

    def _do_check(self, context, cid, data):
        params = {'identity': cid}
        if not isinstance(data, dict):
            msg = _("The params provided is not a map.")
            raise exc.HTTPBadRequest(msg)
        params['params'] = data

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterCheckRequest', params, None)

        obj = None
        try:
            obj = vorc.ClusterCheckRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_check2', obj)

    def _do_recover(self, context, cid, data):
        params = {'identity': cid}
        if not isinstance(data, dict):
            msg = _("The params provided is not a map.")
            raise exc.HTTPBadRequest(msg)
        params['params'] = data

        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterRecoverRequest', params, None)

        obj = None
        try:
            obj = vorc.ClusterRecoverRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(context, 'cluster_recover2', obj)

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

        if this_action == self.ADD_NODES:
            nodes = body.get(this_action).get('nodes', [])
            res = self._add_nodes(req.context, cluster_id, nodes)
        elif this_action == self.DEL_NODES:
            nodes = body.get(this_action).get('nodes', [])
            res = self._del_nodes(req.context, cluster_id, nodes)
        elif this_action == self.RESIZE:
            data = body.get(this_action)
            res = self._do_resize(req.context, cluster_id, data)
        elif this_action == self.SCALE_OUT:
            count = body.get(this_action).get('count')
            res = self._do_scale_out(req.context, cluster_id, count)
        elif this_action == self.SCALE_IN:
            count = body.get(this_action).get('count')
            res = self._do_scale_in(req.context, cluster_id, count)
        elif this_action == self.POLICY_ATTACH:
            data = body.get(this_action)
            res = self._do_policy_attach(req.context, cluster_id, data)
        elif this_action == self.POLICY_DETACH:
            data = body.get(this_action)
            res = self._do_policy_detach(req.context, cluster_id, data)
        elif this_action == self.POLICY_UPDATE:
            data = body.get(this_action)
            res = self._do_policy_update(req.context, cluster_id, data)
        elif this_action == self.CHECK:
            data = body.get(this_action)
            res = self._do_check(req.context, cluster_id, data)
        elif this_action == self.RECOVER:
            data = body.get(this_action)
            res = self._do_recover(req.context, cluster_id, data)
        else:  # this_action == self.REPLACE_NODES:
            data = body.get(this_action)
            res = self._replace_nodes(req, cluster_id, data)

        location = {'location': '/actions/%s' % res['action']}
        res.update(location)
        return res

    @wsgi.Controller.api_version('1.2')
    @util.policy_enforce
    def collect(self, req, cluster_id, path):
        """Aggregate attribute values across a cluster."""
        stripped_path = path.strip()
        if stripped_path == '':
            raise exc.HTTPBadRequest(_("Required path attribute is missing."))

        params = {
            'identity': cluster_id,
            'path': stripped_path,
        }
        norm_req = obj_base.SenlinObject.normalize_req(
            'ClusterCollectRequest', params, None)

        obj = None
        try:
            obj = vorc.ClusterCollectRequest.obj_from_primitive(norm_req)
            jsonschema.validate(norm_req, obj.to_json_schema())
        except ValueError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex))
        except jsonschema.exceptions.ValidationError as ex:
            raise exc.HTTPBadRequest(six.text_type(ex.message))

        return self.rpc_client.call2(req.context, 'cluster_collect2', obj)

    @util.policy_enforce
    def delete(self, req, cluster_id):
        obj = vorc.ClusterDeleteRequest(identity=cluster_id)
        res = self.rpc_client.call2(req.context, 'cluster_delete2', obj)

        action_id = res.pop('action')
        result = {'location': '/actions/%s' % action_id}
        return result
