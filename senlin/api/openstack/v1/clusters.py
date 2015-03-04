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

from oslo_config import cfg
from oslo_log import log as logging

from senlin.api.openstack.v1 import util
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class ClusterData(object):
    '''The data accompanying a POST/PUT request to create/update a cluster.'''

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.CLUSTER_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No cluster name specified."))
        return self.data[consts.CLUSTER_NAME]

    def size(self):
        if consts.CLUSTER_SIZE not in self.data:
            raise exc.HTTPBadRequest(_("No cluster size provided."))
        return self.data.get(consts.CLUSTER_SIZE, None)

    def profile(self):
        if consts.CLUSTER_PROFILE not in self.data:
            raise exc.HTTPBadRequest(_("No cluster profile provided."))
        return self.data[consts.CLUSTER_PROFILE]

    def parent(self):
        return self.data.get(consts.CLUSTER_PARENT, None)

    def tags(self):
        return self.data.get(consts.CLUSTER_TAGS, None)

    def timeout(self):
        return self.data.get(consts.CLUSTER_TIMEOUT,
                             cfg.CONF.default_action_timeout)


class ClusterController(object):
    '''WSGI controller for clusters resource in Senlin v1 API.'''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'clusters'

    SUPPORTED_ACTIONS = (
        ADD_NODES, DEL_NODES, SCALE_OUT, SCALE_IN,
        POLICY_ATTACH, POLICY_DETACH, POLICY_UPDATE,
    ) = (
        'add_nodes', 'del_nodes', 'scale_out', 'scale_in',
        'policy_attach', 'policy_detach', 'policy_update',
    )

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'status': 'mixed',
            'name': 'mixed',
            'project': 'mixed',
            'parent': 'mixed',
            'user': 'mixed',
        }
        param_whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
            'show_deleted': 'single',
            'show_nested': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_SHOW_NESTED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        if not filters:
            filters = None

        clusters = self.rpc_client.cluster_list(req.context,
                                                filters=filters,
                                                tenant_safe=True,
                                                **params)
        return {'clusters': clusters}

    @util.policy_enforce
    def create(self, req, body):
        '''Create a new cluster.'''

        cluster_data = body.get('cluster')
        if cluster_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'cluster' key in request body."))

        data = ClusterData(cluster_data)

        cluster = self.rpc_client.cluster_create(req.context, data.name(),
                                                 data.size(), data.profile(),
                                                 data.parent(), data.tags(),
                                                 data.timeout())

        return {'cluster': cluster}

    @util.policy_enforce
    def get(self, req, cluster_id):
        '''Gets detailed information for a cluster.'''

        cluster = self.rpc_client.cluster_get(req.context, cluster_id)
        return {'cluster': cluster}

    @util.policy_enforce
    def update(self, req, cluster_id, body):
        '''Update an existing cluster with new parameters.'''

        cluster_data = body.get('cluster')
        if cluster_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'cluster' key in request body."))

        size = cluster_data.get(consts.CLUSTER_SIZE)
        if size is not None:
            msg = _("Updating cluster size is not supported, please use "
                    "cluster scaling operations instead.")
            raise exc.HTTPBadRequest(msg)

        name = cluster_data.get(consts.CLUSTER_NAME)
        profile_id = cluster_data.get(consts.CLUSTER_PROFILE)
        parent = cluster_data.get(consts.CLUSTER_PARENT)
        tags = cluster_data.get(consts.CLUSTER_TAGS)
        timeout = cluster_data.get(consts.CLUSTER_TIMEOUT)
        if timeout is not None:
            timeout = utils.parse_int_param(consts.CLUSTER_TIMEOUT, timeout)

        self.rpc_client.cluster_update(req.context, cluster_id, name,
                                       profile_id, parent, tags, timeout)

        raise exc.HTTPAccepted()

    @util.policy_enforce
    def action(self, req, cluster_id, body=None):
        '''Perform specified action on a cluster.'''
        body = body or {}
        if len(body) < 1:
            raise exc.HTTPBadRequest(_('No action specified'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple actions specified'))

        this_action = body.keys()[0]
        if this_action not in self.SUPPORTED_ACTIONS:
            msg = _("Unrecognized action '%s' specified") % this_action
            raise exc.HTTPBadRequest(msg)

        if this_action == self.ADD_NODES:
            nodes = body.get(this_action).get('nodes')
            if nodes is None or not isinstance(nodes, list) or len(nodes) == 0:
                raise exc.HTTPBadRequest(_('No node to add'))
            res = self.rpc_client.cluster_add_nodes(
                req.context, cluster_id, nodes)
        elif this_action == self.DEL_NODES:
            nodes = body.get(this_action).get('nodes')
            if nodes is None or not isinstance(nodes, list) or len(nodes) == 0:
                raise exc.HTTPBadRequest(_('No node to delete'))
            res = self.rpc_client.cluster_del_nodes(
                req.context, cluster_id, nodes)
        elif this_action == self.SCALE_OUT:
            count = body.get(this_action).get('count')
            res = self.rpc_client.cluster_scale_out(req.context, cluster_id,
                                                    count)
        elif this_action == self.SCALE_IN:
            count = body.get(this_action).get('count')
            res = self.rpc_client.cluster_scale_in(req.context, cluster_id,
                                                   count)
        elif this_action == self.POLICY_ATTACH:
            data = body.get(this_action)
            res = self.rpc_client.cluster_policy_attach(req.context,
                                                        cluster_id,
                                                        **data)
        elif this_action == self.POLICY_DETACH:
            data = body.get(this_action)
            res = self.rpc_client.cluster_policy_detach(req.context,
                                                        cluster_id,
                                                        data.get('policy_id'))
        elif this_action == self.POLICY_UPDATE:
            # Note the POLICY_UPDATE action includes policy-enable/disable
            data = body.get(this_action)
            res = self.rpc_client.cluster_policy_update(req.context,
                                                        cluster_id,
                                                        **data)
        else:
            raise exc.HTTPInternalServerError(_('Unexpected action "%s"'),
                                              this_action)
        return res

    @util.policy_enforce
    def delete(self, req, cluster_id):
        action = self.rpc_client.cluster_delete(req.context,
                                                cluster_id,
                                                cast=False)

        if action:
            return {'id': action['target'], 'action_id': action['action']}

        raise exc.HTTPNoContent()


def create_resource(options):
    '''Clusters resource factory method.'''

    return wsgi.Resource(ClusterController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
