# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import itertools

from senlin.api.openstack.v1 import util
from senlin.api.openstack.v1.views import views_common
from senlin.common import attr

_collection_name = 'clusters'

basic_keys = (
    attr.CLUSTER_NAME,
    attr.CLUSTER_PROFILE,
    attr.CLUSTER_ID,
    attr.CLUSTER_PARENT,
    attr.CLUSTER_DOMAIN,
    attr.CLUSTER_PROJECT,
    attr.CLUSTER_USER,
    attr.CLUSTER_CREATED_TIME,
    attr.CLUSTER_DELETED_TIME,
    attr.CLUSTER_UPDATED_TIME,
    attr.CLUSTER_STATUS,
    attr.CLUSTER_STATUS_REASON,
    attr.CLUSTER_TIMEOUT,
    attr.CLUSTER_TAGS,
)


def format_cluster(req, cluster, keys=None, tenant_safe=True):
    def transform(key, value):
        if keys and key not in keys:
            return

        if key == attr.CLUSTER_ID:
            yield ('id', value['cluster_id'])
            yield ('links', [util.make_link(req, value)])
            if not tenant_safe:
                yield ('project', value['tenant'])
        else:
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
