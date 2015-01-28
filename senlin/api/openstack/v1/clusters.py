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

from senlin.api.openstack.v1 import util
from senlin.common import attr
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
        attr.CLUSTER_NAME, attr.CLUSTER_SIZE, attr.CLUSTER_PROFILE,
        attr.CLUSTER_TAGS, attr.CLUSTER_TIMEOUT
    )

    def __init__(self, data):
        self.data = data

    def name(self):
        if attr.CLUSTER_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No cluster name specified."))
        return self.data[attr.CLUSTER_NAME]

    def size(self):
        if attr.CLUSTER_SIZE not in self.data:
            raise exc.HTTPBadRequest(_("No cluster size provided."))
        return self.data[attr.CLUSTER_SIZE]

    def profile(self):
        if attr.CLUSTER_PROFILE not in self.data:
            raise exc.HTTPBadRequest(_("No cluster profile provided."))
        return self.data[attr.CLUSTER_PROFILE]

    def parent(self):
        return self.data.get(attr.CLUSTER_PARENT, None)

    def tags(self):
        return self.data.get(attr.CLUSTER_TAGS, None)

    def timeout(self):
        return self.data.get(attr.CLUSTER_TIMEOUT,
                             cfg.CONF.default_action_timeout)


class ClusterController(object):
    """
    WSGI controller for clusters resource in Senlin v1 API
    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'clusters'

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

        if not filters:
            filters = None

        clusters = self.rpc_client.cluster_list(req.context, filters=filters,
                                                **params)
        return {'clusters': clusters}

    @util.policy_enforce
    def create(self, req, body):
        """
        Create a new cluster
        """
        data = InstantiationData(body)

        action = self.rpc_client.cluster_create(req.context, data.name(),
                                                data.size(), data.profile(),
                                                data.parent(), data.tags(),
                                                data.timeout())

        return {'id': action['target'], 'action_id': action['id']}

    @util.policy_enforce
    def get(self, req, cluster_id):
        """
        Gets detailed information for a cluster
        """

        cluster = self.rpc_client.cluster_get(req.context,
                                              cluster_id)
        if not cluster:
            raise exc.HTTPNotFound()

        return cluster

    @util.policy_enforce
    def update(self, req, cluster_id, body):
        """
        Update an existing cluster with new parameters
        """
        data = InstantiationData(body)

        self.rpc_client.cluster_update(req.context,
                                       cluster_id,
                                       data.size(),
                                       data.profile())

        raise exc.HTTPAccepted()

    @util.policy_enforce
    def delete(self, req, cluster_id):
        action = self.rpc_client.cluster_delete(req.context,
                                             cluster_id,
                                             cast=False)

        if action:
            return {'id': action['target'], 'action_id': action['id']}

        raise exc.HTTPNoContent()


def create_resource(options):
    """
    Clusters resource factory method.
    """
    return wsgi.Resource(ClusterController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
