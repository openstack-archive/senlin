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
Node endpoint for Senlin v1 ReST API.
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


class NodeData(object):
    '''The data accompanying a PUT/POST request to create/update a node.'''

    PARAMS = (consts.NODE_NAME, consts.NODE_CLUSTER_ID,
              consts.NODE_PROFILE_ID, consts.NODE_ROLE,
              consts.NODE_TAGS,)

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.NODE_NAME not in self.data:
            # TODO(Anyone): Generate a random name for the node
            raise exc.HTTPBadRequest(_("No node name specified."))
        return self.data[consts.NODE_NAME]

    def cluster_id(self):
        # cluster_id can be empty, which means the node is an orphaned node
        if consts.NODE_CLUSTER_ID not in self.data:
            return None
        return self.data[consts.NODE_CLUSTER_ID]

    def profile_id(self):
        if consts.NODE_PROFILE_ID not in self.data:
            raise exc.HTTPBadRequest(_("No profile ID provided."))
        return self.data[consts.NODE_PROFILE_ID]

    def role(self):
        if consts.NODE_ROLE not in self.data:
            return None
        return self.data[consts.NODE_ROLE]

    def tags(self):
        if consts.NODE_TAGS not in self.data:
            return {}
        return self.data[consts.NODE_TAGS]


class NodeController(object):
    '''WSGI controller for nodes resource in Senlin v1 API.'''

    REQUEST_SCOPE = 'nodes'

    SUPPORTED_ACTIONS = (
        NODE_JOIN, NODE_LEAVE,
    ) = (
        'join', 'leave',
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
        }
        param_whitelist = {
            'cluster_id': 'single',
            'show_deleted': 'single',
            'limit': 'single',
            'marker': 'single',
            'sort_keys': 'multi',
            'sort_dir': 'single',
            'global_tenant': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_GLOBAL_TENANT
        if key in params:
            del params[key]
            tenant_safe = not utils.parse_bool_param(key, params[key])
            params['tenant_safe'] = tenant_safe

        if not filters:
            filters = None

        nodes = self.rpc_client.node_list(req.context, filters=filters,
                                          **params)

        return {'nodes': nodes}

    @util.policy_enforce
    def create(self, req, body):
        node_data = body.get('node')
        if node_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing"
                                       "'node' key in request body."))

        data = NodeData(node_data)

        result = self.rpc_client.node_create(req.context, data.name(),
                                             data.cluster_id(),
                                             data.profile_id(),
                                             data.role(), data.tags())
        return {'node': result}

    @util.policy_enforce
    def get(self, req, node_id):
        node = self.rpc_client.node_get(req.context, node_id)
        if not node:
            raise exc.HTTPNotFound()

        return {'node': node}

    @util.policy_enforce
    def update(self, req, node_id, body):
        node_data = body.get('node')
        if node_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing"
                                       "'node' key in request body."))

        data = NodeData(node_data)
        # TODO(Anyone): Need to check which fields are updatable.
        # The check should consider whether join/leave are considered node
        # updates
        self.rpc_client.node_update(req.context, node_id, data.name(),
                                    data.profile_id(),
                                    data.role(), data.tags())

        raise exc.HTTPAccepted()

    @util.policy_enforce
    def action(self, req, node_id, body=None):
        '''Perform specified action on a node.'''
        body = body or {}
        if len(body) == 0:
            raise exc.HTTPBadRequest(_('No action specified'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple actions specified'))

        this_action = body.keys()[0]
        if this_action not in self.SUPPORTED_ACTIONS:
            msg = _('Unrecognized action "%s" specified') % this_action
            raise exc.HTTPBadRequest(msg)

        if this_action == self.NODE_JOIN:
            cluster_id = body.get(this_action).get('cluster_id')
            if cluster_id is None:
                raise exc.HTTPBadRequest(_('No cluster specified'))
            res = self.rpc_client.node_join(req.context, node_id, cluster_id)
        elif this_action == self.NODE_LEAVE:
            res = self.rpc_client.node_leave(req.context, node_id)
        else:
            raise exc.HTTPInternalServerError(_('Unexpected action "%s"'),
                                              this_action)

        return res

    @util.policy_enforce
    def delete(self, req, node_id):
        force = 'force' in req.params
        action = self.rpc_client.node_delete(req.context, node_id, force=force,
                                             cast=False)
        if action:
            return {'id': action['target'], 'action_id': action['id']}

        raise exc.HTTPNoContent()


def create_resource(options):
    '''Nodes resource factory method.'''

    return wsgi.Resource(NodeController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
