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

from senlin.api.openstack.v1 import util
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import wsgi
from senlin.openstack.common import log as logging
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class InstantiationData(object):
    """
    The data accompanying a PUT or POST request to create or update a cluster.
    """

    PARAMS = (
        NAME, CLUSTER_ID, PROFILE_ID, ROLE, TAGS,
    ) = (
        'name', 'cluster_id', 'profile_id', 'role', 'tags',
    )

    def __init__(self, data):
        self.data = data

    def name(self):
        if self.NAME not in self.data:
            # TODO(Anyone): Generate a random name for the node
            raise exc.HTTPBadRequest(_("No node name specified."))
        return self.data[self.NAME]

    def cluster_id(self):
        # cluster_id can be empty, which means the node is an orphaned node
        if self.CLUSTER_ID not in self.data:
            return None
        return self.data[self.CLUSTER_ID]

    def profile_id(self):
        if self.PROFILE_ID not in self.data:
            raise exc.HTTPBadRequest(_("No profile ID provided."))
        return self.data[self.PROFILE_ID]

    def role(self):
        if self.ROLE not in self.data:
            return None
        return self.data[self.ROLE]

    def tags(self):
        if self.TAGS not in self.data:
            return {}
        return self.data[self.TAGS]


class NodeController(object):
    '''
    WSGI controller for nodes resource in Senlin v1 API
    '''

    REQUEST_SCOPE = 'nodes'

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
            'sort_dir': 'single',
            'sort_keys': 'multi',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        if not filters:
            filters = None

        nodes = self.rpc_client.node_list(req.context, filters=filters,
                                          **params)

        return {'nodes': nodes}

    @util.policy_enforce
    def create(self, req, body):
        data = InstantiationData(body)

        action = self.rpc_client.node_create(req.context, data.name(),
                                             data.cluster_id(),
                                             data.profile_id(),
                                             data.role(), data.tags())
        return {'id': action['target'], 'action_id': action['id']}

    @util.policy_enforce
    def get(self, req, node_id):
        node = self.rpc_client.node_get(req.context, node_id)
        if not node:
            raise exc.HTTPNotFound()

        return node

    @util.policy_enforce
    def update(self, req, node_id, body):
        data = InstantiationData(body)
        # TODO(Anyone): Need to check which fields are updatable.
        # The check should consider whether join/leave are considered node
        # updates
        self.rpc_client.node_update(req.context, node_id, data.name(),
                                    data.profile_id(),
                                    data.role(), data.tags())

        raise exc.HTTPAccepted()

    @util.policy_enforce
    def delete(self, req, node_id):
        force = 'force' in req.params
        action = self.rpc_client.node_delete(req.context, node_id, force=force,
                                             cast=False)
        if action:
            return {'id': action['target'], 'action_id': action['id']} 

        raise exc.HTTPNoContent()


def create_resource(options):
    """
    Nodes resource factory method.
    """
    return wsgi.Resource(NodeController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
