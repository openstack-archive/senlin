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

from senlin.api.openstack.v1 import util
from senlin.api.openstack.v1.views import clusters_view
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import wsgi
from senlin.openstack.common import log as logging
from senlin.rpc import api as rpc_api
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class InstantiationData(object):
    """
    The data accompanying a PUT or POST request to create or update a cluster.
    """

    PARAMS = (
        CLUSTER_NAME,
        SIZE,
        PROFILE,
    ) = (
        'cluster_name',
        'size',
        'profile'
    )

    def __init__(self, data):
        """
        Initialise from the request object.
        """
        self.data = data

    def cluster_name(self):
        """
        Return the cluster name.
        """
        if self.CLUSTER_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No cluster name specified."))
        return self.data[self.CLUSTER_NAME]

    def size(self):
        """
        Return the cluster size.
        """
        if self.SIZE not in self.data:
            raise exc.HTTPBadRequest(_("No cluster size provided."))
        return self.data[self.SIZE]

    def profile(self):
        """
        Return the cluster profile.
        """
        if self.PROFILE not in self.data:
            raise exc.HTTPBadRequest(_("No cluster profile provided."))
        return self.data[self.PROFILE]


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

    def _index(self, req, tenant_safe=True):
        filter_whitelist = {
            'status': 'mixed',
            'name': 'mixed',
            'tenant': 'mixed',
            'username': 'mixed',
        }
        whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
        }
        params = util.get_allowed_params(req.params, whitelist)
        filter_params = util.get_allowed_params(req.params, filter_whitelist)

        if not filter_params:
            filter_params = None

        clusters = self.rpc_client.list_clusters(req.context,
                                                 filters=filter_params,
                                                 tenant_safe=tenant_safe,
                                                 **params)

        count = None
        return clusters_view.collection(req, clusters=clusters, count=count,
                                        tenant_safe=tenant_safe)

    @util.policy_enforce
    def global_index(self, req):
        return self._index(req, tenant_safe=False)

    @util.policy_enforce
    def index(self, req):
        """
        Lists summary information for all clusters
        """
        global_tenant = bool(req.params.get('global_tenant', False))
        if global_tenant:
            return self.global_index(req, req.context.tenant_id)

        return self._index(req)

    @util.policy_enforce
    def detail(self, req):
        """
        Lists detailed information for all clusters
        """
        clusters = self.rpc_client.list_clusters(req.context)

        return {'clusters': [clusters_view.format_cluster(req, c)
                             for c in clusters]}

    @util.policy_enforce
    def create(self, req, body):
        """
        Create a new cluster
        """
        data = InstantiationData(body)

        result = self.rpc_client.create_cluster(req.context,
                                                data.cluster_name(),
                                                data.size(),
                                                data.profile())

        formatted_cluster = clusters_view.format_cluster(
            req,
            {rpc_api.CLUSTER_ID: result}
        )
        return {'cluster': formatted_cluster}

    @util.identified_cluster
    def show(self, req, identity):
        """
        Gets detailed information for a cluster
        """

        cluster_list = self.rpc_client.show_cluster(req.context,
                                                    identity)

        if not cluster_list:
            raise exc.HTTPInternalServerError()

        cluster = cluster_list[0]

        return {'cluster': clusters_view.format_cluster(req, cluster)}

    @util.identified_cluster
    def update(self, req, identity, body):
        """
        Update an existing cluster with new parameters
        """
        data = InstantiationData(body)

        self.rpc_client.update_cluster(req.context,
                                       identity,
                                       data.size(),
                                       data.profile())

        raise exc.HTTPAccepted()

    @util.identified_cluster
    def delete(self, req, identity):
        """
        Delete the specified cluster
        """

        res = self.rpc_client.delete_cluster(req.context,
                                             identity,
                                             cast=False)

        if res is not None:
            raise exc.HTTPBadRequest(res['Error'])

        raise exc.HTTPNoContent()


class ClusterSerializer(serializers.JSONResponseSerializer):
    """Handles serialization of specific controller method responses."""

    def _populate_response_header(self, response, location, status):
        response.status = status
        response.headers['Location'] = location.encode('utf-8')
        response.headers['Content-Type'] = 'application/json'
        return response

    def create(self, response, result):
        self._populate_response_header(response,
                                       result['cluster']['links'][0]['href'],
                                       201)
        response.body = self.to_json(result)
        return response


def create_resource(options):
    """
    Clusters resource factory method.
    """
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = ClusterSerializer()
    return wsgi.Resource(ClusterController(options), deserializer, serializer)
