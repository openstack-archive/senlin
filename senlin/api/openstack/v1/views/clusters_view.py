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

import itertools

from senlin.api.openstack.v1 import util
from senlin.api.openstack.v1.views import views_common
from senlin.rpc import api as rpc_api

_collection_name = 'clusters'

basic_keys = (
    rpc_api.CLUSTER_NAME,
    rpc_api.CLUSTER_PROFILE,
    rpc_api.CLUSTER_ID,
    rpc_api.CLUSTER_PARENT,
    rpc_api.CLUSTER_DOMAIN,
    rpc_api.CLUSTER_PROJECT,
    rpc_api.CLUSTER_USER,
    rpc_api.CLUSTER_CREATED_TIME,
    rpc_api.CLUSTER_DELETED_TIME,
    rpc_api.CLUSTER_UPDATED_TIME,
    rpc_api.CLUSTER_STATUS,
    rpc_api.CLUSTER_STATUS_REASON,
    rpc_api.CLUSTER_TIMEOUT,
    rpc_api.CLUSTER_TAGS,
)


def format_cluster(req, cluster, keys=None, tenant_safe=True):
    def transform(key, value):
        if keys and key not in keys:
            return

        if key == rpc_api.CLUSTER_ID:
            yield ('id', value['cluster_id'])
            yield ('links', [util.make_link(req, value)])
            if not tenant_safe:
                yield ('project', value['tenant'])
        elif key == rpc_api.CLUSTER_ACTION:
            return
        elif (key == rpc_api.CLUSTER_STATUS and
              rpc_api.CLUSTER_ACTION in cluster):
            # To avoid breaking API compatibility, we join RES_ACTION
            # and RES_STATUS, so the API format doesn't expose the
            # internal split of state into action/status
            yield (key, '_'.join((cluster[rpc_api.CLUSTER_ACTION], value)))
        else:
            # TODO(zaneb): ensure parameters can be formatted for XML
            #elif key == rpc_api.CLUSTER_PARAMETERS:
            #    return key, json.dumps(value)
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in cluster.items()))


def collection(req, clusters, count=None, tenant_safe=True):
    keys = basic_keys
    formatted_clusters = [format_cluster(req, s, keys, tenant_safe)
                        for s in clusters]

    result = {'clusters': formatted_clusters}
    links = views_common.get_collection_links(req, formatted_clusters)
    if links:
        result['links'] = links
    if count is not None:
        result['count'] = count

    return result
